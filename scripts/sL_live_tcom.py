"""Session L: timestamped forward call for TCOM 2026Q3 (live call (b)) from the Session 3 snapshots.

    .venv/bin/python scripts/sL_live_tcom.py

asof = 2026-11-10 (features.data_run_date of the S3 snapshots: latest date on which every daily source
is complete). No network. Output: outputs/tables/live_calls_tcom_2026Q3.csv
"""
import datetime as dt
import sys

import pandas as pd

sys.path.insert(0, "src")
from nowcast import config, features as F, live  # noqa: E402
from nowcast.quarters import Quarter  # noqa: E402

ASOF = dt.date(2026, 11, 10)
NAME, Q = "TCOM", Quarter(2026, 3)
OUT = "outputs/tables/live_calls_tcom_2026Q3.csv"
# hypotheses 3.12: q-1 (2026Q2) carries a MAJOR one_off_revenue break (SAMR contra-revenue).
# Checked in the Q2 2026 release (data/raw/sec_filings/2026-11-10/TCOM_0001193125-26-392473_d167816dex991.htm):
# it quantifies the RMB5.2bn penalty (an expense) and gives "without the effect of the penalty" figures for
# G&A and net income only; it reports no adjusted revenue and does not quantify the contra-revenue.
ADJUSTED_NOTE = ("3.12: q-1 = 2026Q2 contains the MAJOR one_off_revenue SAMR break, but the Q2 2026 release reports "
                 "no adjusted revenue figure and does not quantify the contra-revenue (only the RMB5.2bn penalty, "
                 "an expense), so no call against an adjusted metric is possible. y_{q-1} is depressed by that "
                 "contra-revenue by an unquantified amount, so the GAAP direction vs 2026Q2 is partly mechanical. "
                 "The SAMR penalty is outside revenue.")


def main() -> None:
    series = F.load_series(snapshots=F.backtest_snapshots())
    run_date = F.data_run_date(series)
    if run_date != ASOF:
        raise SystemExit(f"S3 snapshots' data run date is {run_date}, expected {ASOF}")
    versions = pd.read_csv("data/processed/revenue_pit.csv", dtype={"accession": str})
    releases = pd.read_csv("data/processed/earnings_releases.csv", dtype={"accession": str})
    if ((releases.name == NAME) & (releases.quarter == str(Q))).any():
        raise SystemExit(f"{NAME} {Q} already reported in earnings_releases.csv; live call (b) does not apply")
    rows = live.live_calls(NAME, Q, ASOF, series, versions, releases, config.companies(), ADJUSTED_NOTE)
    df = pd.DataFrame(rows)
    # cross-check against the Session 3 feature table (same function, same asof)
    feat = pd.read_csv("data/processed/alt_features.csv")
    feat = feat[(feat.name == NAME) & (feat.quarter == str(Q)) & (feat.checkpoint == "live") & (feat.variant == "base")]
    for _, r in df[df.source != "combined"].iterrows():
        f = feat[feat.source == r.source].iloc[0]
        assert abs(f.d_alt - r.d_alt) < 1e-12 and str(f["asof"]) == str(ASOF), (r.source, f.d_alt, r.d_alt)
    df.to_csv(OUT, index=False, float_format="%.6f")
    pd.set_option("display.width", 250, "display.max_columns", 30, "display.max_colwidth", 200)
    print(df[["source", "asof", "alt_q", "alt_q_minus_1", "d_alt", "call", "y_q_minus_1_pct",
              "beta_pp_per_unit_d_alt", "beta_basis", "n_pairs", "yhat_pct", "magnitude_status", "guidance_label"]].T)
    print(df.combined_detail.iloc[-1])
    print(df[["inputs_q", "inputs_q_minus_1"]].iloc[:2].T)


if __name__ == "__main__":
    main()
