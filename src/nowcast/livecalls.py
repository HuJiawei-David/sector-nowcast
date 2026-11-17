"""Session 6: live calls (a) 2026Q4 quarter-to-date for all names, (b) the locked TCOM 2026Q3 call, with the
guidance benchmark (CLAUDE.md "GUIDANCE BENCHMARK"), base-period events and the TSA base-period sensitivity.

The per-quarter call is live.calls_at() (the same function as the backtest). A source with no published
observation inside the quarter at asof is "insufficient data" (no guess). The locked TCOM 2026Q3 call
(outputs/tables/live_calls_tcom_2026Q3.csv, Session L) is carried unchanged, never recomputed.

Guidance (config/guidance.yaml, extracted by hand, every number quoted verbatim from the release snapshot):
    midpoint      = (low + high) / 2 of the company-stated YoY range, or of the YoY implied by the level
                    range vs the q-4 level the company reports;
    guided dir.   = sign(midpoint - previous quarter's actual YoY of the same metric);
    label         = "above guidance" (call accelerate, guidance decelerate), "below guidance" (reverse),
                    "in line" (agree); a zero guided direction gets no label; "pending" if the company has
                    not reported q-1 yet; "no guidance" if it gives none.
    yhat check    = when the guided metric IS the model target: "in line" if |yhat - midpoint| <= 1.0 pp,
                    else "above" / "below".
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import numpy as np
import pandas as pd

from . import config, features as F, live
from .filings import html_to_text
from .quarters import Quarter
from .rawstore import REPO_ROOT, read_snapshot

IN_LINE_PP = 1.0
LOCKED = REPO_ROOT / "outputs/tables/live_calls_tcom_2026Q3.csv"


def guidance_config() -> dict:
    return config.load_yaml("guidance.yaml")


def snapshot_text(path: str) -> str:
    raw = read_snapshot(REPO_ROOT / path)
    t = html_to_text(raw) if ".htm" in path else raw.decode("utf-8", "replace")
    return re.sub(r"\s+", " ", t).strip()


def _mid_and_prev(g: dict, t_prev: float | None) -> tuple[float, float, float, float | None, str]:
    if "low_yoy_pct" in g:
        lo, hi = float(g["low_yoy_pct"]), float(g["high_yoy_pct"])
    else:
        lo = 100.0 * (g["low_level"] / g["base_level"] - 1.0)
        hi = 100.0 * (g["high_level"] / g["base_level"] - 1.0)
    if "prev_yoy_pct" in g:
        prev, how = float(g["prev_yoy_pct"]), "company-stated (prev_quote)"
    elif "prev_level" in g:
        prev, how = 100.0 * (g["prev_level"] / g["prev_base_level"] - 1.0), "from company-stated levels (prev_quote)"
    else:
        prev, how = t_prev, f"model t_q-1 at asof ({g.get('prev_from', '')})"
    return lo, hi, (lo + hi) / 2.0, prev, how


def guidance_for(name: str, q: Quarter, target: str, call: str, yhat: float | None, t_prev: float | None,
                 gcfg: dict, prev_by_target: dict | None = None) -> dict:
    """t_prev: the call's own target value at q-1; prev_by_target {'y': .., 'k': ..} supplies the previous
    quarter's YoY of a guided metric that is a model target but not this row's target (e.g. revenue
    guidance used as the benchmark for a KPI row)."""
    ents = [g for g in gcfg["guidance"] if g["name"] == name and g["quarter"] == str(q)
            and target in g.get("applies_to_targets", [])]
    if not ents:
        return {"guidance_label": "no guidance"}
    g = ents[0]
    if g.get("label") == "pending":
        return {"guidance_label": "pending", "guidance_note": g["note"]}
    gt = g.get("target")
    prev_val = t_prev if gt in (None, target) else (prev_by_target or {}).get(gt)
    lo, hi, mid, prev, how = _mid_and_prev(g, prev_val)
    gd = None if prev is None else float(np.sign(round(mid - prev, 9)))
    gdir = {1.0: "accelerate", -1.0: "decelerate", 0.0: "no change"}.get(gd, "n/a (no previous value)")
    if call not in ("accelerate", "decelerate"):
        label = f"n/a (call: {call})"
    elif gdir == "no change":
        label = "no label (guidance midpoint equals the previous quarter's YoY)"
    elif gdir.startswith("n/a"):
        label = gdir
    elif call == gdir:
        label = "in line"
    else:
        label = "above guidance" if call == "accelerate" else "below guidance"
    yv = ""
    if g.get("target") == target and yhat is not None:
        diff = yhat - mid
        yv = "in line" if abs(diff) <= IN_LINE_PP else ("above" if diff > 0 else "below")
        yv = f"{yv} (yhat {yhat:.2f}% vs guidance midpoint {mid:.2f}%, diff {diff:+.2f} pp)"
    return {"guidance_metric": g["metric"], "guidance_is_model_target": g.get("target") == target,
            "guidance_basis": g["basis"], "guidance_low_pct": lo, "guidance_high_pct": hi, "guidance_mid_pct": mid,
            "guidance_prev_yoy_pct": prev, "guidance_prev_basis": how, "guided_direction": gdir,
            "guidance_label": label, "yhat_vs_guidance": yv, "guidance_url": g["source_url"],
            "guidance_quote": g["quote"]}


# ------------------------------------------------------------------------------------- base period


def tsa_sensitivity(s: F.Series, q: Quarter, asof: dt.date, events: list[dict]) -> pd.DataFrame:
    """TSA alt_q / d_alt with day pairs dropped whose BASE day (d - 364) falls in an event window.
    q-1 is computed unchanged (its base year is not in the windows). Sensitivity only."""
    rows = []
    base = F.d_alt(s, q, asof)
    rows.append({"variant": "as computed (model)", "n_days": base["n_obs"], "alt_q": base["alt"],
                 "alt_q_minus_1": base["alt_prev"], "d_alt": base["d_alt"], "call": live.direction(base["d_alt"])})
    sets = []
    for e in events:
        a, b = (dt.date.fromisoformat(x) for x in e["window"])
        sets.append((e["id"], {a + dt.timedelta(days=i) for i in range((b - a).days + 1)}))
    combos = [(f"excluding base days in {i}", w) for i, w in sets]
    if len(sets) > 1:
        combos.append(("excluding base days in " + " + ".join(i for i, _ in sets), set().union(*(w for _, w in sets))))
    for lab, w in combos:
        excl = {d + dt.timedelta(days=F.SHIFT_DAYS) for d in w}       # current-year days whose base day is in w
        a = F.alt_q(s, q, asof, exclude=excl)
        rows.append({"variant": lab, "n_days": a.n_obs, "alt_q": a.value, "alt_q_minus_1": base["alt_prev"],
                     "d_alt": None if a.value is None else a.value - base["alt_prev"],
                     "call": live.direction(None if a.value is None else a.value - base["alt_prev"])})
    return pd.DataFrame(rows)


def next_earnings_estimate(releases: pd.DataFrame, name: str, q: Quarter) -> str:
    r = releases[(releases.name == name) & (releases.quarter == str(q - 4)) & (releases.is_amendment == 0)]
    if r.empty:
        return ""
    d = pd.Timestamp(r.filed.iloc[0]).date() + dt.timedelta(days=364)
    return f"{d} (estimate: {q - 4} release date + 364 days)"


# ------------------------------------------------------------------------------------- assemble


def call_label(c: dict) -> str:
    if c["status"] == "ok":
        return c["call"]
    if c["status"].startswith("not run (no data"):
        return "insufficient data"
    return c["call"]


def live_rows(name: str, q: Quarter, asof: dt.date, series: dict, td: live.TargetData, cos: dict,
              releases: pd.DataFrame, gcfg: dict, adjusted_notes: dict, base_notes: dict) -> list[dict]:
    rows = []
    targets = ["y"] + (["k"] if cos[name].get("kpi") else [])
    prev_by_target = {t: (lambda r: None if r is None else r["yoy_pct"])(td.get(name, t, q - 1, "asof", asof))
                      for t in targets}
    for target in targets:
        core = live.calls_at(name, q, asof, series, td, cos, target)
        for c in core:
            call = call_label(c)
            g = guidance_for(name, q, target, call, c["yhat_pct"], c["t_q_minus_1_pct"], gcfg, prev_by_target)
            rows.append({
                "live_call": f"(a) {q} quarter-to-date", "name": name, "quarter": str(q), "source": c["source"],
                "target": target, "asof": asof, "alt_q": c["alt_q"], "alt_q_minus_1": c["alt_q_minus_1"],
                "d_alt": c["d_alt"], "status": c["status"], "call": call,
                "t_q_minus_1_pct": c["t_q_minus_1_pct"], "beta_pp_per_unit_d_alt": c["beta_pp_per_unit_d_alt"],
                "beta_basis": c["beta_basis"], "n_pairs": c["n_pairs"], "pair_quarters": c["pair_quarters"],
                "yhat_pct": c["yhat_pct"], "magnitude_status": c["magnitude_status"],
                "inputs_q": c["inputs_q"], "inputs_q_minus_1": c["inputs_q_minus_1"],
                "combined_detail": c["combined_detail"], **g,
                "adjusted_metric_note": adjusted_notes.get((name, target), ""),
                "base_period_notes": " || ".join(x for x in (live.break_notes(name, q, target),
                                                             base_notes.get(name, "")) if x),
                "next_earnings_estimate": next_earnings_estimate(releases, name, q),
                "score": "not yet reported"})
    return rows


def locked_rows(releases: pd.DataFrame, reported: bool, actual: dict | None) -> list[dict]:
    """The Session L forward call, carried unchanged (values as locked), plus its score if reported."""
    lk = pd.read_csv(LOCKED, keep_default_na=False)
    out = []
    for _, r in lk.iterrows():
        num = lambda v: None if v == "" else float(v)
        score = "not yet reported (no Q3 2026 results 6-K filed by the run date)"
        if reported and actual is not None and r["call"] in ("accelerate", "decelerate"):
            hit = (actual["d_y"] > 0) == (r["call"] == "accelerate") and actual["d_y"] != 0
            score = f"{'HIT' if hit else 'MISS'}: actual d_y {actual['d_y']:+.2f} pp (first results 6-K)"
        out.append({
            "live_call": "(b) 2026Q3 LOCKED forward call (Session L, commit 03746aa, asof 2026-11-10)",
            "name": r["name"], "quarter": r["quarter"], "source": r["source"], "target": "y", "asof": r["asof"],
            "alt_q": num(r["alt_q"]), "alt_q_minus_1": num(r["alt_q_minus_1"]), "d_alt": num(r["d_alt"]),
            "status": r["status"], "call": r["call"], "t_q_minus_1_pct": num(r["y_q_minus_1_pct"]),
            "beta_pp_per_unit_d_alt": num(r["beta_pp_per_unit_d_alt"]), "beta_basis": r["beta_basis"],
            "n_pairs": num(r["n_pairs"]), "pair_quarters": r["pair_quarters"], "yhat_pct": num(r["yhat_pct"]),
            "magnitude_status": r["magnitude_status"], "inputs_q": r["inputs_q"],
            "inputs_q_minus_1": r["inputs_q_minus_1"], "combined_detail": r["combined_detail"],
            "guidance_label": r["guidance_label"], "guidance_url": r["guidance_url"],
            "base_period_notes": r["notes"], "next_earnings_estimate": next_earnings_estimate(releases, "TCOM", Quarter(2026, 3)),
            "score": score})
    return out
