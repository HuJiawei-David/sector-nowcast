"""Known-answer reconciliation: our numbers vs numbers the company itself states.

Checks per (name, quarter):
  revenue_yoy        ours: like-for-like revenue YoY (first filing reporting q; US = XBRL 10-Q/10-K,
                     TCOM = 6-K release) vs the reported Y/Y % stated in the release for q.
  kpi_yoy            ours: KPI YoY from levels in the first release reporting q vs the KPI Y/Y %
                     stated in that release.
  q4_revenue_derived ours: Q4 = FY - 9M YTD (US: XBRL 10-K minus 10-Q; TCOM: 20-F FY minus the
                     Q1-Q3 releases) vs the Q4 figure in the Q4 earnings release.
  revenue_level      ours: first XBRL version of revenue for q vs the figure in the release for q (US).
  kpi_restatement    KPI for q in its own release vs the prior-year comparative in the q+4 release.

Tolerance: half of the company's stated precision + 0.1 pp for percentages (e.g. "16%" -> 0.6 pp);
for levels, half of the stated precision + 0.1% of the value.

Status: "match"; "match (bug fixed: <ids>)" when a logged pipeline bug affected the check;
"definitional: <reason>" (automatic rounding rule, or an entry in config/reconciliation_notes.yaml);
otherwise "UNCLASSIFIED" (tests fail). Data values are never edited to make a check pass.
"""
from __future__ import annotations

import pandas as pd

from . import kpi as K
from . import revenue as RV
from .quarters import Quarter, qrange

PCT_EXTRA = 0.1        # pp
LEVEL_EXTRA = 0.001    # share of value


def _stated(values: pd.DataFrame, name: str, metric: str, q: Quarter, accession: str | None = None):
    s = values[(values["name"] == name) & (values["metric"] == metric) & (values["kind"] == "stated_yoy_pct")
               & (values["quarter"] == str(q))]
    if accession is not None:
        s = s[s["accession"] == accession]
    else:
        s = s[s["release_quarter"] == str(q)]
    s = s[~s["form"].str.endswith("/A")]
    if s.empty:
        return None
    return s.sort_values(["precision", "filed"]).iloc[0]


def _release_value(values, name, metric, q, release_q=None, role=None):
    v = values[(values["name"] == name) & (values["metric"] == metric) & (values["kind"] == "value")
               & (values["quarter"] == str(q)) & (values["release_quarter"] == str(release_q or q))]
    v = v[~v["form"].str.endswith("/A")]
    if role:
        v = v[v["role"] == role]
    if v.empty:
        return None
    return v.sort_values("filed").iloc[0]


def rounding_interval(cur, cur_prec, base, base_prec):
    """YoY % range consistent with levels disclosed to the given precision."""
    hc, hb = cur_prec / 2, base_prec / 2
    lo = 100 * ((cur - hc) / (base + hb) - 1)
    hi = 100 * ((cur + hc) / (base - hb) - 1)
    return lo, hi


def run(names: list[str], cos: dict, rev_versions: pd.DataFrame, values: pd.DataFrame, annual: dict,
        first: Quarter, last: dict, notes: dict) -> pd.DataFrame:
    rows = []

    def add(name, q, check, ours, company, basis, tol, url, auto_reason=None):
        diff = None if ours is None or company is None else ours - company
        rows.append({"name": name, "quarter": str(q), "check": check, "ours": ours, "company": company,
                     "company_basis": basis, "diff": diff, "tolerance": tol, "auto_reason": auto_reason,
                     "source_url": url})

    for name in names:
        co = cos[name]
        lq = last[name]
        for q in qrange(first, lq):
            # ---- revenue YoY
            if co["region"] == "US":
                ours = RV.yoy_same_filing(rev_versions, name, q, "first")
            else:
                ours = K.yoy_same_release(values, name, q, metric="revenue", choice="first")
            st = _stated(values, name, "revenue", q)
            if ours is not None and st is not None:
                tol = st["precision"] / 2 + PCT_EXTRA
                auto = None
                if co["region"] != "US" and ours.get("base_value"):
                    lo, hi = rounding_interval(ours["value"], ours["precision"], ours["base_value"],
                                               ours["base_precision"])
                    auto = _rounding_reason(st, lo, hi)
                add(name, q, "revenue_yoy", ours["yoy_pct"], st["value"],
                    f"reported Y/Y % stated in the {q} release ({_prec_txt(st['precision'])} precision)",
                    tol, st["source_url"], auto)
            # ---- KPI YoY
            if co.get("kpi"):
                ok = K.yoy_same_release(values, name, q, metric="kpi", choice="first")
                if ok is not None and ok["yoy_basis"] == "levels in same release":
                    st = _stated(values, name, "kpi", q, accession=ok["accession"])
                    if st is not None:
                        lo, hi = rounding_interval(ok["value"], ok["precision"], ok["base_value"],
                                                   ok["base_precision"])
                        add(name, q, "kpi_yoy", ok["yoy_pct"], st["value"],
                            f"KPI Y/Y % stated in the {ok['release_quarter']} release "
                            f"({_prec_txt(st['precision'])} precision)",
                            st["precision"] / 2 + PCT_EXTRA, st["source_url"], _rounding_reason(st, lo, hi))
            # ---- KPI restatement: own release vs prior-year comparative in the q+4 release
            if co.get("kpi") and q + 4 <= lq:
                a = _release_value(values, name, "kpi", q, release_q=q, role="current")
                b = _release_value(values, name, "kpi", q, release_q=q + 4, role="prior_year_comparative")
                if a is not None and b is not None:
                    add(name, q, "kpi_restatement", a["value"], b["value"],
                        f"prior-year comparative for {q} in the {q + 4} release",
                        max(a["precision"], b["precision"]) / 2 + 1e-9, b["source_url"])
            # ---- revenue level (US): XBRL first version vs release figure
            rv = _release_value(values, name, "revenue", q, release_q=q, role="current")
            if co["region"] == "US":
                fr = RV.first_reported(rev_versions[rev_versions["name"] == name])
                x = fr[fr["quarter"] == str(q)]
                if rv is not None and len(x):
                    xv = x.iloc[0]
                    tol = rv["precision"] / 2 + LEVEL_EXTRA * abs(rv["value"])
                    chk = "q4_revenue_derived" if q.q == 4 else "revenue_level"
                    basis = ("Q4 revenue in the Q4 release" if q.q == 4 else f"revenue in the {q} release")
                    add(name, q, chk, xv["value"], rv["value"],
                        f"{basis} ({_prec_txt(rv['precision'])} {co['revenue']['currency']} m precision); "
                        f"ours = {xv['method']} {xv['accession']}", tol, rv["source_url"])
            elif q.q == 4 and rv is not None:
                fy = annual.get(name)
                fyq = fy[fy["end"].map(lambda d: d.year) == q.year] if fy is not None else None
                firsts = RV.first_reported(rev_versions[rev_versions["name"] == name])
                q13 = firsts[firsts["quarter"].isin([f"{q.year}Q{i}" for i in (1, 2, 3)])]
                if fyq is not None and len(fyq) and len(q13) == 3:
                    f0 = fyq.sort_values("filed").iloc[0]
                    ours_q4 = f0["value"] - q13["value"].sum()
                    add(name, q, "q4_revenue_derived", ours_q4, rv["value"],
                        f"Q4 net revenue in the Q4 release; ours = 20-F FY ({f0['accession']}) minus "
                        f"Q1-Q3 from the 6-K releases", rv["precision"] / 2 + LEVEL_EXTRA * abs(rv["value"]),
                        rv["source_url"])

    df = pd.DataFrame(rows)
    df["status"] = [_status(r, notes) for r in df.itertuples()]
    return df.drop(columns=["auto_reason"])


def _prec_txt(p):
    return f"{p:g}"


def _rounding_reason(st, lo, hi):
    s, h = st["value"], st["precision"] / 2
    if s + h >= lo and s - h <= hi:
        return (f"rounding: the disclosed levels are rounded, so they imply a Y/Y between {lo:.2f}% and "
                f"{hi:.2f}%; the company's {s:g}% (computed on unrounded figures) lies inside that range")
    return None


def _status(r, notes: dict) -> str:
    key = (r.name, r.quarter, r.check)
    bug_ids = [b["id"] for b in notes.get("bugs_fixed", [])
               if any((a["name"], a["quarter"], a["check"]) == key for a in b.get("affected", []))]
    if r.diff is not None and abs(r.diff) <= r.tolerance + 1e-9:
        return "match" + (f" (bug fixed: {', '.join(bug_ids)})" if bug_ids else "")
    if isinstance(r.auto_reason, str) and r.auto_reason:
        return "definitional: " + r.auto_reason
    for d in notes.get("definitional", []):
        if (d["name"], d["quarter"], d["check"]) == key:
            return "definitional: " + d["reason"]
    return "UNCLASSIFIED"
