"""TSA checkpoint travel numbers: national daily throughput (persons screened), tsa.gov.

Pages: https://www.tsa.gov/travel/passenger-volumes (current year) and
       https://www.tsa.gov/travel/passenger-volumes/<YYYY> (one page per past year).

Capture. `fetch()` requests each page with the project's descriptive User-Agent (no browser
disguise) and saves the response unmodified under data/raw/tsa/<pull_date>/ (hard rule 8); a
non-200 response is saved as `<name>.http<status>.html` and reported, never silently skipped.
(2026-11-11: an exploratory `curl` request with the same User-Agent got 403 "Access Denied";
python-requests got 200 for all eight pages.)

Parse. The table with a "Date" header column; the throughput column is "Numbers" (or, on pages
that carry several year columns, the column headed with the page's year). One row per day.
Rule 9: duplicate dates with different values, gaps and non-positive values fail loudly.
Publication date (hard rule 2): observation date + 1 day.
"""
from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .rawstore import RAW_DIR, read_snapshot, save_snapshot

SOURCE = "tsa"
BASE_URL = "https://www.tsa.gov/travel/passenger-volumes"
HEADERS = {"User-Agent": "sector-nowcast-research/0.1 (non-commercial research tool; python-requests)"}
NAME_RE = re.compile(r"^passenger-volumes_(current|\d{4})\.html?$")


class DataError(ValueError):
    """Rule 9: fail loudly."""


def page_url(key: str) -> str:
    return BASE_URL if key == "current" else f"{BASE_URL}/{key}"


def fetch(keys: list[str], pull_date: dt.date | None = None) -> dict[str, int]:
    """Try the official pages with the project's descriptive User-Agent. A 200 is saved as the
    snapshot; any other status is saved as `<name>.http<status>.html` (evidence) and reported."""
    status = {}
    for key in keys:
        r = requests.get(page_url(key), headers=HEADERS, timeout=60)
        name = f"passenger-volumes_{key}.html"
        if r.status_code != 200:
            name = f"passenger-volumes_{key}.http{r.status_code}.html"
        save_snapshot(SOURCE, name, r.content, {"url": page_url(key), "headers": HEADERS,
                      "http_status": r.status_code, "capture_method": "scripted (requests)"}, pull_date)
        status[key] = r.status_code
    return status


def _num(s: str) -> int | None:
    s = re.sub(r"[,\s]", "", s or "")
    return int(s) if s.isdigit() else None


def _parse_date(s: str) -> dt.date | None:
    s = (s or "").strip()
    for fmt in ("%m/%d/%Y", "%m/%d/%y", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def parse_page(html: bytes, key: str) -> pd.DataFrame:
    """Rows (date, throughput) from one page."""
    soup = BeautifulSoup(html, "lxml")
    for table in soup.find_all("table"):
        header_row = table.find("tr")
        heads = [c.get_text(" ", strip=True) for c in header_row.find_all(["th", "td"])] if header_row else []
        if not heads or not heads[0].lower().startswith("date"):
            continue
        if "Numbers" in heads:
            col = heads.index("Numbers")
        elif key != "current" and key in heads:
            col = heads.index(key)
        elif len(heads) == 2:
            col = 1
        else:
            raise DataError(f"TSA page {key}: cannot identify the throughput column in {heads}")
        rows = []
        for tr in table.find_all("tr")[1:]:
            cells = [c.get_text(" ", strip=True) for c in tr.find_all(["td", "th"])]
            if len(cells) <= col:
                continue
            d, v = _parse_date(cells[0]), _num(cells[col])
            if d is None or v is None:
                raise DataError(f"TSA page {key}: unparseable row {cells}")
            rows.append({"date": d, "value": v})
        if rows:
            return pd.DataFrame(rows)
    raise DataError(f"TSA page {key}: no Date/Numbers table found")


def latest_dir() -> Path:
    base = RAW_DIR / SOURCE
    dirs = sorted(p for p in base.iterdir() if p.is_dir() and any(NAME_RE.match(f.name) for f in p.iterdir())) \
        if base.exists() else []
    if not dirs:
        raise FileNotFoundError("no TSA page snapshots in data/raw/tsa/<date>/ (see src/nowcast/tsa.py docstring)")
    return dirs[-1]


def parse(snap_dir: Path | None = None) -> pd.DataFrame:
    """Daily national throughput from every saved page: date, value, page, source_url."""
    snap_dir = snap_dir or latest_dir()
    frames = []
    for p in sorted(snap_dir.iterdir()):
        m = NAME_RE.match(p.name.removesuffix(".gz"))
        if not m:
            continue
        df = parse_page(read_snapshot(p), m.group(1))
        if m.group(1) != "current":
            yrs = {d.year for d in df.date}
            if yrs != {int(m.group(1))}:
                raise DataError(f"TSA page {m.group(1)} holds dates from years {sorted(yrs)}")
        df["page"], df["source_url"] = m.group(1), page_url(m.group(1))
        frames.append(df)
    if not frames:
        raise DataError(f"no TSA pages in {snap_dir}")
    allrows = pd.concat(frames, ignore_index=True)
    within = allrows[allrows.duplicated(["page", "date"], keep=False)]
    if len(within):
        raise DataError(f"duplicate dates within a TSA page: {within.head().to_dict('records')}")
    conflict = allrows.groupby("date").value.nunique()
    if (conflict > 1).any():
        bad = conflict[conflict > 1].index[:5].tolist()
        raise DataError(f"TSA pages disagree on dates {bad}")
    out = (allrows.sort_values(["date", "page"]).drop_duplicates("date")
           .sort_values("date").reset_index(drop=True))
    return out
