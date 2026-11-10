"""Earnings releases: which filing reports which quarter, and every number we read from them.

Reads raw snapshots only (data/raw/sec_submissions, data/raw/sec_filings). Per-company patterns
live in config/extraction.yaml (hard rule 10); this module holds no company-specific logic.

Outputs (built by scripts/s2_build.py):
- release table: one row per earnings release (name, quarter, filed, accession, form, source URL)
- release values: every (metric, period, value) and stated YoY % read from each release, with the
  extractor that produced it. A release that restates a prior period simply yields another row
  for that period with its own filing date; nothing is overwritten.
"""
from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass

import pandas as pd

from . import config, filings
from .quarters import Quarter
from .rawstore import find_snapshot, read_snapshot

ORD = {"first": 1, "second": 2, "third": 3, "fourth": 4}
MONTH_Q = {"march": 1, "mar": 1, "june": 2, "jun": 2, "september": 3, "sept": 3, "sep": 3,
           "december": 4, "dec": 4}


class ExtractionError(RuntimeError):
    pass


# ----------------------------------------------------------------------------- release table

def _title_quarter(text: str) -> Quarter | None:
    head = re.sub(r"\s+", " ", text[:4000])
    pats = [
        r"\b(first|second|third|fourth)\s+quarter\s+(?:of\s+|and\s+full\s+year\s+(?:of\s+)?)?(?:fiscal\s+)?(20\d\d)",
        r"\b(first|second|third|fourth)\s+quarter\s+and\s+(?:full\s+year|first\s+half)\s+(?:of\s+)?(20\d\d)",
        r"\bQ([1-4])\s*[’']?\s*(20\d\d|\d\d)\b",
        r"\b([1-4])\s?(?:st|nd|rd|th)\s+quarter\s+(?:of\s+|and\s+full[\s-]year\s+)?(20\d\d)",
        r"\bquarter\s+ended\s+(march|june|september|december)\s+\d{1,2},\s+(20\d\d)",
    ]
    # patterns in priority order: spelled-out quarters first, bare "Q1 2020" tokens last (a letter
    # may mention earlier periods, e.g. "from Q1 2020 through Q3 2022", before naming its quarter)
    for group in ([pats[0], pats[1], pats[3], pats[4]], [pats[2]]):
        found = [m for p in group for m in [re.search(p, head, re.I)] if m]
        if found:
            m = min(found, key=lambda x: x.start())
            a, y = m.group(1).lower(), m.group(2)
            q = ORD.get(a) or MONTH_Q.get(a) or int(a)
            yy = int(y) + (2000 if len(y) == 2 else 0)
            return Quarter(yy, q)
    return None


@dataclass
class Release:
    name: str
    cik: int
    accession: str
    form: str
    filed: dt.date
    document: str
    quarter: Quarter
    url: str
    path: object

    def text(self) -> str:
        return normalize(filings.html_to_text(read_snapshot(self.path)))


def normalize(text: str) -> str:
    t = text.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"')
    t = t.replace("–", "-").replace("−", "-").replace("\xa0", " ")
    t = re.sub(r"\(\s+", "(", t)
    t = re.sub(r"\s+\)", ")", t)
    t = re.sub(r"\$\s+", "$", t)
    return re.sub(r"\s+", " ", t)


def release_table(name: str, co: dict, since: dt.date, tcom_regex: str) -> list[Release]:
    """Earnings releases of one company from the latest submissions + filings snapshots."""
    cik = co["cik"]
    sub = filings.submissions(name, cik)
    if co["region"] == "US":
        cand = filings.earnings_8k(sub, since)
    else:
        cand = sub[(sub["form"] == "6-K") & (sub["filingDate"] >= since)]
    out = []
    for _, r in cand.iterrows():
        idx_path = find_snapshot("sec_filings", f"{name}_{r.accessionNumber}_index.htm")
        if idx_path is None:
            raise FileNotFoundError(f"{name} {r.accessionNumber}: filing index not pulled (run s2_pull_sec.py)")
        if co["region"] != "US":
            prim = find_snapshot("sec_filings", f"{name}_{r.accessionNumber}_{r.primaryDocument}")
            if prim is None:
                raise FileNotFoundError(f"{name} {r.accessionNumber}: primary 6-K document not pulled")
            if not re.search(tcom_regex, filings.html_to_text(read_snapshot(prim)), re.I):
                continue
        ex = filings.exhibit_991(filings.parse_index(read_snapshot(idx_path)))
        if ex is None:
            continue      # Item 2.02 8-K without a results exhibit (listed by the build script)
        path = find_snapshot("sec_filings", f"{name}_{r.accessionNumber}_{ex}")
        if path is None:
            raise FileNotFoundError(f"{name} {r.accessionNumber}: exhibit {ex} not pulled")
        text = filings.html_to_text(read_snapshot(path))
        q_title = _title_quarter(text)
        q_filed = filings.fiscal_quarter_of_release(r.filingDate)
        if q_title is None:
            raise ExtractionError(f"{name} {r.accessionNumber}: cannot find the reported quarter in the title")
        if q_title != q_filed:
            raise ExtractionError(f"{name} {r.accessionNumber} filed {r.filingDate}: title says {q_title}, "
                                  f"filing date implies {q_filed}")
        out.append(Release(name, cik, r.accessionNumber, r.form, r.filingDate, ex, q_title,
                           filings.doc_url(cik, r.accessionNumber, ex), path))
    return out


# ----------------------------------------------------------------------------- value parsing

NUM_TOKEN = re.compile(r"\(?-?\$?\d[\d,]*(?:\.\d+)?\s?[MBK]?\)?|—|–")
PCT_TOKEN = re.compile(r"(\(?-?\d[\d,]*(?:\.\d+)?\)?|—|NM|N/M|n/m|\*\*)\s?%?")


def parse_num(tok: str) -> tuple[float | None, int]:
    """'(1,234.5)' -> (-1234.5, 1 decimal).  '—' -> (0.0, 0)."""
    t = tok.strip()
    if t in ("—", "–"):
        return 0.0, 0
    if t.upper() in ("NM", "N/M", "**"):
        return None, 0
    neg = t.startswith("(") or t.startswith("-")
    core = re.sub(r"[()$,\sMBK%-]", "", t)
    if not core:
        return None, 0
    v = float(core)
    dec = len(core.split(".")[1]) if "." in core else 0
    return (-v if neg else v), dec


def numbers(s: str) -> list[tuple[float, int]]:
    out = []
    for m in NUM_TOKEN.finditer(s or ""):
        v, d = parse_num(m.group(0))
        if v is not None:
            out.append((v, d))
    return out


def percents(s: str) -> list[tuple[float | None, int]]:
    return [parse_num(m.group(1)) for m in PCT_TOKEN.finditer(s or "") if m.group(1).strip()]


# ----------------------------------------------------------------------------- header -> periods

_EXPLICIT = re.compile(
    r"\bQ([1-4])\s*[']?\s*(20\d\d|\d\d)\b"                                   # Q3 2026 / Q3'26
    r"|\b([1-4])Q\s*[']?(20\d\d|\d\d)\b"                                      # 3Q26
    r"|\b(March|Mar\.?|June|Jun\.?|September|Sept\.?|Sep\.?|December|Dec\.?)\s*\d{1,2},?\s+(20\d\d)\b"
    r"|\b(FY|Full Year|Total)\s*(20\d\d)?\b", re.I)


def explicit_periods(hdr: str) -> list:
    out = []
    for m in _EXPLICIT.finditer(hdr or ""):
        if m.group(1):
            out.append(Quarter(int(m.group(2)) + (2000 if len(m.group(2)) == 2 else 0), int(m.group(1))))
        elif m.group(3):
            out.append(Quarter(int(m.group(4)) + (2000 if len(m.group(4)) == 2 else 0), int(m.group(3))))
        elif m.group(5):
            mon = m.group(5).lower().rstrip(".")
            out.append(Quarter(int(m.group(6)), MONTH_Q[mon]))
        else:
            out.append("nonquarter")
    return out


def periods_for(layout: dict, hdr: str | None, n: int, rq: Quarter) -> list:
    """Period of each of the n value columns, per the extractor's layout (config/extraction.yaml)."""
    kind = layout["kind"]
    if kind == "relative":
        offs = layout["offsets"]
        per = [rq + o for o in offs] + ["nonquarter"] * max(0, n - len(offs))
        if layout.get("validate_explicit", True) and hdr:
            exp = [p for p in explicit_periods(hdr)][:len(offs)]
            if len(exp) == len(offs) and exp != per[:len(offs)]:
                raise ExtractionError(f"header periods {list(map(str, exp))} != expected {list(map(str, per[:len(offs)]))}")
        return per[:n]
    if kind == "explicit":
        exp = explicit_periods(hdr)
        if len(exp) < n:
            exp = exp + ["nonquarter"] * (n - len(exp))
        return exp[:n]
    if kind == "consecutive":
        # quarter columns run consecutively and end at the release quarter; Q tokens validate it
        nq = n - int(layout.get("trailing_nonquarter", 0))
        qtok = [int(x) for x in re.findall(r"\bQ([1-4])\b", hdr or "")]
        if layout.get("count_from_header") and qtok:
            nq = len(qtok)
        per = [rq - (nq - 1 - i) for i in range(nq)]
        if qtok and len(qtok) == nq and [p.q for p in per] != qtok:
            raise ExtractionError(f"quarter tokens {qtok} do not end at release quarter {rq}")
        return per + ["nonquarter"] * (n - nq)
    if kind == "year_groups":
        # "2019 2021 2022 Q1 Q2 Q3 Q4 Q1 Q2 Q3 Q4 Q1": each listed year owns one run of Q tokens
        # (a run ends when the quarter number stops increasing). Years need not be consecutive.
        years = [int(y) for y in re.findall(r"\b(20\d\d)\b", hdr or "")]
        qtok = [int(x) for x in re.findall(r"\bQ([1-4])\b", hdr or "")]
        groups, cur = [], []
        for qn in qtok:
            if cur and qn <= cur[-1]:
                groups.append(cur)
                cur = []
            cur.append(qn)
        if cur:
            groups.append(cur)
        if len(groups) != len(years):
            raise ExtractionError(f"year_groups: {len(years)} years {years} but {len(groups)} quarter runs {groups}")
        per = [Quarter(y, qn) for y, g in zip(years, groups) for qn in g]
        if per[-1] != rq:
            raise ExtractionError(f"year_groups: last column {per[-1]} is not the release quarter {rq}")
        if len(per) < n:
            per = per + ["nonquarter"] * (n - len(per))
        return per[:n]
    if kind == "year_label_pairs":
        years = re.findall(r"\b(20\d\d)\b", hdr or "")
        labels = re.findall(r"\b(Q[1-4]|Total|FY)\b", hdr or "", re.I)
        if len(years) != len(labels):
            raise ExtractionError(f"year/label header mismatch: {years} vs {labels}")
        per = [Quarter(int(y), int(lb[1])) if lb.upper().startswith("Q") else "nonquarter"
               for y, lb in zip(years, labels)]
        if len(per) < n:
            raise ExtractionError(f"{n} values but only {len(per)} header columns")
        return per[:n]
    if kind == "years_same_quarter":
        years = [int(y) for y in re.findall(r"\b(20\d\d)\b", hdr or "")][:n]
        if len(years) < n:
            raise ExtractionError(f"{n} values but years {years} in header")
        return [Quarter(y, rq.q) for y in years]
    raise ValueError(f"unknown layout kind {kind}")


# ----------------------------------------------------------------------------- extraction

def extract(rel: Release, spec: dict, text: str | None = None) -> tuple[list[dict], list[str]]:
    """Apply every extractor of one company to one release.

    Returns (rows, missing): rows = one dict per value / stated YoY; missing = ids of extractors
    that are `required` for this release quarter but did not match (the caller fails loudly).
    """
    text = text if text is not None else rel.text()
    rows, missing = [], []
    for ex in spec["extractors"]:
        lo = Quarter.parse(ex["from"]) if ex.get("from") else None
        hi = Quarter.parse(ex["to"]) if ex.get("to") else None
        if (lo and rel.quarter < lo) or (hi and rel.quarter > hi):
            continue
        if ex.get("quarters") and rel.quarter.q not in ex["quarters"]:
            continue
        rx = re.compile(ex["regex"], re.I)
        matches = list(rx.finditer(text))
        if not matches:
            if ex.get("required", False):
                missing.append(ex["id"])
            continue
        # a match whose qualifier group fired ("Excluding North America, ...", "In EMEA, ...") is not
        # the company-wide figure and is skipped
        rej = ex.get("reject_groups", [])
        matches = [m for m in matches if not any(m.groupdict().get(k) for k in rej)]
        if not matches and ex.get("required", False):
            missing.append(ex["id"])
        for mi, m in enumerate(matches[: ex.get("max_matches", 1)]):
            g = _merge_alternatives(m.groupdict())
            base = {"name": rel.name, "metric": ex["metric"], "extractor": ex["id"],
                    "release_quarter": str(rel.quarter), "filed": rel.filed, "accession": rel.accession,
                    "form": rel.form, "source_url": rel.url, "unit": ex.get("unit", ""),
                    "snippet": m.group(0)[:300]}
            scale = float(ex.get("scale", 1.0))
            if g.get("unit"):
                scale = float(ex["unit_scale"][g["unit"].lower()])
            if g.get("vals") is not None:
                vals = numbers(g["vals"])
                per = periods_for(ex["layout"], g.get("hdr"), len(vals), rel.quarter)
                for (v, dec), p in zip(vals, per):
                    if p == "nonquarter":
                        continue
                    rows.append({**base, "quarter": str(p), "kind": "value", "value": v * scale,
                                 "decimals": dec, "precision": scale * 10 ** -dec, "role": _role(p, rel.quarter)})
                if g.get("yoys") is not None:
                    ys = percents(g["yoys"])
                    yper = per
                    if ex.get("yoy_for") == "current":
                        if len(ys) != 1:
                            raise ExtractionError(f"{ex['id']}: expected one Y/Y value, got {len(ys)}")
                        yper = [rel.quarter]
                    elif ex.get("yoy_align") == "right":
                        # Y/Y row shorter than the value row: it covers the latest quarter columns
                        qcols = [p for p in per if p != "nonquarter"]
                        if len(ys) > len(qcols):
                            raise ExtractionError(f"{ex['id']}: {len(ys)} Y/Y values for {len(qcols)} quarters")
                        yper = qcols[len(qcols) - len(ys):]
                    for (y, dec), p in zip(ys, yper):
                        if p == "nonquarter" or y is None:
                            continue
                        rows.append({**base, "quarter": str(p), "kind": "stated_yoy_pct", "value": y,
                                     "decimals": dec, "precision": 10 ** -dec, "role": _role(p, rel.quarter)})
            elif g.get("cur") is not None:
                # sentence with levels: "revenue of $969.9 million versus $569.9 million in Q4 2020"
                for key, p in (("cur", rel.quarter), ("prior", rel.quarter - 4)):
                    if g.get(key) is None:
                        continue
                    v, dec = parse_num(g[key])
                    f = float(ex["unit_scale"][g[key + "_unit"].lower()])
                    rows.append({**base, "quarter": str(p), "kind": "value", "value": v * f,
                                 "decimals": dec, "precision": f * 10 ** -dec, "role": _role(p, rel.quarter)})
                if g.get("yoy") is not None:
                    y, dec = parse_num(g["yoy"])
                    rows.append({**base, "quarter": str(rel.quarter), "kind": "stated_yoy_pct", "value": y,
                                 "decimals": dec, "precision": 10 ** -dec, "role": "current"})
            elif g.get("yoy") is not None or g.get("flat"):
                # "flat" = the company rounds the change to 0%
                y, dec = (0.0, 0) if g.get("flat") else parse_num(g["yoy"])
                dirv = g.get("dir")
                if dirv and re.match(r"(decreas|declin|down|fell|lower)", dirv, re.I):
                    y = -abs(y)
                if y is not None:
                    rows.append({**base, "quarter": str(rel.quarter), "kind": "stated_yoy_pct", "value": y,
                                 "decimals": dec, "precision": 10 ** -dec, "role": "current"})
    return rows, missing


def _merge_alternatives(g: dict) -> dict:
    """Regex alternatives name their groups x, x2, x3 (Python forbids duplicate names); fold them."""
    out = dict(g)
    for k, v in g.items():
        m = re.fullmatch(r"([a-z_]+?)(\d)(_unit)?", k)
        if m and v is not None:
            base = m.group(1) + (m.group(3) or "")
            if out.get(base) is None:
                out[base] = v
    return out


def _role(p: Quarter, rq: Quarter) -> str:
    if p == rq:
        return "current"
    if p == rq - 4:
        return "prior_year_comparative"
    return "other_period"
