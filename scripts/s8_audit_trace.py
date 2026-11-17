"""Session 8 audit, item 3 (traceability). No network. Writes outputs/tables/audit_traceability.csv.

    .venv/bin/python scripts/s8_audit_trace.py

Every numeric token in README.md, outputs/memos/*.md, docs/cv_bullets.md and every numeric cell of the tracker
workbook is looked up in the files the document cites:
  * CSV sources (outputs/tables/*.csv; per-name memos use only that name's rows, plus the shared TSA / multiple-
    testing / power rows): a token with d decimals matches a cell v if round(v, d), round(100 v, d) or their
    absolute values equal the token;
  * "H of N" and "H/N" pairs must match a (hits, N), (momentum hits, N), (inflections caught, scored) or
    (need, N) pair of that name in results / robustness / lead_time / inflections_summary / power_table;
  * text sources (config/*.yaml, docs/drivers.md, docs/hypotheses.md): the token must appear in that text.
Tokens that are dates, quarter labels, URLs, hashes, section numbers or file names are not numbers and are skipped.
Rows with status 'unmatched' are reviewed by hand in docs/audit.md.
"""
import re
import sys
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

sys.path.insert(0, "src")
from nowcast.rawstore import REPO_ROOT  # noqa: E402

T = REPO_ROOT / "outputs" / "tables"
NAMES = ["BKNG", "EXPE", "ABNB", "UBER", "LYFT", "DASH", "TCOM"]
CSVS = ["results", "robustness", "lead_time", "inflections_summary", "live_calls", "live_calls_tcom_2026Q3",
        "live_tsa_sensitivity", "multiple_testing", "power_table", "geo_mix_fy2025", "bkng_k_rounding_check",
        "caac_yoy_check", "revenue_yoy", "kpi_yoy", "relevancy_matrix", "tsa_dependence", "placebo_wrong_company",
        "snapshot_revision_check", "calls", "live_calls_scored", "tcom_caac_small_moves", "audit_asof_minus_1",
        "audit_asof_minus_1_cells"]
TEXTS = ["config/guidance.yaml", "config/breaks.yaml", "config/companies.yaml", "docs/drivers.md", "docs/hypotheses.md",
         "config/pipeline.yaml"]
SKIP = re.compile(r"https?://\S+|\b\d{4}-\d{2}-\d{2}\b|\b\d{4}Q[1-4]\b|\b[0-9a-f]{7,64}\b|§\s?\d+(?:\.\d+)?|"
                  r"\b[\w/.-]+\.(?:csv|md|yaml|py|png|xlsx|sql|sh|htm)\b|\bQ[1-4]\b|\b3\.1[0-2]\b|\b20[12]\d\b|"
                  r"\bH\d\b|Python 3\.12|x02|\bday (?:28|56)\b|\b364\b")
TOKEN = re.compile(r"(?<![\w.])([-−+]?)\$?(\d[\d,]*(?:\.\d+)?)")
PAIR = re.compile(r"\b(\d+)\s*(?:of|/)\s*(\d+)\b")


def frames() -> dict[str, pd.DataFrame]:
    return {c: pd.read_csv(T / f"{c}.csv") for c in CSVS if (T / f"{c}.csv").exists()}


def pool_for(fr: dict, name: str | None) -> list[tuple[float, str]]:
    out = []
    for c, df in fr.items():
        d = df
        if name and "name" in df.columns:
            d = df[df["name"] == name]
        for col in d.columns:
            vals = pd.to_numeric(d[col], errors="coerce").dropna().unique()
            out += [(float(v), f"{c}.csv:{col}") for v in vals if np.isfinite(v)]
        for col in [c_ for c_ in d.columns if not pd.api.types.is_numeric_dtype(d[c_])]:          # numbers embedded in note / detail strings
            for s in d[col].dropna().unique():
                for m in TOKEN.finditer(SKIP.sub(" ", str(s))):
                    out.append((float(m.group(2).replace(",", "")), f"{c}.csv:{col} (text)"))
    return out


def pairs_for(fr: dict, name: str | None) -> set[tuple[int, int]]:
    ps = set()

    def add(df, h, n):
        d = df if not name or "name" not in df.columns else df[df["name"] == name]
        for a, b in zip(pd.to_numeric(d[h], errors="coerce"), pd.to_numeric(d[n], errors="coerce")):
            if pd.notna(a) and pd.notna(b):
                ps.add((int(a), int(b)))
    for c in ("results", "robustness"):
        add(fr[c], "hits", "N_realised"); add(fr[c], "momentum_hits", "N_realised")
        add(fr[c], "min_hits_p05_realised", "N_realised")
    add(fr["lead_time"], "hits", "N"); add(fr["inflections_summary"], "caught", "scored")
    add(fr["inflections_summary"], "caught", "inflections")
    add(fr["power_table"], "min_hits_p05", "N"); add(fr["multiple_testing"], "green_found", "direction_cells_tested")
    add(fr["tsa_dependence"], "names_hit", "names_scored")
    if "tcom_caac_small_moves" in fr:
        s = fr["tcom_caac_small_moves"]
        for col in ("small_d_y", "small_d_alt", "small_either"):
            ps.add((int(s[col].sum()), len(s)))
            ps.add((int((s[col] & s.correct).sum()), int(s[col].sum())))
            ps.add((int((~s[col] & s.correct).sum()), int((~s[col]).sum())))
    if "bkng_k_rounding_check" in fr and name in (None, "BKNG"):
        b = fr["bkng_k_rounding_check"]
        ps.add((int((b.sign_differs == False).sum()), len(b)))  # noqa: E712
    return ps


def text_pool(texts: dict[str, str]) -> dict[float, str]:
    out = {}
    for p, t in texts.items():
        for m in TOKEN.finditer(SKIP.sub(" ", t)):
            out.setdefault(float(m.group(2).replace(",", "")), p)
    return out


def match(tok: str, pool, tpool) -> str:
    v = float(tok.replace(",", ""))
    d = len(tok.split(".")[1]) if "." in tok else 0
    hits = []
    for x, src in pool:
        for y in (x, 100 * x):
            if abs(round(abs(y), d) - v) < 1e-9:
                hits.append(src)
                break
    if hits:
        return "; ".join(sorted(set(hits))[:3])
    if v in tpool:
        return tpool[v] + " (text)"
    return ""


def check_doc(doc: str, text: str, name: str | None, fr: dict, tpool: dict) -> list[dict]:
    pool, ps = pool_for(fr, name), pairs_for(fr, name)
    if name:                                    # shared rows every memo may cite
        pool += pool_for({k: fr[k] for k in ("multiple_testing", "live_tsa_sensitivity", "power_table")}, None)
        ps |= pairs_for({**fr}, None) & {(1, 39)}
    rows = []
    clean = SKIP.sub(lambda m: " " * len(m.group(0)), text)
    pair_spans = []
    for m in PAIR.finditer(clean):
        h, n = int(m.group(1)), int(m.group(2))
        pair_spans.append(m.span())
        rows.append({"document": doc, "token": m.group(0), "kind": "H of N",
                     "status": "matched" if (h, n) in ps else "unmatched",
                     "source": "hits/N pair in results|robustness|lead_time|inflections_summary|power_table" if (h, n) in ps else "",
                     "context": clean[max(0, m.start() - 70):m.end() + 30].replace("\n", " ")})
    for m in TOKEN.finditer(clean):
        if any(a <= m.start() < b for a, b in pair_spans):
            continue
        src = match(m.group(2), pool, tpool)
        rows.append({"document": doc, "token": m.group(1) + m.group(2), "kind": "number",
                     "status": "matched" if src else "unmatched", "source": src,
                     "context": clean[max(0, m.start() - 70):m.end() + 30].replace("\n", " ")})
    return rows


def tracker_rows(fr: dict, tpool: dict) -> list[dict]:
    wb = openpyxl.load_workbook(REPO_ROOT / "outputs/tracker/sector_nowcast_tracker.xlsx")
    pool = pool_for(fr, None)
    rows = []
    for ws in wb:
        for row in ws.iter_rows():
            for c in row:
                v = c.value
                if isinstance(v, bool) or v is None:
                    continue
                if isinstance(v, (int, float)):
                    ok = any(abs(x - v) < 5e-7 or abs(100 * x - v) < 5e-5 for x, _ in pool)
                    src = next((s for x, s in pool if abs(x - v) < 5e-7 or abs(100 * x - v) < 5e-5), "")
                    rows.append({"document": f"tracker:{ws.title}", "token": repr(v), "kind": "cell",
                                 "status": "matched" if ok else "unmatched", "source": src, "context": c.coordinate})
                elif isinstance(v, str) and v.startswith("="):
                    rows.append({"document": f"tracker:{ws.title}", "token": v, "kind": "formula",
                                 "status": "formula (computed from matched cells)", "source": "", "context": c.coordinate})
    return rows


def main() -> None:
    fr = frames()
    tpool = text_pool({p: (REPO_ROOT / p).read_text() for p in TEXTS})
    docs = [("README.md", None), ("docs/cv_bullets.md", None), ("outputs/memos/SECTOR.md", None)]
    docs += [(f"outputs/memos/{n}.md", n) for n in NAMES]
    rows = []
    for doc, name in docs:
        rows += check_doc(doc, (REPO_ROOT / doc).read_text(), name, fr, tpool)
    rows += tracker_rows(fr, tpool)
    df = pd.DataFrame(rows)
    df.to_csv(T / "audit_traceability.csv", index=False)
    s = df.groupby(["document", "status"]).size().unstack(fill_value=0)
    print(s.to_string())
    pd.set_option("display.width", 250, "display.max_colwidth", 130, "display.max_rows", 400)
    print(df[df.status == "unmatched"][["document", "token", "context"]].to_string())


if __name__ == "__main__":
    main()
