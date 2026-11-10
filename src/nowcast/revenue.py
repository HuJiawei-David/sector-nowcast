"""Quarterly revenue with every filed version, and the point-in-time (as-of) view.

US names: SEC companyfacts (XBRL). Every fact keeps value, fy, fp, form, start, end, filed and
accession. A filing that reports a discrete quarter (3-month fact) gives a `reported_3m` version.
A filing that reports only a year-to-date amount gives a `derived_ytd` version:
    quarter = YTD(this filing) - preceding YTD (same filing if it has it, else the latest version
    of that preceding YTD filed on or before this filing).
Q4 is always derived from a 10-K: Q4 = FY - 9-month YTD.

TCOM: quarterly net revenue (RMB) from the 6-K results releases (src/nowcast/releases.py); each
release gives versions for q, q-1 and q-4, point-in-time date = 6-K filing date.

As-of rule (hard rule 2): a version is usable for a call with as-of date `asof` only if
filed < asof. The as-of view picks, per quarter, the latest such version (restatements).
"""
from __future__ import annotations

import datetime as dt
import gzip
import json

import pandas as pd

from .filings import quarter_end, quarter_of_date
from .pit import assert_pit
from .quarters import Quarter, qrange
from .rawstore import RAW_DIR, read_snapshot


class DataError(ValueError):
    """Rule 9: fail loudly."""


def load_companyfacts(ticker: str, cik: int, pull_date: str | None = None) -> dict:
    base = RAW_DIR / "sec_companyfacts"
    dates = [pull_date] if pull_date else sorted((p.name for p in base.iterdir() if p.is_dir()), reverse=True)
    for d in dates:
        for name in (f"{ticker}_CIK{cik:010d}.json.gz", f"{ticker}_CIK{cik:010d}.json"):
            p = base / d / name
            if p.exists():
                return json.loads(read_snapshot(p))
    raise FileNotFoundError(f"no companyfacts snapshot for {ticker}")


def facts_table(cf: dict, tags: list[str], unit: str, bands: dict) -> pd.DataFrame:
    """All duration facts for `tags` (us-gaap) in `unit`, with period kind and calendar checks."""
    rows = []
    gaap = cf["facts"].get("us-gaap", {})
    for prio, tag in enumerate(tags):
        for r in gaap.get(tag, {}).get("units", {}).get(unit, []):
            if "start" not in r:
                continue
            rows.append({"tag": tag, "tag_priority": prio, "start": dt.date.fromisoformat(r["start"]),
                         "end": dt.date.fromisoformat(r["end"]), "value": float(r["val"]),
                         "accession": r["accn"], "fy": r.get("fy"), "fp": r.get("fp"), "form": r["form"],
                         "filed": dt.date.fromisoformat(r["filed"]), "frame": r.get("frame")})
    df = pd.DataFrame(rows)
    if df.empty:
        return df
    df = df.drop_duplicates(["tag", "accession", "start", "end", "value"])
    days = (pd.to_datetime(df["end"]) - pd.to_datetime(df["start"])).dt.days + 1

    def kind(d):
        for k, (lo, hi) in (("3m", bands["quarter_days"]), ("6m", bands["half_days"]),
                            ("9m", bands["nine_month_days"]), ("12m", bands["year_days"])):
            if lo <= d <= hi:
                return k
        return "other"
    df["period"] = [kind(d) for d in days]
    # first tag (config order) with a fact for this (filing, period) wins
    df = df.sort_values("tag_priority").drop_duplicates(["accession", "start", "end"], keep="first")
    return df.sort_values(["end", "filed", "accession"]).reset_index(drop=True)


def check_calendar(df: pd.DataFrame, ticker: str, first: Quarter) -> None:
    """Rule 9: non-calendar fiscal quarters raise. Checked for facts ending on/after `first`."""
    lo = quarter_end(first - 1)
    sub = df[df["end"] > lo]
    for _, r in sub.iterrows():
        q = quarter_of_date(r["end"])
        if r["end"] != quarter_end(q):
            raise DataError(f"{ticker}: fact ends {r['end']} (not a calendar quarter end), accession {r['accession']}")
        if r["period"] == "other":
            raise DataError(f"{ticker}: fact {r['start']}..{r['end']} has a non-standard duration ({r['accession']})")
        if r["period"] in ("6m", "9m", "12m") and (r["start"].month, r["start"].day) != (1, 1):
            raise DataError(f"{ticker}: YTD fact {r['start']}..{r['end']} does not start on Jan 1 ({r['accession']})")
        if r["period"] == "3m" and r["start"] != quarter_end(q - 1) + dt.timedelta(days=1):
            raise DataError(f"{ticker}: quarterly fact {r['start']}..{r['end']} is not a calendar quarter")


_PREV = {"6m": "3m", "9m": "6m", "12m": "9m"}
_NQ = {"3m": 1, "6m": 2, "9m": 3, "12m": 4}


def _cum_key(end: dt.date, period: str) -> tuple[int, int]:
    """(year, number of quarters) identifying a Jan-1-based cumulative amount."""
    return end.year, _NQ[period]


def versions_from_facts(df: pd.DataFrame, ticker: str, currency: str, url_for) -> pd.DataFrame:
    """One row per (quarter, filing) version: reported 3-month facts, else YTD differences."""
    out = []
    # cumulative amounts per (year, n_quarters): list of (filed, accession, value); 3m Q1 counts as cum 1
    cum: dict[tuple[int, int], list] = {}
    for _, r in df.iterrows():
        if r["period"] == "3m" and r["end"].month == 3:
            cum.setdefault((r["end"].year, 1), []).append((r["filed"], r["accession"], r["value"]))
        elif r["period"] in _PREV:
            cum.setdefault(_cum_key(r["end"], r["period"]), []).append((r["filed"], r["accession"], r["value"]))

    def latest_cum(key, filed, accession):
        cands = cum.get(key, [])
        same = [c for c in cands if c[1] == accession]
        if same:
            return same[0], "same filing"
        prior = [c for c in cands if c[0] <= filed]
        if not prior:
            return None, None
        best = max(prior, key=lambda c: (c[0], c[1]))
        return best, "latest filed on/before"

    for accn, g in df.groupby("accession"):
        filed = g["filed"].iloc[0]
        form = g["form"].iloc[0]
        quarters_3m = {quarter_of_date(e) for e in g.loc[g["period"] == "3m", "end"]}
        for _, r in g.iterrows():
            base = {"name": ticker, "currency": currency, "filed": filed, "accession": accn, "form": form,
                    "fy": r["fy"], "fp": r["fp"], "tag": r["tag"], "source_url": url_for(accn)}
            q = quarter_of_date(r["end"])
            if r["period"] == "3m":
                out.append({**base, "quarter": str(q), "value": r["value"], "period_start": r["start"],
                            "period_end": r["end"], "method": "reported_3m", "derivation": ""})
            elif r["period"] in _PREV and q not in quarters_3m:
                prev_key = (r["end"].year, _NQ[r["period"]] - 1)
                prev, how = latest_cum(prev_key, filed, accn)
                if prev is None:
                    continue           # cannot derive (no preceding YTD known at this filing date)
                out.append({**base, "quarter": str(q), "value": r["value"] - prev[2],
                            "period_start": quarter_end(q - 1) + dt.timedelta(days=1), "period_end": r["end"],
                            "method": "derived_ytd",
                            "derivation": f"{r['period']} {r['value']:.0f} ({accn}) - {_NQ[r['period']] - 1}Q YTD "
                                          f"{prev[2]:.0f} ({prev[1]}, {how})"})
    v = pd.DataFrame(out)
    if v.empty:
        return v
    if v.duplicated(["name", "quarter", "accession"]).any():
        dup = v[v.duplicated(["name", "quarter", "accession"], keep=False)]
        raise DataError(f"{ticker}: duplicate (quarter, accession) versions:\n{dup}")
    return v.sort_values(["quarter", "filed", "accession"]).reset_index(drop=True)


def us_revenue_versions(ticker: str, co: dict, bands: dict, first: Quarter) -> pd.DataFrame:
    cf = load_companyfacts(ticker, co["cik"])
    df = facts_table(cf, co["revenue"]["xbrl_tags"], co["revenue"]["currency"], bands)
    df = df[df["end"] > quarter_end(first - 5)]          # keep what is needed to derive from `first`
    check_calendar(df, ticker, first)
    cik = co["cik"]

    def url_for(accn):
        return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accn.replace('-', '')}/{accn}-index.htm"
    v = versions_from_facts(df, ticker, co["revenue"]["currency"], url_for)
    v["value"] = v["value"] / 1e6
    v["unit"] = f"{co['revenue']['currency']} millions"
    return v[v["quarter"].map(Quarter.parse) >= first].reset_index(drop=True)


def annual_facts(ticker: str, co: dict, tags: list[str], unit: str, bands: dict) -> pd.DataFrame:
    cf = load_companyfacts(ticker, co["cik"])
    df = facts_table(cf, tags, unit, bands)
    return df[df["period"] == "12m"].assign(value=lambda d: d["value"] / 1e6)


def release_revenue_versions(values: pd.DataFrame, ticker: str, currency: str) -> pd.DataFrame:
    """Revenue versions from press-release values (TCOM): one per (quarter, release)."""
    v = values[(values["name"] == ticker) & (values["metric"] == "revenue") & (values["kind"] == "value")]
    v = v.assign(currency=currency, method="press_release", derivation=v["extractor"], tag="",
                 fy=None, fp=None, period_start=None, period_end=None)
    cols = ["name", "quarter", "value", "unit", "currency", "period_start", "period_end", "fy", "fp", "form",
            "filed", "accession", "tag", "method", "derivation", "source_url"]
    return v[cols].sort_values(["quarter", "filed"]).reset_index(drop=True)


# ----------------------------------------------------------------------------- as-of view

_METHOD_RANK = {"reported_3m": 0, "press_release": 0, "derived_ytd": 1}


def asof_view(versions: pd.DataFrame, asof: dt.date) -> pd.DataFrame:
    """Per (name, quarter): the latest version filed strictly before `asof`."""
    v = versions[pd.to_datetime(versions["filed"]).dt.date < asof].copy()
    if v.empty:
        return v
    v["_rank"] = v["method"].map(_METHOD_RANK).fillna(9)
    v = v.sort_values(["name", "quarter", "filed", "_rank", "accession"],
                      ascending=[True, True, True, False, True])
    out = v.groupby(["name", "quarter"], as_index=False).tail(1).drop(columns="_rank")
    assert_pit(out.rename(columns={"filed": "published"}), asof, strict=True)
    return out.reset_index(drop=True)


def first_reported(versions: pd.DataFrame) -> pd.DataFrame:
    """Per (name, quarter): the first version filed (realised outcome, hypotheses.md 3.11)."""
    v = versions.copy()
    v["_rank"] = v["method"].map(_METHOD_RANK).fillna(9)
    v = v.sort_values(["name", "quarter", "filed", "_rank", "accession"])
    return v.groupby(["name", "quarter"], as_index=False).head(1).drop(columns="_rank").reset_index(drop=True)


def yoy_same_filing(versions: pd.DataFrame, name: str, q: Quarter, filing_choice: str = "first",
                    asof: dt.date | None = None) -> dict | None:
    """Like-for-like YoY (hypotheses.md 3.11): value(q) / value(q-4) from the SAME filing.

    filing_choice='first': the first filing that reports q (realised outcome).
    filing_choice='asof' : the latest filing filed before `asof` that reports q.
    """
    v = versions[versions["name"] == name]
    cur = v[v["quarter"] == str(q)]
    if filing_choice == "asof":
        cur = cur[pd.to_datetime(cur["filed"]).dt.date < asof]
    if cur.empty:
        return None
    cur = cur.assign(_rank=cur["method"].map(_METHOD_RANK).fillna(9))
    cur = cur.sort_values(["filed", "_rank", "accession"])
    # walk candidate filings in order of preference; the first with a q-4 comparative wins
    cands = cur.iloc[::-1] if filing_choice == "asof" else cur
    for _, c in cands.iterrows():
        base = v[(v["quarter"] == str(q - 4)) & (v["accession"] == c["accession"])]
        if len(base):
            b = base.iloc[0]
            return {"name": name, "quarter": str(q), "value": c["value"], "base_value": b["value"],
                    "yoy_pct": 100.0 * (c["value"] / b["value"] - 1.0), "filed": c["filed"],
                    "accession": c["accession"], "form": c["form"], "method": c["method"],
                    "base_method": b["method"], "source_url": c["source_url"]}
    return None


def required_range(first: Quarter, last_reported: Quarter) -> list[Quarter]:
    return qrange(first, last_reported)
