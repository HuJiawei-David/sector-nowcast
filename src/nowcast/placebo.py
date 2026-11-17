"""Session 5: placebos, multiple testing, inflections and lead time (docs/hypotheses.md section 1).

Placebo (a), shuffle (PRIMARY significance test): within a cell's scored quarters (the same sample the
cell's hit count uses), the call values d_alt (combined: sum d_alt/std) are permuted across quarters,
1000 runs, fixed seed. This keeps the share of accelerate / decelerate calls. Each run's hits are counted
against the unchanged actual directions.
    placebo_percentile = 100 x share of runs with FEWER hits than the cell (strictly; ties count against
                         the cell, so the definition is conservative)
    placebo_p          = (1 + runs with hits >= the cell's hits) / (1 + runs)
Magnitude cells (secondary): d_alt permuted the same way while each quarter keeps its own y_{q-1} and
fitted beta; percentile = 100 x share of runs with a LARGER MAE than the cell.

Placebo (b), wrong-company (Wikipedia direction cells only): the cell's quarters are scored with each
other name's Wikipedia d_alt at the same asof. wrong_company_percentile = 100 x share of the other
names' series that score FEWER hits than the name's own series. TSA is one series for all six US names
and CAAC maps to one name, so (b) is undefined for them ("n/a: same series" / "n/a: single name").

GREEN (direction cells): beats both baselines (50% and momentum, same quarters) AND placebo
percentile >= 95. Multiple testing over the 39 pre-registered family cells (hypotheses 3.7):
cells tested, expected by chance (0.05 x cells), GREEN found, BH q-values on the placebo p.

Inflection: a clean quarter q (target d_q clean, headline window) with sign(d_q) != sign(d_{q-1}),
d from first-reported values (calls.csv d_t_actual_pp). Caught = the quarter-end call is correct.

Lead time: hit rate at day28 / day56 / quarter end (asof = quarter start + 27 / + 55 days / quarter
end) and the median number of weeks from each checkpoint to the earnings release date (8-K Item 2.02 /
6-K filing date of q's results release).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import binom
from statsmodels.stats.multitest import multipletests

from .power import min_hits

SEED = 20261110          # prereg date; one fixed seed, a fresh generator per cell
RUNS = 1000
GREEN_PCT = 95.0
SIGN = {"accelerate": 1, "decelerate": -1, "flat": 0, "no call": 0}


def _sign(x) -> np.ndarray:
    return np.sign(np.asarray(x, float)).astype(int)


def hits_of(pred_sign: np.ndarray, actual_sign: np.ndarray) -> int:
    """A call scores only if it is non-zero and equals a non-zero actual (zero call or flat actual = miss)."""
    return int(((pred_sign == actual_sign) & (pred_sign != 0)).sum())


def shuffle_direction(d_alt: np.ndarray, actual_sign: np.ndarray, runs: int = RUNS, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    obs = hits_of(_sign(d_alt), actual_sign)
    ps = _sign(d_alt)
    sims = np.array([hits_of(rng.permutation(ps), actual_sign) for _ in range(runs)])
    return {"placebo_hits_obs": obs, "placebo_mean_hits": float(sims.mean()),
            "placebo_percentile": 100.0 * float((sims < obs).mean()),
            "placebo_p": float((1 + (sims >= obs).sum()) / (1 + runs)), "_sims": sims}


def shuffle_magnitude(d_alt, t_prev, beta, actual, runs: int = RUNS, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    d_alt, t_prev, beta, actual = (np.asarray(x, float) for x in (d_alt, t_prev, beta, actual))
    mae = float(np.abs(t_prev + beta * d_alt - actual).mean())
    sims = np.array([np.abs(t_prev + beta * rng.permutation(d_alt) - actual).mean() for _ in range(runs)])
    return {"placebo_mae_obs": mae, "placebo_mean_mae": float(sims.mean()),
            "placebo_percentile": 100.0 * float((sims > mae).mean()),
            "placebo_p": float((1 + (sims <= mae).sum()) / (1 + runs))}


def cell_rows(calls: pd.DataFrame, r: pd.Series, variant: str) -> pd.DataFrame:
    """The scored quarters of a results row (its `quarters_scored`), in quarter order."""
    qs = [q for q in str(r.quarters_scored).split(",") if q and q != "nan"]
    c = calls[(calls.name == r["name"]) & (calls.source == r.source) & (calls.target == r.target)
              & (calls.variant == variant) & (calls.checkpoint == "qend") & calls.quarter.isin(qs)]
    c = c.sort_values("quarter")
    if len(c) != len(qs):
        raise ValueError(f"{r['name']} {r.source} {r.target}: {len(c)} call rows for {len(qs)} scored quarters")
    return c


def actual_sign(c: pd.DataFrame) -> np.ndarray:
    return c.actual.map(SIGN).to_numpy(int)


def add_shuffle(res: pd.DataFrame, calls: pd.DataFrame, variant_of: dict[str, str]) -> pd.DataFrame:
    res = res.copy()
    for col in ("placebo_percentile", "placebo_p", "placebo_mean_hits", "placebo_mean_mae"):
        res[col] = np.nan
    res["placebo_status"] = ""
    for i, r in res.iterrows():
        if not r.N_realised:
            res.at[i, "placebo_status"] = "not run (cell not run)"
            continue
        c = cell_rows(calls, r, variant_of[r.analysis])
        if r.model == "direction":
            out = shuffle_direction(c.d_alt.to_numpy(float), actual_sign(c))
            if out["placebo_hits_obs"] != int(r.hits):
                raise ValueError(f"placebo hit count {out['placebo_hits_obs']} != results {r.hits} ({r['name']} {r.source})")
            res.at[i, "placebo_mean_hits"] = out["placebo_mean_hits"]
        else:
            out = shuffle_magnitude(c.d_alt, c.t_q_minus_1_asof_pct, c.beta_pp_per_unit_d_alt, c.t_q_first_pct)
            if abs(out["placebo_mae_obs"] - r.mae_pp) > 1e-9:
                raise ValueError("placebo MAE differs from results")
            res.at[i, "placebo_mean_mae"] = out["placebo_mean_mae"]
        res.at[i, "placebo_percentile"] = out["placebo_percentile"]
        res.at[i, "placebo_p"] = out["placebo_p"]
        res.at[i, "placebo_status"] = f"ok ({RUNS} runs, seed {SEED})"
    d = res.model == "direction"
    res["green"] = d & res.beats_both_baselines.fillna(False).astype(bool) & (res.placebo_percentile >= GREEN_PCT)
    fam = res.family_member.astype(bool)
    res["bh_q_placebo"] = np.nan
    res.loc[fam, "bh_q_placebo"] = multipletests(res.loc[fam, "placebo_p"], method="fdr_bh")[1]
    return res


# ------------------------------------------------------------------------------------- wrong company


def wrong_company(res: pd.DataFrame, calls: pd.DataFrame, wiki_dalt, variant_of: dict[str, str]
                  ) -> tuple[pd.DataFrame, pd.DataFrame]:
    """wiki_dalt(other_name, quarter_str, asof) -> that name's Wikipedia d_alt at asof (base variant).
    Run for the base-variant analyses (headline, robustness (i), (ii)); not for the ewr variant."""
    res = res.copy()
    res["wrong_company"] = ""
    res["wrong_company_percentile"] = np.nan
    names = sorted(res.name.unique())
    pairs = []
    for i, r in res.iterrows():
        if r.model != "direction":
            continue
        if r.source in ("tsa",):
            res.at[i, "wrong_company"] = "n/a: same series (TSA is one national series for all six US names)"
            continue
        if r.source in ("caac", "hkia"):
            res.at[i, "wrong_company"] = "n/a: single name (maps to TCOM only)"
            continue
        if r.source == "combined":
            res.at[i, "wrong_company"] = "n/a: placebo (b) is defined for Wikipedia cells only"
            continue
        if not r.N_realised:
            res.at[i, "wrong_company"] = "not run (cell not run)"
            continue
        if variant_of[r.analysis] != "base":
            res.at[i, "wrong_company"] = "not run (placebo (b) is computed for the base Wikipedia series only)"
            continue
        c = cell_rows(calls, r, "base")
        act = actual_sign(c)
        own = hits_of(_sign(c.d_alt), act)
        others = {}
        for o in names:
            if o == r["name"]:
                continue
            d = np.array([wiki_dalt(o, q, a) for q, a in zip(c.quarter, c["asof"])], float)
            others[o] = hits_of(_sign(d), act)
            pairs.append({"analysis": r.analysis, "name": r["name"], "target": r.target, "series_of": o,
                          "N": len(c), "hits": others[o], "own_hits": own})
        res.at[i, "wrong_company"] = "; ".join(f"{k} {v}/{len(c)}" for k, v in others.items())
        res.at[i, "wrong_company_percentile"] = 100.0 * np.mean([v < own for v in others.values()])
    return res, pd.DataFrame(pairs)


def multiple_testing_line(res: pd.DataFrame) -> dict:
    fam = res[res.family_member.astype(bool)]
    green = fam[fam.green]
    return {"direction_cells_tested": len(fam), "expected_to_pass_by_chance": round(0.05 * len(fam), 2),
            "green_found": len(green),
            "green_cells": "; ".join(f"{r['name']} {r.source} {r.target}" for _, r in green.iterrows()),
            "cells_bh_q_placebo_below_0.05": int((fam.bh_q_placebo < 0.05).sum()),
            "min_bh_q_placebo": float(fam.bh_q_placebo.min()),
            "note": ("the six TSA cells per target share one call series (identical call for all US names each "
                     "quarter), so they are not independent tests")}


# ------------------------------------------------------------------------------------- inflections


def inflections(calls: pd.DataFrame) -> pd.DataFrame:
    """Every inflection quarter (headline, clean) x source, with the quarter-end call and whether it caught it."""
    c = calls[(calls.variant == "base") & (calls.checkpoint == "qend")]
    rows = []
    for (name, target), g in c.groupby(["name", "target"]):
        act = g.drop_duplicates("quarter").set_index("quarter").d_t_actual_pp
        for q, gq in g[g.in_headline].groupby("quarter"):
            prev_q = _prev(q)
            if prev_q not in act.index or pd.isna(act[prev_q]) or pd.isna(act[q]):
                continue
            s_now, s_prev = np.sign(act[q]), np.sign(act[prev_q])
            if s_now == s_prev:
                continue
            for _, x in gq.iterrows():
                rows.append({"name": name, "target": target, "quarter": q, "source": x.source,
                             "d_t_q_minus_1_pp": act[prev_q], "d_t_q_pp": act[q],
                             "actual": x.actual, "quarter_end_call": x.prediction,
                             "caught": None if pd.isna(x.correct) else bool(x.correct),
                             "momentum_call": x.momentum_prediction,
                             "momentum_caught": None if pd.isna(x.momentum_correct) else bool(x.momentum_correct)})
    return pd.DataFrame(rows)


def _prev(q: str) -> str:
    y, n = int(q[:4]), int(q[-1])
    return f"{y - 1}Q4" if n == 1 else f"{y}Q{n - 1}"


def inflection_summary(inf: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (name, target, source), g in inf.groupby(["name", "target", "source"], sort=False):
        run = g[g.caught.notna()]
        rows.append({"name": name, "target": target, "source": source, "inflections": g.quarter.nunique(),
                     "scored": len(run), "caught": int(run.caught.astype(bool).sum()),
                     "missed": int((~run.caught.astype(bool)).sum()),
                     "not_run": int(g.caught.isna().sum()),
                     "caught_quarters": ",".join(run[run.caught.astype(bool)].quarter),
                     "missed_quarters": ",".join(run[~run.caught.astype(bool)].quarter),
                     "not_run_quarters": ",".join(g[g.caught.isna()].quarter),
                     "momentum_caught": int(g.momentum_caught.fillna(False).astype(bool).sum())})
    return pd.DataFrame(rows)


# ------------------------------------------------------------------------------------- lead time


def lead_time(calls_cp: pd.DataFrame, releases: pd.DataFrame) -> pd.DataFrame:
    """Hit rate per (name, source, target, checkpoint) on headline quarters, base variant; quarters where
    the source has no published data at the checkpoint are 'not run (no data)' and excluded (3.10)."""
    rel = releases[releases.is_amendment == 0].set_index(["name", "quarter"]).filed
    c = calls_cp[(calls_cp.variant == "base") & calls_cp.in_headline].copy()
    c["release_date"] = [pd.Timestamp(rel.get((n, q))) for n, q in zip(c.name, c.quarter)]
    if c.release_date.isna().any():
        raise ValueError("headline quarter without an earnings release date")
    c["weeks_to_release"] = (c.release_date - pd.to_datetime(c["asof"])).dt.days / 7.0
    rows = []
    order = {"day28": 0, "day56": 1, "qend": 2}
    for (name, source, target, cp), g in c.groupby(["name", "source", "target", "checkpoint"], sort=False):
        ok = g[g.correct.notna() & ~g.actual.str.startswith("not run")]
        nr = g[g.correct.isna()]
        n, h = len(ok), int(ok.correct.astype(bool).sum())
        rows.append({"name": name, "source": source, "target": target, "checkpoint": cp,
                     "checkpoint_order": order[cp], "N": n, "hits": h, "hit_rate": h / n if n else None,
                     "min_hits_p05": min_hits(n) if n else None,
                     "binom_p_one_sided": float(binom.sf(h - 1, n, 0.5)) if n else None,
                     "n_not_run": len(nr), "not_run_reasons": "; ".join(sorted(set(nr.status))),
                     "not_run_quarters": ",".join(nr.quarter),
                     "median_weeks_to_release": float(ok.weeks_to_release.median()) if n else None,
                     "min_weeks_to_release": float(ok.weeks_to_release.min()) if n else None,
                     "max_weeks_to_release": float(ok.weeks_to_release.max()) if n else None})
    out = pd.DataFrame(rows)
    return out.sort_values(["name", "target", "source", "checkpoint_order"], kind="stable").reset_index(drop=True)
