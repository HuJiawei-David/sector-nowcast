"""Wikipedia pageviews (Wikimedia Pageviews REST API), English Wikipedia, agent=user.

Pull: one request per (title, chunk of years) for every title listed in config/companies.yaml
(`wikipedia_articles[*].titles_since_2019`, including former titles), 2019-01-01 to the last
complete day. Each response is saved unmodified under data/raw/wikipedia_pageviews/<pull_date>/
(hard rule 8). Parse: reads only snapshots.

Series per name (hypotheses.md 3.3): daily sum over every listed article and every title it held
since 2019-01-01. Days before a title's first row count as zero for that title (the title did not
exist yet, e.g. "Trip.com Group" before the 2019-11-07 move). A missing day after a title's first
row, or a title that stops before the series end, is an error (rule 9).
"""
from __future__ import annotations

import datetime as dt
import json
import time
import urllib.parse
from pathlib import Path

import pandas as pd
import requests

from . import config
from .rawstore import RAW_DIR, read_snapshot, save_snapshot
from .wikimedia import WIKI_HEADERS

SOURCE = "wikipedia_pageviews"
API = ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/"
       "{project}/{access}/{agent}/{title}/daily/{start}/{end}")


class DataError(ValueError):
    """Rule 9: fail loudly."""


def titles_by_name(cos: dict | None = None) -> dict[str, list[str]]:
    cos = cos or config.companies()
    out = {}
    for name, c in cos.items():
        ts = []
        for art in c.get("wikipedia_articles") or []:
            ts.extend(art["titles_since_2019"])
        if len(set(ts)) != len(ts):
            raise DataError(f"{name}: duplicate Wikipedia titles in config: {ts}")
        out[name] = ts
    return out


def _snap_name(title: str, start: str, end: str) -> str:
    safe = title.replace(" ", "_").replace("/", "%2F")
    return f"{safe}__{start}_{end}.json"


def pull(end: dt.date | None = None, start: dt.date = dt.date(2019, 1, 1)) -> list[Path]:
    """Download every configured title, 2019-01-01 .. `end` (default: yesterday). Saves raw JSON."""
    defaults = config.load_yaml("companies.yaml")["defaults"]["wikipedia"]
    end = end or (dt.date.today() - dt.timedelta(days=1))
    paths = []
    for name, titles in titles_by_name().items():
        for title in titles:
            s, e = start.strftime("%Y%m%d"), end.strftime("%Y%m%d")
            url = API.format(project=defaults["project"], access=defaults["access"], agent=defaults["agent"],
                             title=urllib.parse.quote(title.replace(" ", "_"), safe=""), start=s, end=e)
            for attempt in range(6):
                r = requests.get(url, headers=WIKI_HEADERS, timeout=120)
                if r.status_code != 429:
                    break
                time.sleep(float(r.headers.get("Retry-After", 0)) or 10 * (attempt + 1))
            r.raise_for_status()
            params = {"url": url, "name": name, "title": title, "start": s, "end": e,
                      "project": defaults["project"], "access": defaults["access"],
                      "agent": defaults["agent"], "headers": WIKI_HEADERS}
            paths.append(save_snapshot(SOURCE, _snap_name(title, s, e), r.content, params))
            time.sleep(1.0)
    return paths


def _latest_dir() -> Path:
    base = RAW_DIR / SOURCE
    dirs = sorted(p for p in base.iterdir() if p.is_dir()) if base.exists() else []
    if not dirs:
        raise FileNotFoundError("no Wikipedia pageview snapshots; run scripts/s3_pull.py")
    return dirs[-1]


def load_title_views(snap_dir: Path | None = None) -> pd.DataFrame:
    """Long table: name, title, date, views (one row per title-day returned by the API)."""
    snap_dir = snap_dir or _latest_dir()
    rows = []
    for req in sorted(snap_dir.glob("*.request.json")):
        meta = json.loads(req.read_text())
        data = json.loads(read_snapshot(snap_dir / meta["stored_as"]))
        for it in data.get("items", []):
            rows.append({"name": meta["name"], "title": meta["title"],
                         "date": dt.datetime.strptime(it["timestamp"][:8], "%Y%m%d").date(),
                         "views": int(it["views"])})
    df = pd.DataFrame(rows)
    if df.empty:
        raise DataError(f"no pageview rows in {snap_dir}")
    if df.duplicated(["name", "title", "date"]).any():
        raise DataError("duplicate (name, title, date) pageview rows")
    return df


def daily_series(title_views: pd.DataFrame, start: dt.date, end: dt.date,
                 cos: dict | None = None) -> pd.DataFrame:
    """Per name, the daily sum over all titles (leading title-days before a title existed = 0).

    Every configured title must be present in the snapshot (else error). Returns columns
    name, date, value, n_titles_with_data.
    """
    want = titles_by_name(cos)
    days = pd.date_range(start, end, freq="D").date
    out = []
    for name, titles in want.items():
        sub = title_views[title_views.name == name]
        missing = set(titles) - set(sub.title)
        if missing:
            raise DataError(f"{name}: configured titles without a snapshot: {sorted(missing)}")
        wide = (sub.pivot(index="date", columns="title", values="views")
                .reindex(days).reindex(columns=titles))
        for t in titles:
            have = wide[t].notna()
            if not have.any():
                raise DataError(f"{name}/{t}: no views in {start}..{end}")
            first, last = have.idxmax(), have[::-1].idxmax()
            interior_gaps = (~have.loc[first:last]).sum()
            if interior_gaps or last != days[-1]:
                # A title may start late (it did not exist yet, e.g. a move target); it may not have
                # holes or stop early. Rule 9.
                raise DataError(f"{name}/{t}: {interior_gaps} missing day(s) inside {first}..{last}; series end {last}")
        n_with = wide.notna().sum(axis=1)
        out.append(pd.DataFrame({"name": name, "date": days, "value": wide.fillna(0).sum(axis=1).astype(int).values,
                                 "n_titles_with_data": n_with.values}))
    return pd.concat(out, ignore_index=True)
