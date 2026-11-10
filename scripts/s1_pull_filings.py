"""Session 1: pull latest annual report + latest earnings release per name (raw snapshots).
Run from repo root: .venv/bin/python scripts/s1_pull_filings.py
"""
import json, sys
sys.path.insert(0, "src")
from nowcast import sec

CIKS = {"BKNG": 1075531, "EXPE": 1324424, "ABNB": 1559720, "UBER": 1543151,
        "LYFT": 1759509, "DASH": 1792789, "TCOM": 1269238}
out = {}
for t, cik in CIKS.items():
    body, _ = sec.fetch(sec.submissions_url(cik), "sec_submissions", f"{t}_CIK{cik:010d}.json", ticker=t, cik=cik)
    j = json.loads(body)
    r = j["filings"]["recent"]
    rows = list(zip(r["form"], r["filingDate"], r["accessionNumber"], r["primaryDocument"], r["items"], r["reportDate"]))
    annual = [x for x in rows if x[0] in ("10-K", "20-F")][:1]
    if t == "TCOM":
        er = [x for x in rows if x[0] == "6-K"][:12]
    else:
        er = [x for x in rows if x[0] == "8-K" and "2.02" in x[4]][:2]
    out[t] = {"name": j["name"], "fye": j.get("fiscalYearEnd"), "annual": annual, "earnings": er}
    print(t, j["name"], "FYE", j.get("fiscalYearEnd"))
    for x in annual + er: print("   ", x)
json.dump(out, open("/private/tmp/claude-501/-Users-david--claude-spares-spare-B5rNJE/8da16b4c-a381-4cf8-80db-388c65cae207/scratchpad/filings.json", "w"), indent=1)
