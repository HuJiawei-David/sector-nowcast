"""Session 1b: evidence for the structural-break materiality rule (docs/hypotheses.md section 3.8).

For each acquisition/disposal break (types that are MAJOR only under rule (b)), run an EDGAR
full-text search (efts.sec.gov, official) for the acquiree's name in the company's 8-K / 10-Q /
10-K filings from the effective date to the run date, download every matching document that is
not already in data/raw/sec_filings/, and print sentences that mention the acquiree together with
a number and a revenue / KPI / growth word, or an "excluding <acquiree>" figure. The printed
candidates are read by hand; the classification and the quoted sentence go into config/breaks.yaml.
Raw responses are saved under data/raw/sec_efts/<date>/ and data/raw/sec_filings/<date>/.
"""
import gzip, hashlib, json, re, sys, urllib.parse
from pathlib import Path
sys.path.insert(0, "src")
from bs4 import BeautifulSoup
from nowcast import sec

QUERIES = [  # (name, cik, acquiree query, start, end)
    ("BKNG", 1075531, "Getaroom", "2021-11-01", "2023-03-31"),
    ("EXPE", 1324424, "Egencia", "2021-11-01", "2023-03-31"),
    ("UBER", 1543151, "Transplace", "2021-11-01", "2023-03-31"),
    ("UBER", 1543151, "Trendyol", "2025-05-01", "2026-11-10"),
    ("UBER", 1543151, "SpotHero", "2026-04-01", "2026-11-10"),
    ("UBER", 1543151, "Getir", "2026-04-01", "2026-11-10"),
    ("UBER", 1543151, "Careem", "2026-07-01", "2026-11-10"),
    ("LYFT", 1759509, "Freenow", "2025-07-01", "2026-11-10"),
    ("LYFT", 1759509, "TBR", "2025-10-01", "2026-11-10"),
    ("DASH", 1792789, "Wolt", "2022-05-01", "2023-08-31"),
    ("DASH", 1792789, "Symbiosys", "2025-05-01", "2026-11-10"),
    ("DASH", 1792789, "SevenRooms", "2025-05-01", "2026-11-10"),
    ("DASH", 1792789, "Deliveroo", "2025-10-01", "2026-11-10"),
]
FILINGS = Path("data/raw/sec_filings")
NUM = re.compile(r"(?i)(exclud|contribut|since (the|its) acquisition|\d+(\.\d+)? ?(%|percent|percentage point|pp\b|million|billion|bps))")
TOPIC = re.compile(r"(?i)revenue|orders|trips|rides|room nights|gross bookings|GOV|growth")


def efts(q, cik, start, end):
    params = {"q": f'"{q}"', "ciks": f"{cik:010d}", "forms": "8-K,10-Q,10-K",
              "dateRange": "custom", "startdt": start, "enddt": end}
    url = "https://efts.sec.gov/LATEST/search-index?" + urllib.parse.urlencode(params)
    tag = hashlib.sha1(url.encode()).hexdigest()[:10]
    body, _ = sec.fetch(url, "sec_efts", f"efts_{tag}.json", query=params)
    return json.loads(body)["hits"]["hits"]


def local_copy(name, adsh, fn):
    for p in FILINGS.glob(f"*/{name}_{adsh}_{fn}*"):
        if not p.name.endswith(".request.json"):
            return p
    return None


def text_of(p):
    b = p.read_bytes()
    if p.suffix == ".gz":
        b = gzip.decompress(b)
    return re.sub(r"\s+", " ", BeautifulSoup(b, "lxml").get_text(" "))


for name, cik, q, start, end in QUERIES:
    hits = efts(q, cik, start, end)
    print(f"\n===== {name} {q}: {len(hits)} hits")
    for h in hits:
        adsh, fn = h["_id"].split(":", 1)
        s = h["_source"]
        p = local_copy(name, adsh, fn)
        if p is None:
            url = sec.archive_file_url(cik, adsh, fn)
            _, p = sec.fetch(url, "sec_filings", f"{name}_{adsh}_{fn}", purpose=f"S1b materiality evidence: {q}")
        pat = re.compile(r"(?i)\b" + re.escape(q))
        for sent in re.split(r"(?<=[.;])\s+(?=[A-Z(•])", text_of(p)):
            if pat.search(sent) and NUM.search(sent) and TOPIC.search(sent) and len(sent) < 1500:
                print(f"  [{s['file_date']} {s['form']} {adsh} {fn}] {sent.strip()}")
