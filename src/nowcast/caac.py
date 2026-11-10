"""CAAC monthly civil-aviation passenger traffic (民航旅客运输量), national total.

Source (hard rule 7): caac.gov.cn, 信息公开 -> 统计数据 -> 月度运输生产统计 (classification 112).
Each month CAAC publishes a bulletin page "中国民航YYYY年M月份主要生产指标统计" whose attachment
(PDF, older months may differ) holds the table; the row 旅客运输量 (万人) gives the month's
passenger traffic and its Y/Y %.

Publication date (hard rule 2): the 发文日期 recorded on the bulletin page itself; the listing
page's 发文日期 is recorded too. If they differ the LATER one is used (conservative). If neither can
be recorded the month-end + 45 days fallback applies and the row is flagged.

Pull: listing pages, every bulletin page and its attachment are saved unmodified under
data/raw/caac/<pull_date>/ (hard rule 8). Parse: reads only those snapshots.
"""
from __future__ import annotations

import datetime as dt
import io
import json
import re
import time
import urllib.parse
from pathlib import Path

import pandas as pd
import requests
from bs4 import BeautifulSoup

from .pit import month_end
from .rawstore import RAW_DIR, read_snapshot, save_snapshot

SOURCE = "caac"
HEADERS = {"User-Agent": "sector-nowcast-research/0.1 (non-commercial research tool; python-requests)"}
LIST_URL = "https://www.caac.gov.cn/was5/web/search"
LIST_PARAMS = {"channelid": "211383",
               "was_custom_expr": " PARENTID='112' or CLASSINFOID='112' ",
               "perpage": "10", "outlinepage": "7", "orderby": "-fabuDate", "selST": "All", "fl": "112"}
TITLE_RE = re.compile(r"中国民航(\d{4})年(\d{1,2})月份?主要(?:运输)?生产指标统计")  # 2019 and earlier: 主要运输生产指标统计
DATE_RE = re.compile(r"(\d{4})[年\-](\d{1,2})[月\-](\d{1,2})")


class DataError(ValueError):
    """Rule 9: fail loudly."""


def _get(url: str, params: dict | None = None) -> requests.Response:
    for attempt in range(4):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=60)
            r.raise_for_status()
            return r
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(5 * (attempt + 1))
    raise RuntimeError("unreachable")


def _date(s: str) -> dt.date | None:
    m = DATE_RE.search(s or "")
    return dt.date(int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def parse_listing(html: bytes) -> tuple[list[dict], int]:
    """Bulletin rows on one listing page and the total page count."""
    soup = BeautifulSoup(html, "lxml")
    rows = []
    for a in soup.find_all("a", href=True):
        m = TITLE_RE.search(a.get_text(strip=True))
        if not m:
            continue
        tr = a.find_parent("tr")
        listing_date = _date(tr.get_text(" ", strip=True)) if tr else None
        rows.append({"year": int(m.group(1)), "month": int(m.group(2)), "title": a.get_text(strip=True),
                     "url": a["href"], "listing_date": listing_date})
    m = re.search(r"共\s*(\d+)\s*页", soup.get_text(" ", strip=True))
    return rows, int(m.group(1)) if m else 1


def _dedupe_rows(rows: list[dict]) -> list[dict]:
    seen, out = set(), []
    for r in rows:
        k = (r["year"], r["month"], r["url"])
        if k not in seen:
            seen.add(k)
            out.append(r)
    return out


def pull(first_month: str = "2019-01", pull_date: dt.date | None = None,
         skip_existing: bool = True) -> pd.DataFrame:
    """Download listing pages (until the first month is passed), bulletin pages and attachments."""
    fy, fm = map(int, first_month.split("-"))
    page, n_pages, rows = 1, None, []
    while True:
        params = {"page": str(page), **LIST_PARAMS}
        r = _get(LIST_URL, params)
        save_snapshot(SOURCE, f"listing_p{page:02d}.html", r.content,
                      {"url": r.url, "params": params, "headers": HEADERS}, pull_date)
        prow, n_pages = parse_listing(r.content)
        rows.extend(prow)
        page += 1
        oldest = min(((x["year"], x["month"]) for x in prow), default=(9999, 12))
        if page > n_pages or oldest < (fy, fm):
            break
        time.sleep(1.0)
    rows = [x for x in _dedupe_rows(rows) if (x["year"], x["month"]) >= (fy, fm)]
    for x in rows:
        stem = f"bulletin_{x['year']}-{x['month']:02d}"
        if skip_existing and (RAW_DIR / SOURCE / (pull_date or dt.date.today()).isoformat() / (stem + ".html")).exists():
            continue
        r = _get(x["url"])
        save_snapshot(SOURCE, stem + ".html", r.content, {"url": x["url"], "headers": HEADERS,
                      "listing_title": x["title"], "listing_date": str(x["listing_date"])}, pull_date)
        for i, att in enumerate(_attachments(r.content, x["url"])):
            ext = Path(urllib.parse.urlparse(att).path).suffix.lower() or ".bin"
            ra = _get(att)
            save_snapshot(SOURCE, f"{stem}_att{i}{ext}", ra.content, {"url": att, "headers": HEADERS,
                          "bulletin_url": x["url"]}, pull_date)
            time.sleep(0.5)
        time.sleep(0.8)
    return pd.DataFrame(rows)


def _attachments(html: bytes, page_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    out = []
    for a in soup.find_all("a", href=True):
        h = a["href"]
        if re.search(r"\.(pdf|xlsx?|docx?|et|wps)$", h, re.I):
            out.append(urllib.parse.urljoin(page_url, h))
    return list(dict.fromkeys(out))


def page_release_date(html: bytes) -> dt.date | None:
    """发文日期 on the bulletin page (the first date after the label)."""
    text = BeautifulSoup(html, "lxml").get_text("\n", strip=True)
    m = re.search(r"发文日期[：:]\s*\n?\s*(\d{4}-\d{1,2}-\d{1,2}|\d{4}年\d{1,2}月\d{1,2}日)", text)
    return _date(m.group(1)) if m else None


PAX_RE = re.compile(r"旅客运输量\s*万人\s*([\d,]+\.?\d*)\s+(-?[\d.]+)")


def parse_pax(text: str) -> tuple[float, float] | None:
    """(level in 10k persons, Y/Y %) for the national 旅客运输量 row, or None."""
    m = PAX_RE.search(text.replace("　", " "))
    if not m:
        return None
    return float(m.group(1).replace(",", "")), float(m.group(2))


def attachment_text(path: Path) -> str:
    data = read_snapshot(path)
    name = path.name.removesuffix(".gz").lower()
    if name.endswith(".pdf"):
        import pypdf
        return "\n".join(p.extract_text() or "" for p in pypdf.PdfReader(io.BytesIO(data)).pages)
    if name.endswith((".html", ".htm")):
        return BeautifulSoup(data, "lxml").get_text(" ", strip=True)
    raise DataError(f"unsupported attachment type: {path.name}")


def _latest_dir() -> Path:
    base = RAW_DIR / SOURCE
    dirs = sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []
    if not dirs:
        raise FileNotFoundError("no CAAC snapshots; run scripts/s3_pull.py")
    return dirs[-1]


def parse(snap_dir: Path | None = None, fallback_lag_days: int = 45) -> pd.DataFrame:
    """One row per month: month, value (万人), yoy_stated_pct, release dates, published, source URLs."""
    snap_dir = snap_dir or _latest_dir()
    rows = []
    for req in sorted(snap_dir.glob("bulletin_*.html.request.json")):
        meta = json.loads(req.read_text())
        ym = re.search(r"bulletin_(\d{4})-(\d{2})", req.name)
        y, m = int(ym.group(1)), int(ym.group(2))
        html = read_snapshot(snap_dir / meta["stored_as"])
        page_date = page_release_date(html)
        listing_date = _date(meta.get("listing_date") or "")
        source_texts = [BeautifulSoup(html, "lxml").get_text(" ", strip=True)]
        att_paths = sorted(p for p in snap_dir.glob(f"bulletin_{y}-{m:02d}_att*")
                           if not p.name.endswith(".request.json"))
        att_urls = []
        for p in att_paths:
            source_texts.insert(0, attachment_text(p))
            att_urls.append(json.loads((snap_dir / (p.name.removesuffix(".gz") + ".request.json")).read_text())["url"])
        parsed = None
        for t in source_texts:
            parsed = parse_pax(t)
            if parsed:
                break
        recorded = [d for d in (page_date, listing_date) if d]
        if recorded:
            published, rule = max(recorded), "recorded_from_source_page"
        else:
            published = month_end(dt.date(y, m, 1)) + dt.timedelta(days=fallback_lag_days)
            rule = f"fallback_month_end_plus_{fallback_lag_days}"
        rows.append({"month": f"{y}-{m:02d}", "obs_date": dt.date(y, m, 1),
                     "value": parsed[0] if parsed else None, "yoy_stated_pct": parsed[1] if parsed else None,
                     "page_release_date": page_date, "listing_release_date": listing_date,
                     "published": published, "publication_rule": rule,
                     "bulletin_url": meta["url"], "attachment_urls": " ".join(att_urls)})
    df = pd.DataFrame(rows)
    if df.empty:
        raise DataError(f"no CAAC bulletins in {snap_dir}")
    if df.month.duplicated().any():
        raise DataError(f"duplicate CAAC months: {df.month[df.month.duplicated()].tolist()}")
    return df.sort_values("month").reset_index(drop=True)


def coverage(df: pd.DataFrame, first: str = "2019-01") -> dict:
    """HKIA-trigger evidence (hypotheses 3.6): months missing / unparsed / without a date rule."""
    last = df.month.max()
    want = [p.strftime("%Y-%m") for p in pd.period_range(first, last, freq="M")]
    have = set(df.month)
    return {"first": first, "latest_published_month": last, "n_expected": len(want),
            "missing_months": [x for x in want if x not in have],
            "unparsed_months": df.loc[df.value.isna(), "month"].tolist(),
            "fallback_date_months": df.loc[df.publication_rule != "recorded_from_source_page", "month"].tolist()}
