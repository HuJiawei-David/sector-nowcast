"""Session 6: live calls + Excel tracker, from the refreshed snapshots (no network here; pulls are
scripts/s3_pull.py and scripts/s6_pull_events.py).

    .venv/bin/python scripts/s6_live.py

Live-call asof = features.data_run_date() of the LATEST snapshots: the latest date on which every daily
source has all its observations published. The S4/S5 backtest stays on the pinned S3 snapshots.
Outputs
  outputs/tables/live_calls.csv               (a) 2026Q4 QTD, all names, y and k; (b) locked TCOM 2026Q3 rows
  outputs/tables/live_tsa_sensitivity.csv     TSA 2026Q4 QTD with/without base-period event days (sensitivity)
  outputs/tables/snapshot_revision_check.csv  refreshed vs backtest snapshots on overlapping days
  outputs/tables/wikipedia_revision_effect.csv  2026Q2/Q3 quarter-end Wikipedia d_alt, backtest vs refreshed snapshots
  outputs/tracker/sector_nowcast_tracker.xlsx
"""
import json
import sys

import pandas as pd

sys.path.insert(0, "src")
from nowcast import config, features as F, live, livecalls as LC, tracker  # noqa: E402
from nowcast.quarters import Quarter  # noqa: E402
from nowcast.rawstore import RAW_DIR, REPO_ROOT, read_snapshot  # noqa: E402

T = REPO_ROOT / "outputs" / "tables"
Q = Quarter(2026, 4)


def revision_check(new: dict, old: dict) -> pd.DataFrame:
    rows = []
    for k, s in new.items():
        o = old[k].obs.set_index("obs_date").value
        n = s.obs.set_index("obs_date").value
        common = o.index.intersection(n.index)
        d = (n[common] - o[common]).abs()
        rows.append({"series": k, "backtest_last_obs": o.index.max(), "refreshed_last_obs": n.index.max(),
                     "overlap_obs": len(common), "n_changed": int((d > 0).sum()), "max_abs_change": float(d.max()),
                     "first_changed": None if not (d > 0).any() else d[d > 0].index.min()})
    return pd.DataFrame(rows)


def tcom_q3_reported() -> bool:
    p = RAW_DIR / "sec_submissions_live" / "2026-11-17" / "TCOM_CIK0001269238.json"
    rec = json.loads(read_snapshot(p))["filings"]["recent"]
    later = [(f, d) for f, d in zip(rec["form"], rec["filingDate"]) if f.startswith("6-K") and d > "2026-09-16"]
    if later:
        raise SystemExit(f"TCOM filed 6-K(s) after the Q2 release: {later}; check whether one is the Q3 results "
                         "release and score the locked call from it")
    return False


def adjusted_notes(td: live.TargetData, versions: pd.DataFrame, asof) -> dict:
    """hypotheses 3.12 for the 2026Q4 live call: BKNG (2026Q3 FTC item), LYFT (2025Q4 and 2026Q3 reserves)."""
    yb = td.get("BKNG", "y", Q - 1, "asof", asof)
    rev = lambda n, q: float(versions[(versions.name == n) & (versions.quarter == q)].sort_values("filed").value.iloc[-1])
    l_q1, l_q5, l_q4 = rev("LYFT", "2026Q3"), rev("LYFT", "2025Q3"), rev("LYFT", "2025Q4")
    yl = td.get("LYFT", "y", Q - 1, "asof", asof)
    lyft_ex = 100.0 * ((l_q1 + 69.1) / l_q5 - 1.0)
    return {
        ("BKNG", "y"): (f"3.12: q-1 = 2026Q3 contains the MAJOR one_off_revenue FTC item (-$900m revenue). GAAP "
                        f"y_q-1 = {yb['yoy_pct']:.2f}% vs company Adjusted Revenue growth +9% (same release). The "
                        "guidance label for y uses Adjusted Revenue guidance (0% to 2%). The GAAP 2026Q4 direction "
                        "vs 2026Q3 is mechanically driven by the FTC item (depressed q-1 base); the alt call is the "
                        "same sign for GAAP and Adjusted Revenue."),
        ("LYFT", "y"): (f"3.12: Lyft reports no adjusted revenue metric (it states revenue excluding the items in "
                        f"rounded $bn). q-1 = 2026Q3 includes a $69.1m reserve reduction: GAAP y_q-1 = "
                        f"{yl['yoy_pct']:.2f}%, excluding it {lyft_ex:.2f}% (XBRL revenue {l_q1:.1f} + 69.1 vs "
                        f"{l_q5:.1f}, USD m). q-4 = 2025Q4 includes a $168m reduction (base {l_q4:.1f}, "
                        f"{l_q4 + 168:.1f} without it), which mechanically lifts GAAP 2026Q4 YoY; the GAAP direction "
                        "is partly mechanical. Amounts: config/breaks.yaml (company releases)."),
    }


def main() -> None:
    cos = config.companies()
    series = F.load_series()                                     # latest pull
    for s in series.values():
        F.validate_series(s)
    asof = F.data_run_date(series)
    old = F.load_series(snapshots=F.backtest_snapshots())
    rc = revision_check(series, old)
    rc.to_csv(T / "snapshot_revision_check.csv", index=False)
    rev = []                     # do the revised Wikipedia days change any recent quarter-end backtest call?
    for n in cos:
        for q in (Q - 2, Q - 1):
            a = F.checkpoint_asof(q, "qend")
            o, m = (F.d_alt(x[f"wikipedia:{n}"], q, a)["d_alt"] for x in (old, series))
            rev.append({"name": n, "quarter": str(q), "d_alt_backtest": o, "d_alt_refreshed": m,
                        "sign_flip": (o > 0) != (m > 0)})
    pd.DataFrame(rev).to_csv(T / "wikipedia_revision_effect.csv", index=False, float_format="%.6f")
    reported = tcom_q3_reported()
    versions = pd.read_csv(REPO_ROOT / "data/processed/revenue_pit.csv", dtype={"accession": str})
    values = pd.read_csv(REPO_ROOT / "data/processed/release_values.csv", dtype={"accession": str})
    releases = pd.read_csv(REPO_ROOT / "data/processed/earnings_releases.csv", dtype={"accession": str})
    td = live.TargetData(versions, values)
    gcfg = LC.guidance_config()

    ev = [e for e in gcfg["base_period_events"] if e["source_series"] == "tsa"]
    sens = LC.tsa_sensitivity(series["tsa"], Q, asof, ev)
    sens.insert(0, "asof", asof)
    sens.to_csv(T / "live_tsa_sensitivity.csv", index=False, float_format="%.6f")
    s_txt = "; ".join(f"{r.variant}: alt_q {r.alt_q:+.4f} ({r.n_days} days), d_alt {r.d_alt:+.4f} -> {r.call}"
                      if r.alt_q is not None and not pd.isna(r.alt_q) else f"{r.variant}: no days left"
                      for r in sens.itertuples())
    ev_txt = " | ".join(f"{e['event']} [{e['source_url']}]" for e in ev)
    base_notes = {n: (f"Base period ({Q - 4}): {ev_txt}. TSA sensitivity (not a model change): {s_txt} "
                      "[outputs/tables/live_tsa_sensitivity.csv]") for n in cos if cos[n]["volume_source"] == "tsa"}
    adj = adjusted_notes(td, versions, asof)

    rows = []
    for name in cos:
        rows += LC.live_rows(name, Q, asof, series, td, cos, releases, gcfg, adj, base_notes)
    rows += LC.locked_rows(releases, reported, None)
    lv = pd.DataFrame(rows)
    lv.to_csv(T / "live_calls.csv", index=False, float_format="%.6f")

    res = pd.read_csv(T / "results.csv")
    lead = pd.read_csv(T / "lead_time.csv")
    calls = pd.read_csv(T / "calls.csv")
    mt = pd.read_csv(T / "multiple_testing.csv").iloc[0].to_dict()
    mt["green_cells"] = "" if pd.isna(mt["green_cells"]) else mt["green_cells"]
    method = [
        "1. Targets: revenue YoY (y; SEC XBRL, TCOM 6-K) and headline KPI YoY (k; earnings releases), like-for-like from one filing (hypotheses 3.11).",
        "2. Sources: TSA national throughput (US names), CAAC passenger traffic (TCOM), English Wikipedia pageviews (all), and a combined z-score source.",
        "3. Feature: alt_q = YoY of the source over the quarter (to date), 364-day weekday-aligned; d_alt = alt_q - alt_q-1 at the same as-of.",
        "4. Call: accelerate if d_alt > 0, decelerate if < 0; scored against the sign of d_y (first-reported).",
        "5. Point-in-time: alt data only if published by the as-of date (daily obs + 1 day; CAAC recorded release date); filings only if filed before it.",
        "6. Backtest: as-of = each quarter end, headline windows US 2023Q2-2026Q3, TCOM 2024Q2-2026Q2, pandemic-affected quarters excluded.",
        "7. Baselines: momentum (same direction as last quarter) and 50%; magnitude yhat = y_q-1 + beta x d_alt vs y_q-1.",
        "8. Significance: 1,000-run shuffle placebo (primary); GREEN = beats both baselines AND placebo percentile >= 95.",
        "9. Multiple testing over 39 pre-registered cells; BH q-values; TSA cells share one series and are not independent.",
        "10. Pre-registration: docs/hypotheses.md frozen at tag prereg (SHA-256 posted publicly) before any alt data was downloaded.",
    ]
    limits = [
        "- Small N: 14 quarters per US cell (needs 11 hits for p<0.05), 9 for TCOM; a real 70% signal is detected only ~1/3 of the time (power_table.csv).",
        "- TSA and CAAC measure travel VOLUME; revenue also moves with price, take rate, FX, accounting changes and M&A (docs/drivers.md, config/breaks.yaml).",
        "- Wikipedia measures attention (news, earnings days), is English-only and blocked in mainland China (TCOM).",
        "- Live-call base periods contain one-offs (2025 US federal lapse in appropriations and FAA flight cuts; LYFT reserves; BKNG FTC item; DASH Deliveroo anniversary).",
        "- Companies tend to guide conservatively, so 'above guidance' is the common case and is weak evidence on its own.",
        "- Guidance figures were extracted by hand from the releases (config/guidance.yaml, verbatim quotes checked by tests).",
    ]
    nd = lv[lv.call == "insufficient data"]
    if len(nd):
        limits.append(f"- Live as-of {asof}: no published data inside 2026Q4 for " + ", ".join(
            sorted({f"{r.name} {r.source}" for r in nd.itertuples()})) + " -> 'insufficient data' (no guess).")
    limits.append("- Wikimedia revised pageviews for ~80 days since 2026-06-20 between the 2026-11-11 and 2026-11-17 pulls; "
                  "the backtest stays on the 2026-11-11 snapshots; no 2026Q2/Q3 Wikipedia call changes sign "
                  "(outputs/tables/snapshot_revision_check.csv, wikipedia_revision_effect.csv).")
    tracker.build(REPO_ROOT / "outputs/tracker/sector_nowcast_tracker.xlsx", lv, res, lead, calls, mt, cos, method, limits)
    pd.set_option("display.width", 250, "display.max_columns", 20, "display.max_colwidth", 60)
    print("live asof:", asof)
    print(rc.to_string(index=False))
    print(sens.to_string(index=False))
    print(lv[lv.target == "y"][["live_call", "name", "quarter", "source", "d_alt", "call", "t_q_minus_1_pct", "yhat_pct",
                                 "guidance_label"]].to_string(index=False))


if __name__ == "__main__":
    main()
