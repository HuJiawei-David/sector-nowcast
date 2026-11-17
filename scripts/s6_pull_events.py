"""Session 6: official sources for base-period events of the 2026Q4 live calls (citation only; not a model input).

    .venv/bin/python scripts/s6_pull_events.py

Federal Register API (federalregister.gov, official US government publication): FAA orders reducing
scheduled flights in November 2025, and documents describing the October-November 2025 lapse in
appropriations. Responses saved unmodified under data/raw/federal_register/<today>/ (hard rule 8).
"""
import json
import sys
import time

import requests

sys.path.insert(0, "src")
from nowcast.rawstore import save_snapshot  # noqa: E402
from nowcast.wikimedia import WIKI_HEADERS  # noqa: E402

API = "https://www.federalregister.gov/api/v1/documents.json"
QUERIES = {
    "faa_flight_reductions_2025-11": {"conditions[term]": "\"high-volume airports\" reduction scheduled operations",
                                      "conditions[agencies][]": "federal-aviation-administration",
                                      "conditions[publication_date][gte]": "2025-11-01",
                                      "conditions[publication_date][lte]": "2025-12-31", "per_page": "20"},
    "lapse_in_appropriations_2025": {"conditions[term]": "\"lapse in appropriations\" October 1, 2025",
                                     "conditions[publication_date][gte]": "2025-10-01",
                                     "conditions[publication_date][lte]": "2025-12-31", "per_page": "20"},
}
for key, params in QUERIES.items():
    r = requests.get(API, params=params, headers=WIKI_HEADERS, timeout=60)
    print(key, r.status_code, r.url)
    save_snapshot("federal_register", f"{key}.json", r.content, {"url": r.url, "params": params,
                  "headers": WIKI_HEADERS, "http_status": r.status_code, "purpose": "citation for base-period events"})
    if r.ok:
        for d in r.json().get("results", [])[:20]:
            print("  ", d["publication_date"], d["type"], d["title"][:150], d["html_url"])
    time.sleep(1)

# Full documents found by the queries above (FAA emergency orders on scheduled operations, November 2025).
DOCS = ["2025-19986", "2025-20308"]
for num in DOCS:
    u = f"https://www.federalregister.gov/api/v1/documents/{num}.json"
    r = requests.get(u, headers=WIKI_HEADERS, timeout=60)
    save_snapshot("federal_register", f"doc_{num}.json", r.content, {"url": u, "headers": WIKI_HEADERS,
                  "http_status": r.status_code, "purpose": "citation for base-period events"})
    meta = r.json()
    t = requests.get(meta["raw_text_url"], headers=WIKI_HEADERS, timeout=60)
    save_snapshot("federal_register", f"doc_{num}_raw.txt", t.content, {"url": meta["raw_text_url"],
                  "headers": WIKI_HEADERS, "http_status": t.status_code, "purpose": "citation for base-period events"})
    print(num, r.status_code, t.status_code, meta["title"], meta["html_url"])
    time.sleep(1)
