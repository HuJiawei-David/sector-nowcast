"""KPI (and release-revenue) values read from earnings releases: dedupe, as-of view, like-for-like YoY.

A value is identified by (name, metric, kind, quarter, accession). Two extractors reading the same
number from one release must agree within rounding; the most precise reading is kept. Values for
the same quarter from different releases are different VERSIONS (e.g. a restated prior-year
comparative) and are all kept.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd

from .pit import assert_pit
from .quarters import Quarter

KEY = ["name", "metric", "kind", "quarter", "accession"]


class ConflictError(ValueError):
    pass


def dedupe(values: pd.DataFrame) -> pd.DataFrame:
    out = []
    for key, g in values.groupby(KEY, sort=False):
        g = g.sort_values("precision")
        best = g.iloc[0].to_dict()
        tol = g["precision"].max() / 2 + 1e-9
        if (g["value"] - best["value"]).abs().max() > tol:
            raise ConflictError(f"{key}: extractors disagree: "
                                f"{list(zip(g['extractor'], g['value']))}")
        best["extractors"] = ";".join(sorted(set(g["extractor"])))
        out.append(best)
    df = pd.DataFrame(out)
    if df.duplicated(KEY).any():
        raise ConflictError("duplicate keys after dedupe")
    return df.sort_values(["name", "metric", "kind", "quarter", "filed"]).reset_index(drop=True)


def asof_view(values: pd.DataFrame, asof: dt.date, metric: str = "kpi", kind: str = "value") -> pd.DataFrame:
    """Per (name, quarter): the value from the latest release filed strictly before `asof`."""
    v = values[(values["metric"] == metric) & (values["kind"] == kind)]
    v = v[pd.to_datetime(v["filed"]).dt.date < asof]
    v = v.sort_values(["name", "quarter", "filed", "accession"])
    out = v.groupby(["name", "quarter"], as_index=False).tail(1)
    assert_pit(out.rename(columns={"filed": "published"}), asof, strict=True)
    return out.reset_index(drop=True)


def yoy_same_release(values: pd.DataFrame, name: str, q: Quarter, metric: str = "kpi",
                     choice: str = "first", asof: dt.date | None = None) -> dict | None:
    """Like-for-like YoY (hypotheses.md 3.11) from ONE release.

    choice='first': first release that reports q (realised outcome); 'asof': latest release filed
    before `asof` that reports q. Uses value(q)/value(q-4) from one release that carries both; if no
    such release exists, the YoY % a release states for q; else None (not run: no like-for-like base).
    """
    v = values[(values["name"] == name) & (values["metric"] == metric)]
    cur = v[(v["quarter"] == str(q)) & (v["kind"] == "value")]
    if choice == "asof":
        cur = cur[pd.to_datetime(cur["filed"]).dt.date < asof]
    if cur.empty:
        return None
    cur = cur.sort_values(["filed", "accession"])
    order = cur.iloc[::-1] if choice == "asof" else cur
    # Prefer the release (first / latest) that carries BOTH q and q-4, so the two levels are on one
    # basis; a release that shows q only as an older comparative has no q-4 and is skipped.
    for _, c in order.iterrows():
        rel = v[v["accession"] == c["accession"]]
        base = rel[(rel["quarter"] == str(q - 4)) & (rel["kind"] == "value")]
        if len(base):
            b = base.iloc[0]
            return {**_head(c, name, q, metric), "base_value": b["value"], "base_precision": b["precision"],
                    "yoy_pct": 100.0 * (c["value"] / b["value"] - 1.0), "yoy_basis": "levels in same release"}
    for _, c in order.iterrows():
        rel = v[v["accession"] == c["accession"]]
        st = rel[(rel["quarter"] == str(q)) & (rel["kind"] == "stated_yoy_pct")]
        if len(st):
            s = st.sort_values("precision").iloc[0]
            return {**_head(c, name, q, metric), "base_value": None, "base_precision": None,
                    "yoy_pct": s["value"], "yoy_basis": "stated Y/Y % in same release"}
    return None


def _head(c, name, q, metric) -> dict:
    return {"name": name, "quarter": str(q), "metric": metric, "value": c["value"], "precision": c["precision"],
            "filed": c["filed"], "accession": c["accession"], "release_quarter": c["release_quarter"],
            "source_url": c["source_url"]}
