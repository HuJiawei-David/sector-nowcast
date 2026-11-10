"""Session 2 printout (reads the built tables; no network). Also saved to
outputs/tables/session2_printout.txt.

    .venv/bin/python scripts/s2_report.py
"""
import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
T = ROOT / "outputs" / "tables"
P = ROOT / "data" / "processed"
SPOT_Q = ["2022Q2", "2024Q2", "2026Q3"]          # fixed in advance: one early, one middle, latest
TCOM_SPOT_Q = ["2022Q2", "2024Q2", "2026Q2"]


def main():
    y = pd.read_csv(T / "revenue_yoy.csv")
    k = pd.read_csv(T / "kpi_yoy.csv")
    v = pd.read_csv(P / "release_values.csv")
    rec = pd.read_csv(T / "reconciliation.csv")

    print("=" * 100)
    print("REVENUE YoY (%) 2022Q1-2026Q3, like-for-like from the first filing reporting q "
          "(US: XBRL 10-Q/10-K; TCOM: 6-K release, RMB)")
    print("  '*' = CLEAN YoY under hard rule 4 (neither q nor q-4 in the exclusion window); "
          "'n/r' = not yet reported")
    print("  source: outputs/tables/revenue_yoy.csv")
    names = list(dict.fromkeys(y["name"]))
    piv = {}
    for n in names:
        d = y[y["name"] == n].set_index("quarter")
        piv[n] = [("n/r" if r.status != "ok" else f"{r.y_pct_first_reported:6.1f}" + ("*" if r.yoy_clean else " "))
                  for r in d.itertuples()]
    qs = list(y[y["name"] == names[0]]["quarter"])
    print(f"{'quarter':8}" + "".join(f"{n:>9}" for n in names))
    for i, q in enumerate(qs):
        print(f"{q:8}" + "".join(f"{piv[n][i]:>9}" for n in names))

    print("\nKPI YoY (%) availability (outputs/tables/kpi_yoy.csv):")
    print(k.groupby(["name", "status"]).size().to_string())

    print("\n" + "=" * 100)
    print("SPOT-CHECK (open the URL and find the quoted text): 3 KPI numbers per name, 3 revenue numbers for TCOM")
    for n in names:
        if n == "TCOM":
            sel = v[(v["name"] == n) & (v["metric"] == "revenue") & (v["kind"] == "value") & (v["role"] == "current")
                    & v["quarter"].isin(TCOM_SPOT_Q)]
            what = "net revenue, RMB m"
        else:
            sel = v[(v["name"] == n) & (v["metric"] == "kpi") & (v["kind"] == "value") & (v["role"] == "current")
                    & v["quarter"].isin(SPOT_Q)]
            what = "KPI, millions"
        sel = sel[~sel["form"].str.endswith("/A")].sort_values("quarter").drop_duplicates("quarter")
        if len(sel) < 3:      # KPI first disclosed later (LYFT): add the earliest quarter it appears
            pool = v[(v["name"] == n) & (v["metric"] == "kpi") & (v["kind"] == "value") & (v["role"] == "current")
                     & ~v["form"].str.endswith("/A") & ~v["quarter"].isin(sel["quarter"])].sort_values("quarter")
            sel = pd.concat([pool.head(3 - len(sel)), sel]).sort_values("quarter")
        for r in sel.itertuples():
            print(f"  {n} {r.quarter} {what}: {r.value:g}   filed {r.filed}   {r.source_url}")
            print(f"      text: \"{str(r.snippet)[:160]}\"")

    print("\n" + "=" * 100)
    st = rec["status"].str.extract(r"^(match \(bug fixed|match|definitional)")[0]
    print("RECONCILIATION (outputs/tables/reconciliation.csv)")
    print(f"  checks run: {len(rec)}; matches: {(st == 'match').sum()}; "
          f"matches after a bug fix: {(st == 'match (bug fixed').sum()}; definitional: {(st == 'definitional').sum()}; "
          f"unclassified: {rec['status'].eq('UNCLASSIFIED').sum()}")
    print("  bugs fixed (config/reconciliation_notes.yaml, STATUS.md): see bugs_fixed ids there")
    print(rec.groupby(["check"]).agg(n=("status", "size"),
                                     match=("status", lambda s: s.str.startswith("match").sum()),
                                     definitional=("status", lambda s: s.str.startswith("definitional").sum())).to_string())
    print("\n  3 rows per name (for checking by hand):")
    for n in names:
        d = rec[rec["name"] == n]
        pick = pd.concat([d[d["check"] == "revenue_yoy"].tail(1), d[d["check"] == "kpi_yoy"].tail(1),
                          d[d["check"].isin(["q4_revenue_derived"])].tail(1)])
        if len(pick) < 3:
            pick = pd.concat([pick, d[~d.index.isin(pick.index)].tail(3 - len(pick))])
        for r in pick.itertuples():
            print(f"  {n} {r.quarter} {r.check}: ours {r.ours:.2f} vs company {r.company:g} ({r.company_basis}); "
                  f"diff {r.diff:+.2f}, tol {r.tolerance:.2f} -> {r.status[:60]}")
            print(f"      {r.source_url}")


if __name__ == "__main__":
    buf = io.StringIO()
    with redirect_stdout(buf):
        main()
    out = buf.getvalue()
    (T / "session2_printout.txt").write_text(out)
    sys.stdout.write(out)
