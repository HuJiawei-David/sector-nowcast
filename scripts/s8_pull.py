"""Session 8 (audit): two small official pulls, saved unmodified per hard rule 8. Network.

    .venv/bin/python scripts/s8_pull.py

1. Federal Register documents that state the START of the 2025 lapse in appropriations (coach item 8a): the
   candidates come from the Session 6 search snapshot data/raw/federal_register/2026-11-17/
   lapse_in_appropriations_2025.json. Saved as data/raw/federal_register/<today>/doc_<number>{.json,_raw.txt}.
2. EDGAR submissions for Trip.com (CIK 1269238), to see whether the Q3 2026 results 6-K is filed (coach item 8d).
   Saved under data/raw/sec_submissions_s8/<today>/ (its own folder: the Session 6 snapshot in
   sec_submissions_live/2026-11-17/ is an input of scripts/s6_live.py and must not be overwritten).
"""
import json
import sys
import time

import requests

sys.path.insert(0, "src")
from nowcast import sec  # noqa: E402
from nowcast.rawstore import save_snapshot  # noqa: E402
from nowcast.wikimedia import WIKI_HEADERS  # noqa: E402

FR_DOCS = sys.argv[1:] or ["2025-21834", "2025-20331", "2025-23429"]
for num in FR_DOCS:
    u = f"https://www.federalregister.gov/api/v1/documents/{num}.json"
    r = requests.get(u, headers=WIKI_HEADERS, timeout=60)
    save_snapshot("federal_register", f"doc_{num}.json", r.content, {"url": u, "headers": WIKI_HEADERS,
                  "http_status": r.status_code, "purpose": "citation for the start of the 2025 lapse in appropriations"})
    r.raise_for_status()
    meta = r.json()
    t = requests.get(meta["raw_text_url"], headers=WIKI_HEADERS, timeout=60)
    save_snapshot("federal_register", f"doc_{num}_raw.txt", t.content, {"url": meta["raw_text_url"],
                  "headers": WIKI_HEADERS, "http_status": t.status_code,
                  "purpose": "citation for the start of the 2025 lapse in appropriations"})
    print(num, r.status_code, t.status_code, meta["publication_date"], meta["title"][:100], meta["html_url"])
    time.sleep(1)

content, path = sec.fetch(sec.submissions_url(1269238), "sec_submissions_s8", "TCOM_CIK0001269238.json",
                          purpose="check for the Q3 2026 results 6-K (locked forward call)")
rec = json.loads(content)["filings"]["recent"]
print("saved", path)
for f, d, a, p in list(zip(rec["form"], rec["filingDate"], rec["accessionNumber"], rec["primaryDocument"]))[:12]:
    print(d, f, a, p)
