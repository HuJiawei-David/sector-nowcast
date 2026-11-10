"""Session 1: FY2025 revenue mix shares for docs/drivers.md.
Inputs are transcribed from the FY2025 annual reports (source URL per row; raw copies in
data/raw/sec_filings/2026-11-10/). Shares are computed here, not by hand.
Writes outputs/tables/geo_mix_fy2025.csv.
"""
import csv
from pathlib import Path

A = "https://www.sec.gov/Archives/edgar/data/"
SRC = {
    "BKNG": A + "1075531/000107553126000009/bkng-20251231.htm",
    "EXPE": A + "1324424/000132442426000008/expe-20251231.htm",
    "ABNB": A + "1559720/000155972026000004/abnb-20251231.htm",
    "UBER": A + "1543151/000154315126000015/uber-20251231.htm",
    "LYFT": A + "1759509/000162828026006960/lyft-20251231.htm",
    "DASH": A + "1792789/000179278926000013/dash-20251231.htm",
    "TCOM": A + "1269238/000119312526183379/d27369d20f.htm",
    "TCOM_SAMR": A + "1269238/000119312526316761/d256213d6k.htm",
}
# (name, basis, segment, value, unit, total)
ROWS = [
    ("BKNG", "entity domicile (not traveller location)", "U.S.", 2579, "USD m", 26917),
    ("BKNG", "entity domicile (not traveller location)", "Outside the U.S.", 24338, "USD m", 26917),
    ("BKNG", "entity domicile (not traveller location)", "of which entity domiciled in the Netherlands", 21700, "USD m", 26917),
    ("EXPE", "location of websites / points of sale", "United States", 8710, "USD m", 14733),
    ("EXPE", "location of websites / points of sale", "All other countries", 6023, "USD m", 14733),
    ("ABNB", "location of host's listing", "United States", 4814, "USD m", 12241),
    ("ABNB", "location of host's listing", "International", 7427, "USD m", 12241),
    ("UBER", "region", "US & Canada", 26469, "USD m", 52017),
    ("UBER", "region", "Latin America", 3327, "USD m", 52017),
    ("UBER", "region", "EMEA", 16364, "USD m", 52017),
    ("UBER", "region", "APAC", 5857, "USD m", 52017),
    ("UBER", "country", "United States", 23771, "USD m", 52017),
    ("UBER", "country", "United Kingdom", 10609, "USD m", 52017),
    ("LYFT", "where transaction occurred / contracting entity", "United States", 6060220, "USD k", 6316261),
    ("LYFT", "where transaction occurred / contracting entity", "International", 256041, "USD k", 6316261),
    ("DASH", "merchant address (consumer address for memberships)", "United States", 11460, "USD m", 13717),
    ("DASH", "merchant address (consumer address for memberships)", "International", 2257, "USD m", 13717),
    ("TCOM", "product line", "Accommodation reservation", 26.1, "RMB bn", 62.5),
    ("TCOM", "product line", "Transportation ticketing", 22.5, "RMB bn", 62.5),
    ("TCOM", "product line", "Packaged tours", 4.7, "RMB bn", 62.5),
    ("TCOM", "product line", "Corporate travel", 2.8, "RMB bn", 62.5),
]
out = Path("outputs/tables"); out.mkdir(parents=True, exist_ok=True)
with open(out / "geo_mix_fy2025.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["name", "basis", "segment", "value", "unit", "total", "share_pct", "source"])
    for n, b, s, v, u, t in ROWS:
        w.writerow([n, b, s, v, u, t, round(100 * v / t, 1), SRC[n]])
    # TCOM PRC share implied by the SAMR decision: fine RMB3,521m = 7.5% of 2025 PRC sales revenue
    prc = 3521 / 0.075
    w.writerow(["TCOM", "implied by SAMR fine (7.5% of 2025 PRC sales revenue)", "PRC (implied)",
                round(prc), "RMB m", 62500, round(100 * prc / 62500, 1), SRC["TCOM_SAMR"]])
    # combined share used in docs: accommodation + transportation ticketing
    w.writerow(["TCOM", "product line", "Accommodation + transportation ticketing", 26.1 + 22.5, "RMB bn", 62.5,
                round(100 * (26.1 + 22.5) / 62.5, 1), SRC["TCOM"]])
for line in open(out / "geo_mix_fy2025.csv"):
    print(line.rstrip()[:150])
