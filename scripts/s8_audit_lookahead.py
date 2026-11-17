"""Session 8 audit, item 1 (look-ahead). No network. Writes outputs/tables/audit_*.csv.

    .venv/bin/python scripts/s8_audit_lookahead.py

(a) audit_asof_minus_1.csv / audit_asof_minus_1_cells.csv: the whole walk-forward backtest is rerun with EVERY
    as-of date moved one day earlier (the call's asof and the quarter-end asof of every past quarter used for
    the combined std and the magnitude pairs). A point-in-time pipeline must give materially the same calls.
(b) audit_restated_quarters.csv: every (name, quarter) whose revenue has more than one filed value; for each,
    the version the backtest's as-of view selects at the quarter-end asof of q+1 .. q+5 and the value filed later.
(c) audit_caac_publication.csv: every CAAC month used by a backtest or lead-time call, with its recorded
    publication date and the earliest asof at which any call used it (must be >= publication date).
"""
import datetime as dt
import sys

import pandas as pd

sys.path.insert(0, "src")
from nowcast import evaluate as E, features as F, placebo as P  # noqa: E402
from nowcast.quarters import Quarter, qrange  # noqa: E402
from nowcast.rawstore import REPO_ROOT  # noqa: E402
from nowcast.revenue import asof_view  # noqa: E402

T = REPO_ROOT / "outputs" / "tables"
KEY = ["name", "quarter", "source", "target", "variant", "checkpoint"]


def asof_minus_1(inp: dict) -> tuple[pd.DataFrame, pd.DataFrame]:
    base = pd.read_csv(T / "calls.csv")
    orig = F.checkpoint_asof
    F.checkpoint_asof = lambda q, cp: orig(q, cp) - dt.timedelta(days=1)
    try:
        inp["td"]._cache.clear()
        shifted = E.make_calls(inp)
        res_s = E.results(shifted, inp["cos"])
        res_s = P.add_shuffle(res_s, shifted, {a: v for a, _, v in E.ANALYSES})
    finally:
        F.checkpoint_asof = orig
        inp["td"]._cache.clear()
    res_b = pd.read_csv(T / "results.csv")
    shifted = shifted.copy()
    shifted["asof"] = shifted["asof"].astype(str)
    m = base.merge(shifted, on=KEY, suffixes=("", "_m1"), how="outer", indicator=True)
    if (m._merge != "both").any():
        raise SystemExit("asof-1 rerun has a different set of call rows")
    m["prediction_changed"] = m.prediction.astype(str) != m.prediction_m1.astype(str)
    m["momentum_changed"] = m.momentum_prediction.astype(str) != m.momentum_prediction_m1.astype(str)
    norm = lambda x: x.map(lambda v: "" if pd.isna(v) else str(bool(v)))
    m["correct_changed"] = norm(m.correct) != norm(m.correct_m1)
    m["abs_d_alt_diff"] = (m.d_alt - m.d_alt_m1).abs()
    m["abs_yhat_diff_pp"] = (m.yhat_pct - m.yhat_pct_m1).abs()
    cols = KEY + ["in_headline", "asof", "asof_m1", "d_alt", "d_alt_m1", "abs_d_alt_diff", "prediction",
                  "prediction_m1", "prediction_changed", "momentum_prediction", "momentum_prediction_m1",
                  "momentum_changed", "correct", "correct_m1", "correct_changed", "yhat_pct", "yhat_pct_m1",
                  "abs_yhat_diff_pp"]
    calls_cmp = m[cols]
    h = res_s[res_s.analysis == "headline"]
    ck = ["name", "source", "target", "model"]
    c = res_b.merge(h, on=ck, suffixes=("", "_m1"))
    cells = c[ck + ["family_member", "status", "status_m1", "N_realised", "N_realised_m1", "hits", "hits_m1",
                    "momentum_hits", "momentum_hits_m1", "meets_min_hits", "meets_min_hits_m1",
                    "beats_both_baselines", "beats_both_baselines_m1", "placebo_percentile",
                    "placebo_percentile_m1", "green", "green_m1", "mae_pp", "mae_pp_m1"]].copy()
    cells["hits_diff"] = cells.hits_m1 - cells.hits
    cells["mae_diff_pp"] = cells.mae_pp_m1 - cells.mae_pp
    return calls_cmp, cells


def restated(inp: dict) -> pd.DataFrame:
    v = pd.read_csv(REPO_ROOT / "data/processed/revenue_pit.csv", dtype={"accession": str})
    v["filed_d"] = pd.to_datetime(v.filed).dt.date
    rows = []
    for (name, q), g in v.groupby(["name", "quarter"]):
        g = g.sort_values(["filed", "accession"])
        if g.value.round(6).nunique() < 2:
            continue
        qq = Quarter.parse(q)
        for k in range(1, 6):
            asof = F.checkpoint_asof(qq + k, "qend")
            av = asof_view(v[v.name == name], asof)
            sel = av[av.quarter == q]
            later = g[g.filed_d >= asof]
            if sel.empty:
                rows.append({"name": name, "quarter": q, "asof": asof, "selected_value": None})
                continue
            s = sel.iloc[0]
            if pd.Timestamp(s.filed).date() >= asof:
                raise SystemExit(f"LOOK-AHEAD: {name} {q} at {asof} selected a version filed {s.filed}")
            expect = g[g.filed_d < asof].iloc[-1]
            rows.append({"name": name, "quarter": q, "asof": asof, "selected_value": s.value,
                         "selected_filed": s.filed, "selected_accession": s.accession, "selected_form": s.form,
                         "selected_method": s.method,
                         "selected_is_latest_filed_before_asof": bool(s.filed == expect.filed),
                         "n_versions_total": len(g), "n_versions_filed_on_or_after_asof": len(later),
                         "later_values": ";".join(f"{x.value:.3f}@{x.filed}" for x in later.itertuples()),
                         "max_abs_diff_vs_later": float((later.value - s.value).abs().max()) if len(later) else 0.0})
    return pd.DataFrame(rows)


def caac_publication(inp: dict) -> pd.DataFrame:
    s = inp["series"]["caac"]
    pub = s.obs.set_index("obs_date").published
    first_use: dict = {}
    head = Quarter.parse(inp["cos"]["TCOM"]["headline_window"][1])
    for q in qrange(E.CALL_FIRST_Q, head):
        for cp in F.CHECKPOINTS:
            asof = F.checkpoint_asof(q, cp)
            r = F.d_alt(s, q, asof)
            for u in r["_used"]:
                for d in u.obs_date:
                    if d not in first_use or asof < first_use[d][0]:
                        first_use[d] = (asof, f"{q} {cp}")
    rows = []
    for m in sorted(first_use):
        a, where = first_use[m]
        if pub[m] > a:
            raise SystemExit(f"LOOK-AHEAD: CAAC {m} published {pub[m]} used at asof {a}")
        rows.append({"month": m.strftime("%Y-%m"), "published": pub[m], "earliest_asof_used": a,
                     "earliest_use": where, "days_published_before_use": (a - pub[m]).days})
    return pd.DataFrame(rows)


def main() -> None:
    inp = E.load_inputs()
    calls_cmp, cells = asof_minus_1(inp)
    calls_cmp.to_csv(T / "audit_asof_minus_1.csv", index=False, float_format="%.6f")
    cells.to_csv(T / "audit_asof_minus_1_cells.csv", index=False, float_format="%.6f")
    h = calls_cmp[calls_cmp.in_headline & (calls_cmp.variant == "base")]
    fam = cells[cells.family_member]
    print(f"asof-1: {len(calls_cmp)} calls; prediction changed {int(calls_cmp.prediction_changed.sum())} "
          f"(headline base {int(h.prediction_changed.sum())}); momentum changed {int(calls_cmp.momentum_changed.sum())}; "
          f"correct changed {int(calls_cmp.correct_changed.sum())}; max |d_alt diff| {calls_cmp.abs_d_alt_diff.max():.6f}; "
          f"max |yhat diff| {calls_cmp.abs_yhat_diff_pp.max():.4f} pp")
    print(f"family cells with a different hit count: {int((fam.hits_diff != 0).sum())} of {len(fam)}; "
          f"different N: {int((fam.N_realised != fam.N_realised_m1).sum())}; "
          f"max |MAE diff| {cells.mae_diff_pp.abs().max():.4f} pp; GREEN changed: "
          f"{int((fam.green.astype(bool) != fam.green_m1.astype(bool)).sum())}; reach-min-hits changed: "
          f"{int((fam.meets_min_hits.astype(bool) != fam.meets_min_hits_m1.astype(bool)).sum())}")
    rs = restated(inp)
    rs.to_csv(T / "audit_restated_quarters.csv", index=False, float_format="%.6f")
    print(f"restated: {rs[['name', 'quarter']].drop_duplicates().shape[0]} (name, quarter) with >1 filed value; "
          f"{len(rs)} as-of checks; all select the latest version filed before asof: "
          f"{bool(rs.selected_is_latest_filed_before_asof.all())}; max later diff {rs.max_abs_diff_vs_later.max():.3f}")
    cp = caac_publication(inp)
    cp.to_csv(T / "audit_caac_publication.csv", index=False)
    print(f"CAAC: {len(cp)} months used; min days published before first use {int(cp.days_published_before_use.min())}")


if __name__ == "__main__":
    main()
