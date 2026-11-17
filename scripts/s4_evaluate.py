"""Session 4: walk-forward evaluation (src/nowcast/evaluate.py) from the Session 2/3 snapshots. No network.

    .venv/bin/python scripts/s4_evaluate.py

Outputs
  outputs/tables/calls.csv              one row per single quarterly call (asof = quarter end)
  outputs/tables/results.csv            headline: one row per (name, source, target, model)
  outputs/tables/robustness.csv         robustness (i) US 2024Q1-2026Q3, (ii) MAJOR breaks removed,
                                        (iii) Wikipedia earnings-day windows removed
  outputs/tables/relevancy_matrix.csv   sql/results_summary.sql run on data/nowcast.db
  outputs/tables/tsa_dependence.csv     the single TSA call per quarter, scored per US name
  outputs/tables/bkng_k_rounding_check.csv  data-quality note (BKNG room nights rounded to millions)
"""
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, "src")
from nowcast import evaluate as E  # noqa: E402
from nowcast.rawstore import REPO_ROOT  # noqa: E402

T = REPO_ROOT / "outputs" / "tables"
DB = REPO_ROOT / "data" / "nowcast.db"
SQL = REPO_ROOT / "sql"


def to_db(res: pd.DataFrame, cos: dict) -> pd.DataFrame:
    order = {n: i for i, n in enumerate(cos)}
    t = pd.DataFrame({
        "analysis": res.analysis, "name_order": res.name.map(order), "name": res.name, "source": res.source,
        "target": res.target, "model": res.model, "status": res.status,
        "family_member": res.family_member.astype(int), "n_prereg": res.N_prereg,
        "n_realised": res.N_realised.astype(int), "hits": res.hits, "min_hits_p05": res.min_hits_p05_realised,
        "momentum_hits": res.momentum_hits, "beats_both": res.beats_both_baselines.map({True: 1, False: 0}),
        "binom_p": res.binom_p_one_sided, "bh_q_binom": res.bh_q_binom, "mae_pp": res.mae_pp,
        "mae_baseline_pp": res.mae_baseline_pp})
    con = sqlite3.connect(DB)
    con.executescript((SQL / "results_schema.sql").read_text())
    t.to_sql("results_cells", con, if_exists="append", index=False)
    con.commit()
    m = pd.read_sql_query((SQL / "results_summary.sql").read_text(), con)
    con.close()
    return m


def main() -> None:
    inp = E.load_inputs()
    calls = E.make_calls(inp)
    res = E.results(calls, inp["cos"])
    calls.to_csv(T / "calls.csv", index=False, float_format="%.6f")
    head = res[res.analysis == "headline"].drop(columns="analysis")
    head.to_csv(T / "results.csv", index=False, float_format="%.6f")
    res[res.analysis != "headline"].to_csv(T / "robustness.csv", index=False, float_format="%.6f")
    m = to_db(res, inp["cos"])
    m.to_csv(T / "relevancy_matrix.csv", index=False)
    E.tsa_dependence(calls).to_csv(T / "tsa_dependence.csv", index=False, float_format="%.6f")
    bk = E.bkng_k_rounding_check(inp)
    bk.to_csv(T / "bkng_k_rounding_check.csv", index=False, float_format="%.4f")
    print(f"calls: {len(calls)} rows; results: {len(head)} rows; robustness: {int((res.analysis != 'headline').sum())} rows")
    print(f"BKNG k sign(d_k) levels vs stated differ in {int(bk.sign_differs.sum())} of {bk.sign_differs.notna().sum()} headline quarters")


if __name__ == "__main__":
    main()
