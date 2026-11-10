"""Session 1: EDGAR full-text search (efts.sec.gov, official) to locate source filings for
structural breaks. Raw responses saved under data/raw/sec_efts/<date>/."""
import json, sys, hashlib, urllib.parse
sys.path.insert(0, "src")
from nowcast import sec
q, ciks, forms, start, end = sys.argv[1:6]
params = {"q": q, "ciks": ciks, "forms": forms, "dateRange": "custom", "startdt": start, "enddt": end}
url = "https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode(params)
tag = hashlib.sha1(url.encode()).hexdigest()[:10]
body, _ = sec.fetch(url, "sec_efts", f"efts_{tag}.json", query=params)
hits = json.loads(body)["hits"]["hits"]
for h in hits[:int(sys.argv[6]) if len(sys.argv) > 6 else 10]:
    s = h["_source"]
    print(s["file_date"], s["form"], s.get("period_ending"), h["_id"], s.get("file_description") or "")
