"""EDGAR filing lists and earnings-release identification (reads raw snapshots only, hard rule 8).

- submissions(): every filing of a company, merged from the `recent` block and the older pages
  listed under filings.files, from the latest data/raw/sec_submissions/<date>/ snapshot.
- earnings_8k(): US earnings releases = 8-K / 8-K/A carrying Item 2.02.
- parse_index(): documents of a filing from its EDGAR -index.htm page (Seq, Description, Document, Type).
- fiscal_quarter_of_release(): the calendar quarter an earnings release reports (the latest quarter
  that ended before the filing date).
"""
from __future__ import annotations

import datetime as dt
import json
import re

import pandas as pd
from bs4 import BeautifulSoup

from .quarters import Quarter
from .rawstore import RAW_DIR, read_snapshot

SUBMISSIONS_SRC = "sec_submissions"
FILINGS_SRC = "sec_filings"
ARCHIVES = "https://www.sec.gov/Archives/edgar/data"


def latest_pull_date(source: str) -> str:
    dates = sorted(p.name for p in (RAW_DIR / source).iterdir() if p.is_dir())
    if not dates:
        raise FileNotFoundError(f"no snapshots under data/raw/{source}")
    return dates[-1]


def _submission_files(ticker: str, cik: int, pull_date: str) -> list:
    d = RAW_DIR / SUBMISSIONS_SRC / pull_date
    main = d / f"{ticker}_CIK{cik:010d}.json"
    if not main.exists():
        raise FileNotFoundError(main)
    out = [main]
    j = json.loads(read_snapshot(main))
    for f in j["filings"].get("files", []):
        p = d / f"{ticker}_{f['name']}"
        if not p.exists():
            raise FileNotFoundError(f"older submissions page not pulled: {p}")
        out.append(p)
    return out


def submissions(ticker: str, cik: int, pull_date: str | None = None) -> pd.DataFrame:
    pull_date = pull_date or latest_pull_date(SUBMISSIONS_SRC)
    frames = []
    for i, p in enumerate(_submission_files(ticker, cik, pull_date)):
        j = json.loads(read_snapshot(p))
        block = j["filings"]["recent"] if i == 0 else j
        cols = ["accessionNumber", "filingDate", "reportDate", "form", "items", "primaryDocument",
                "primaryDocDescription"]
        frames.append(pd.DataFrame({c: block.get(c, [""] * len(block["accessionNumber"])) for c in cols}))
    df = pd.concat(frames, ignore_index=True)
    if df["accessionNumber"].duplicated().any():
        raise ValueError(f"{ticker}: duplicate accession numbers across submissions pages")
    df["filingDate"] = pd.to_datetime(df["filingDate"]).dt.date
    df.insert(0, "ticker", ticker)
    df["cik"] = cik
    return df.sort_values("filingDate").reset_index(drop=True)


def earnings_8k(sub: pd.DataFrame, since: dt.date) -> pd.DataFrame:
    m = sub["form"].isin(["8-K", "8-K/A"]) & sub["items"].fillna("").str.contains(r"\b2\.02\b") \
        & (sub["filingDate"] >= since)
    return sub[m].copy()


def parse_index(html: bytes) -> pd.DataFrame:
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for tb in soup.find_all("table", class_="tableFile"):
        for tr in tb.find_all("tr"):
            tds = tr.find_all("td")
            if len(tds) < 4:
                continue
            a = tds[2].find("a")
            href = a["href"] if a else ""
            doc = href.split("/")[-1] if href else ""
            rows.append({"seq": tds[0].get_text(strip=True), "description": tds[1].get_text(" ", strip=True),
                         "document": doc, "type": tds[3].get_text(strip=True)})
    return pd.DataFrame(rows, columns=["seq", "description", "document", "type"])


def exhibit_991(index_df: pd.DataFrame) -> str | None:
    """Document name of the EX-99.1 exhibit (HTML); falls back to a lone 'EX-99' exhibit; else None."""
    html = index_df["document"].str.lower().str.endswith((".htm", ".html"))
    typ = index_df["type"].str.upper()
    for m in (html & (typ == "EX-99.1"), html & (typ == "EX-99")):
        if m.any():
            return index_df.loc[m, "document"].iloc[0]
    return None


def doc_url(cik: int, accession: str, document: str) -> str:
    return f"{ARCHIVES}/{cik}/{accession.replace('-', '')}/{document}"


def quarter_end(q: Quarter) -> dt.date:
    m = q.q * 3
    nxt = dt.date(q.year + (m == 12), m % 12 + 1, 1)
    return nxt - dt.timedelta(days=1)


def quarter_of_date(d: dt.date) -> Quarter:
    return Quarter(d.year, (d.month - 1) // 3 + 1)


def fiscal_quarter_of_release(filed: dt.date) -> Quarter:
    """Latest calendar quarter that ended strictly before the filing date."""
    return quarter_of_date(filed) - 1


_WS = re.compile(r"\s+")


def html_to_text(html: bytes) -> str:
    """Visible text of an HTML exhibit, whitespace-normalised, one line per block element."""
    soup = BeautifulSoup(html, "lxml")
    for t in soup(["script", "style"]):
        t.decompose()
    text = soup.get_text("\n")
    lines = [_WS.sub(" ", ln).strip() for ln in text.splitlines()]
    return "\n".join(ln for ln in lines if ln)
