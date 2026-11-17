"""Walk-forward evaluation (Session 4), exactly as docs/hypotheses.md specifies.

For every name, target t in {y, k}, quarter q and source in {volume source, Wikipedia, combined}, the call
is made at asof = fiscal quarter end by THE shared per-quarter call, live.calls_at() (the live calls use
the same function). Each call row records:

- prediction  = sign(d_alt_q) at asof (combined: sign of sum d_alt_s / std_s); d_alt == 0 is a miss.
- actual      = sign(d_t_q), d_t_q = t_q - t_{q-1}, both the FIRST-reported like-for-like YoY
                (hypotheses 3.11: the realised outcome uses the first filing/release that reports q).
- momentum    = sign(d_t_{q-1}) with t_{q-1}, t_{q-2} the 3.11 values at asof (latest filing filed
                strictly before asof); may use non-clean values (spec). d == 0 is a miss.
- 50% baseline: expected hit rate 0.5.
- magnitude   = yhat_q = t_{q-1}(asof) + beta * d_alt_q (live.magnitude; pairs per 3.11 at asof);
                baseline yhat_q = t_{q-1}(asof). Scored against the first-reported t_q. Combined: not run.

Conventions (Session 4 prompt, applied everywhere through live.py):
(i)  the combined source's expanding std uses each past quarter's d_alt computed at that quarter's own end;
(ii) magnitude fitting pairs use 3.11 values at asof; the scored outcome uses the first-reported value.

Same-sample rule: within a cell, the model and its baselines are scored on the identical set of
quarters; a quarter where any of them (or the actual) is "not run" is excluded for all and counted.

Windows / variants (hypotheses 3.5, 3.7, 3.8; hard rule 4):
- headline   : name's headline window, quarters whose target d is clean;
- robustness : (i) US 2024Q1-2026Q3 (TCOM: none, 3.7); (ii) MAJOR structural-break quarters removed
               (q dropped if t_q or t_{q-1} is listed for that name/target); (iii) Wikipedia with the
               7 days from each earnings release removed from both years (variant 'ewr'; the combined
               source is rerun with the ewr Wikipedia component; the volume component is unchanged).

TSA gives the identical call to all six US names each quarter: those six cells are not independent
(tsa_dependence() summarises per quarter, each quarter counted once).
"""
from __future__ import annotations

import datetime as dt
import re
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import binom
from statsmodels.stats.multitest import multipletests

from . import config, features as F, live
from .power import BREAK_ROBUSTNESS_MIN_N, major_break_quarters, min_hits
from .quarters import Quarter, d_clean, qrange
from .rawstore import REPO_ROOT

CALL_FIRST_Q = Quarter(2022, 2)          # first q with d_y: revenue versions start 2021Q1 -> y from 2022Q1
VOLUME_SOURCES = ("tsa", "caac", "hkia")
DIRECTIONS = ("accelerate", "decelerate")


# ------------------------------------------------------------------------------------- inputs


def load_inputs() -> dict:
    series = F.load_series(snapshots=F.backtest_snapshots())   # pinned S3 snapshots
    versions = pd.read_csv(REPO_ROOT / "data/processed/revenue_pit.csv", dtype={"accession": str})
    values = pd.read_csv(REPO_ROOT / "data/processed/release_values.csv", dtype={"accession": str})
    releases = pd.read_csv(REPO_ROOT / "data/processed/earnings_releases.csv", dtype={"accession": str})
    pipe = config.load_yaml("pipeline.yaml")
    return {"series": series, "td": live.TargetData(versions, values), "releases": releases,
            "cos": config.companies(), "releases_since": dt.date.fromisoformat(pipe["releases_since"])}


def predictions_from_hypotheses() -> dict[tuple[str, str, str], str]:
    """(name, source, target) -> 'signal expected' / 'signal NOT expected' from hypotheses.md section 5."""
    text = (REPO_ROOT / "docs" / "hypotheses.md").read_text()
    sec = text[text.index("## 5."):text.index("## 6.")]
    out = {}
    for line in sec.splitlines():
        m = re.match(r"^\| (\w+) \| ([^|]+?) \| (y|k) \| ([^|]+?) \|", line)
        if m:
            src = m.group(2).strip().lower().replace(" (fallback)", "")
            pred = "signal expected" if m.group(4).strip().replace("**", "").startswith("signal expected") \
                else "signal NOT expected"
            out[(m.group(1), src, m.group(3))] = pred
    return out


def power_table() -> pd.DataFrame:
    return pd.read_csv(REPO_ROOT / "outputs/tables/power_table.csv")


# ------------------------------------------------------------------------------------- d_alt cache


class DaltCache:
    """Memoised features.d_alt. variant 'base' or 'ewr' (Wikipedia: 7 days from each earnings release
    removed from both years, releases filed on or before asof; other sources unchanged)."""

    def __init__(self, release_dates: dict[str, list[dt.date]], releases_since: dt.date):
        self.rd, self.since, self._c = release_dates, releases_since, {}

    def fn(self, variant: str):
        def d(s: F.Series, p: Quarter, a: dt.date) -> dict:
            ewr = variant == "ewr" and s.source == "wikipedia"
            key = (s.series_id, ewr, str(p), a)
            if key not in self._c:
                if ewr:
                    name = s.series_id.split(":", 1)[1]
                    self._c[key] = F.d_alt(s, p, a, self.rd[name], self.since)
                else:
                    self._c[key] = F.d_alt(s, p, a)
            return self._c[key]
        return d


def release_dates(releases: pd.DataFrame) -> dict[str, list[dt.date]]:
    r = releases[releases.is_amendment == 0]
    return {n: sorted(pd.to_datetime(g.filed).dt.date.tolist()) for n, g in r.groupby("name")}


# ------------------------------------------------------------------------------------- calls


def _dir(d: float | None) -> str | None:
    if d is None or (isinstance(d, float) and np.isnan(d)):
        return None
    return "accelerate" if d > 0 else "decelerate" if d < 0 else "flat"


def _correct(pred: str | None, actual: str | None) -> bool | None:
    """None = not scoreable; a 'no call' (d_alt == 0) or a flat actual is a miss."""
    if pred is None or actual is None:
        return None
    return pred in DIRECTIONS and pred == actual


def targets_of(co: dict) -> list[str]:
    return ["y"] + (["k"] if co.get("kpi") else [])


def make_calls(inp: dict, variants=("base", "ewr"), checkpoints=("qend",)) -> pd.DataFrame:
    """One row per (name, quarter, source, target, variant, checkpoint) call. Backtest asof = quarter end;
    the lead-time checkpoints day28 / day56 (quarter start + 27 / + 55 days) use the same call."""
    series, td, cos = inp["series"], inp["td"], inp["cos"]
    cache = DaltCache(release_dates(inp["releases"]), inp["releases_since"])
    rows = []
    for name, co in cos.items():
        excl = config.window(co["exclusion_window"])
        head = config.window(co["headline_window"])
        rob = config.window(co["robustness_window"]) if co.get("robustness_window") else None
        for target in targets_of(co):
            major = major_break_quarters(name, target)
            for variant in variants:
                dfn = cache.fn(variant)
                for q, cp in [(q, cp) for q in qrange(CALL_FIRST_Q, head[1]) for cp in checkpoints]:
                    asof = F.checkpoint_asof(q, cp)
                    core = live.calls_at(name, q, asof, series, td, cos, target, dalt_fn=dfn)
                    a_cur, a_prev = td.get(name, target, q, "first"), td.get(name, target, q - 1, "first")
                    d_act = None if a_cur is None or a_prev is None else a_cur["yoy_pct"] - a_prev["yoy_pct"]
                    if a_cur is not None and pd.Timestamp(a_cur["filed"]).date() < asof:
                        raise F.DataError(f"{name} {target} {q}: first report filed before asof {asof}")
                    m1, m2 = td.get(name, target, q - 1, "asof", asof), td.get(name, target, q - 2, "asof", asof)
                    d_mom = None if m1 is None or m2 is None else m1["yoy_pct"] - m2["yoy_pct"]
                    actual = _dir(d_act)
                    mom = _dir(d_mom)
                    for c in core:
                        if variant == "ewr" and c["source"] in VOLUME_SOURCES:
                            continue                     # volume call is unchanged by the Wikipedia variant
                        pred = c["call"] if c["status"] == "ok" else None
                        if pred is not None and pred.startswith("no call"):
                            pred = "no call"
                        yhat = c["yhat_pct"]
                        base = c["t_q_minus_1_pct"]
                        rows.append({
                            "name": name, "quarter": str(q), "source": c["source"], "target": target,
                            "variant": variant, "checkpoint": cp, "asof": asof,
                            "clean": d_clean(q, excl), "in_headline": head[0] <= q <= head[1] and d_clean(q, excl),
                            "in_robustness_window": bool(rob and rob[0] <= q <= rob[1] and d_clean(q, excl)),
                            "major_break_dropped": (q in major) or ((q - 1) in major),
                            "alt_q": c["alt_q"], "alt_q_minus_1": c["alt_q_minus_1"], "d_alt": c["d_alt"],
                            "inputs_q": c["inputs_q"], "inputs_q_minus_1": c["inputs_q_minus_1"],
                            "combined_detail": c["combined_detail"],
                            "status": c["status"], "prediction": pred if pred else c["status"],
                            "t_q_first_pct": None if a_cur is None else a_cur["yoy_pct"],
                            "t_q_minus_1_first_pct": None if a_prev is None else a_prev["yoy_pct"],
                            "d_t_actual_pp": d_act, "actual": actual if actual else "not run (no like-for-like base)",
                            "t_q_first_filed": None if a_cur is None else a_cur["filed"],
                            "t_q_first_url": None if a_cur is None else a_cur["source_url"],
                            "correct": _correct(pred, actual),
                            "momentum_d_t_q_minus_1_pp": d_mom,
                            "momentum_prediction": mom if mom else "not run (no like-for-like base at asof)",
                            "momentum_correct": _correct(mom if mom != "flat" else "no call", actual) if mom else None,
                            "t_q_minus_1_asof_pct": base, "beta_pp_per_unit_d_alt": c["beta_pp_per_unit_d_alt"],
                            "beta_basis": c["beta_basis"], "n_pairs": c["n_pairs"], "pair_quarters": c["pair_quarters"],
                            "yhat_pct": yhat, "magnitude_status": c["magnitude_status"],
                            "abs_err_model_pp": None if yhat is None or a_cur is None else abs(yhat - a_cur["yoy_pct"]),
                            "abs_err_baseline_pp": None if base is None or a_cur is None else abs(base - a_cur["yoy_pct"]),
                        })
    df = pd.DataFrame(rows)
    if df.duplicated(["name", "quarter", "source", "target", "variant", "checkpoint"]).any():
        raise F.DataError("duplicate call keys")
    return df


# ------------------------------------------------------------------------------------- scoring


def _reasons(sub: pd.DataFrame, cols: dict[str, pd.Series]) -> str:
    out = []
    for lab, mask in cols.items():
        n = int(mask.sum())
        if n:
            qs = ",".join(sub.loc[mask, "quarter"])
            out.append(f"{lab}: {n} ({qs})")
    return "; ".join(out)


def score_direction(sub: pd.DataFrame) -> dict:
    """Direction metrics on the same sample for the model, momentum and the 50% baseline."""
    no_model = sub.correct.isna()
    no_mom = sub.momentum_correct.isna() & ~no_model
    no_act = sub.actual.str.startswith("not run")
    keep = ~(sub.correct.isna() | sub.momentum_correct.isna() | no_act)
    s = sub[keep]
    n = len(s)
    hits = int(s.correct.astype(bool).sum())
    mh = int(s.momentum_correct.astype(bool).sum())
    h = min_hits(n) if n else None
    p = float(binom.sf(hits - 1, n, 0.5)) if n else None
    excl = _reasons(sub, {"model not run": no_model & ~no_act,
                          "momentum not run": no_mom & ~no_act,
                          "actual not run": no_act})
    return {"N_realised": n, "first_q": s.quarter.min() if n else "", "last_q": s.quarter.max() if n else "",
            "hits": hits, "hit_rate": hits / n if n else None, "min_hits_p05_realised": h,
            "meets_min_hits": (hits >= h) if h is not None else False, "binom_p_one_sided": p,
            "momentum_hits": mh, "momentum_hit_rate": mh / n if n else None, "baseline_50_hit_rate": 0.5,
            "beats_50": (hits / n > 0.5) if n else False, "beats_momentum": hits > mh if n else False,
            "beats_both_baselines": (hits / n > 0.5 and hits > mh) if n else False,
            "n_no_call_d_alt_zero": int((s.prediction == "no call").sum()),
            "n_excluded_same_sample": int((~keep).sum()), "excluded_detail": excl,
            "quarters_scored": ",".join(s.quarter)}


def score_magnitude(sub: pd.DataFrame) -> dict:
    keep = sub.abs_err_model_pp.notna() & sub.abs_err_baseline_pp.notna()
    s = sub[keep]
    n = len(s)
    mae, mae_b = (float(s.abs_err_model_pp.mean()), float(s.abs_err_baseline_pp.mean())) if n else (None, None)
    reasons = {}
    for st, g in sub[~keep].groupby("magnitude_status"):
        reasons[st if st != "ok" else "actual not run"] = sub.index.isin(g.index)
    return {"N_realised": n, "first_q": s.quarter.min() if n else "", "last_q": s.quarter.max() if n else "",
            "mae_pp": mae, "mae_baseline_pp": mae_b,
            "mae_minus_baseline_pp": None if n == 0 else mae - mae_b,
            "mae_ratio_to_baseline": None if n == 0 or mae_b == 0 else mae / mae_b,
            "beats_baseline": (mae < mae_b) if n else False,
            "beta_basis_counts": "; ".join(f"{k}: {v}" for k, v in s.beta_basis.value_counts().items()),
            "n_excluded_same_sample": int((~keep).sum()), "excluded_detail": _reasons(sub, reasons),
            "quarters_scored": ",".join(s.quarter)}


def _window_mask(calls: pd.DataFrame, window: str) -> pd.Series:
    if window == "headline":
        return calls.in_headline
    if window == "robustness_2024Q1_2026Q3":
        return calls.in_robustness_window
    if window == "excl_major_breaks":
        return calls.in_headline & ~calls.major_break_dropped
    raise ValueError(window)


ANALYSES = [  # (analysis label, window, variant)
    ("headline", "headline", "base"),
    ("robustness (i) US 2024Q1-2026Q3", "robustness_2024Q1_2026Q3", "base"),
    ("robustness (ii) MAJOR structural-break quarters removed", "excl_major_breaks", "base"),
    ("robustness (iii) Wikipedia earnings-day windows removed", "headline", "ewr"),
]


def cell_list(cos: dict) -> list[tuple[str, str, str]]:
    """Every (name, source, target) cell of the results table, incl. not-run ones (rule 5)."""
    out = []
    for name, co in cos.items():
        srcs = [co["volume_source"]] + ([co["volume_source_fallback"]] if co.get("volume_source_fallback") else []) \
            + ["wikipedia", "combined"]
        for t in ("y", "k"):
            for s in srcs:
                out.append((name, s, t))
    return out


def not_run_reason(name: str, source: str, target: str, co: dict, analysis: str, model: str) -> str | None:
    if target == "k" and not co.get("kpi"):
        return "not run (company discloses no volume KPI: revenue only)"
    if source == co.get("volume_source_fallback"):
        return "not run (fallback not triggered; docs/decisions_log.md)"
    if model == "magnitude" and source == "combined":
        return live.COMBINED_NOT_RUN_MAG
    if analysis.startswith("robustness (i)") and not co.get("robustness_window"):
        return "not run (no robustness window for this name; hypotheses.md 3.7)"
    if analysis.startswith("robustness (iii)") and source not in ("wikipedia", "combined"):
        return "n/a (variant changes the Wikipedia series only; volume call identical to headline)"
    return None


def results(calls: pd.DataFrame, cos: dict) -> pd.DataFrame:
    preds = predictions_from_hypotheses()
    pw = power_table().set_index(["name", "source", "target"])
    rows = []
    for analysis, window, variant in ANALYSES:
        cv = calls[(calls.variant == variant) & _window_mask(calls, window)]
        for name, source, target in cell_list(cos):
            co = cos[name]
            fam = (analysis == "headline" and source != co.get("volume_source_fallback")
                   and (target == "y" or co.get("kpi")))
            # power table N (HKIA rows: same N as the CAAC rows, hypotheses.md section 6); none for window (i)
            key = (name, co["volume_source"] if source == co.get("volume_source_fallback") else source, target)
            prereg_n = None
            if key in pw.index and window != "robustness_2024Q1_2026Q3":
                prereg_n = int(pw.loc[key, "N_excl_major_breaks" if window == "excl_major_breaks" else "N"])
            for model in ("direction", "magnitude"):
                base = {"analysis": analysis, "name": name, "source": source, "target": target, "model": model,
                        "family_member": bool(fam and model == "direction"),
                        "hypothesis": preds.get((name, source, target), "n/a (no KPI)" if target == "k" else ""),
                        "N_prereg": prereg_n,
                        "tsa_note": ("identical call for all six US names each quarter: not independent across names"
                                     if source == "tsa" else "")}
                reason = not_run_reason(name, source, target, co, analysis, model)
                if reason:
                    rows.append({**base, "status": reason, "N_realised": 0})
                    continue
                sub = cv[(cv.name == name) & (cv.source == source) & (cv.target == target)].sort_values("quarter")
                m = score_direction(sub) if model == "direction" else score_magnitude(sub)
                st = "ok" if m["N_realised"] else "not run (no scoreable quarter)"
                if window == "excl_major_breaks" and m["N_realised"] < BREAK_ROBUSTNESS_MIN_N:
                    st += "; robustness not informative (N < 6)"
                rows.append({**base, "status": st, **m})
    df = pd.DataFrame(rows)
    # Benjamini-Hochberg over the 39 pre-registered family cells (hypotheses.md 3.7), on the binomial
    # one-sided p (reference test). The placebo-based q-value is added in Session 5.
    fam = df.family_member & df.binom_p_one_sided.notna()
    if fam.sum() != 39:
        raise ValueError(f"multiple-testing family has {int(fam.sum())} cells, hypotheses.md 3.7 fixes 39")
    df["bh_q_binom"] = np.nan
    df.loc[fam, "bh_q_binom"] = multipletests(df.loc[fam, "binom_p_one_sided"], method="fdr_bh")[1]
    return df


def tsa_dependence(calls: pd.DataFrame) -> pd.DataFrame:
    """One row per headline quarter: the single TSA call and how it scored for each US name."""
    t = calls[(calls.source == "tsa") & (calls.variant == "base") & calls.in_headline]
    rows = []
    for (q, target), g in t.groupby(["quarter", "target"]):
        if g.prediction.nunique() != 1 or g.d_alt.round(12).nunique() != 1:
            raise AssertionError(f"TSA call differs across names in {q}")
        r = {"quarter": q, "target": target, "tsa_d_alt": g.d_alt.iloc[0], "tsa_call": g.prediction.iloc[0]}
        for _, x in g.iterrows():
            r[f"{x['name']}_correct"] = x.correct
        sc = g.correct.dropna()
        r["names_scored"], r["names_hit"] = len(sc), int(sc.astype(bool).sum())
        rows.append(r)
    return pd.DataFrame(rows)


def bkng_k_rounding_check(inp: dict) -> pd.DataFrame:
    """Data-quality note: sign(d_k) from rounded room-night levels vs from Booking's stated Y/Y %."""
    vals = pd.read_csv(REPO_ROOT / "data/processed/release_values.csv", dtype={"accession": str})
    st = vals[(vals.name == "BKNG") & (vals.metric == "kpi") & (vals.kind == "stated_yoy_pct")]
    td = inp["td"]
    co = inp["cos"]["BKNG"]
    head = config.window(co["headline_window"])

    def stated_first(q):
        x = st[st.quarter == str(q)].sort_values(["filed", "accession"])
        return None if x.empty else x.iloc[0]

    rows = []
    for q in qrange(*head):
        a, b = td.get("BKNG", "k", q, "first"), td.get("BKNG", "k", q - 1, "first")
        sa, sb = stated_first(q), stated_first(q - 1)
        d_lv = a["yoy_pct"] - b["yoy_pct"]
        d_st = None if sa is None or sb is None else float(sa.value) - float(sb.value)
        rows.append({"quarter": str(q), "k_levels_pct": a["yoy_pct"], "k_prev_levels_pct": b["yoy_pct"],
                     "d_k_levels_pp": d_lv, "k_stated_pct": None if sa is None else sa.value,
                     "k_prev_stated_pct": None if sb is None else sb.value, "d_k_stated_pp": d_st,
                     "sign_differs": None if d_st is None else bool(np.sign(d_lv) != np.sign(d_st)),
                     "stated_source_url": None if sa is None else sa.source_url})
    return pd.DataFrame(rows)


def results_db(res: pd.DataFrame, cos: dict, db: Path = REPO_ROOT / "data" / "nowcast.db",
               sql_dir: Path = REPO_ROOT / "sql") -> pd.DataFrame:
    """Load the results into data/nowcast.db (sql/results_schema.sql) and run sql/results_summary.sql
    (name x source relevancy matrix). Placebo / GREEN columns are filled once Session 5 has run."""
    order = {n: i for i, n in enumerate(cos)}
    col = lambda c: res[c] if c in res.columns else pd.Series([None] * len(res), index=res.index)
    t = pd.DataFrame({
        "analysis": res.analysis, "name_order": res.name.map(order), "name": res.name, "source": res.source,
        "target": res.target, "model": res.model, "status": res.status,
        "family_member": res.family_member.astype(int), "n_prereg": res.N_prereg,
        "n_realised": res.N_realised.astype(int), "hits": res.hits, "min_hits_p05": res.min_hits_p05_realised,
        "momentum_hits": res.momentum_hits, "beats_both": res.beats_both_baselines.map({True: 1, False: 0}),
        "binom_p": res.binom_p_one_sided, "bh_q_binom": res.bh_q_binom, "mae_pp": res.mae_pp,
        "mae_baseline_pp": res.mae_baseline_pp, "placebo_percentile": col("placebo_percentile"),
        "bh_q_placebo": col("bh_q_placebo"),
        "green": col("green").map({True: 1, False: 0})})
    con = sqlite3.connect(db)
    con.executescript((sql_dir / "results_schema.sql").read_text())
    t.to_sql("results_cells", con, if_exists="append", index=False)
    con.commit()
    m = pd.read_sql_query((sql_dir / "results_summary.sql").read_text(), con)
    con.close()
    return m
