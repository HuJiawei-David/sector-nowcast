"""Rule 9 validations (fail loudly, never patch).

- missing quarters inside a name's required range (first required quarter through its last
  REPORTED quarter; a quarter not yet reported is not missing)
- Q1+Q2+Q3+Q4 != FY (tolerance from config/pipeline.yaml, 0.5%)
- duplicate keys
- non-calendar fiscal quarters (checked when XBRL facts are read: revenue.check_calendar)
"""
from __future__ import annotations

import pandas as pd

from .quarters import Quarter, qrange


class ValidationError(ValueError):
    pass


def no_duplicates(df: pd.DataFrame, key: list[str], what: str) -> None:
    d = df[df.duplicated(key, keep=False)]
    if len(d):
        raise ValidationError(f"{what}: duplicate keys {key}:\n{d[key].head(10)}")


def no_missing_quarters(quarters, first: Quarter, last: Quarter, what: str) -> None:
    have = {Quarter.parse(q) if isinstance(q, str) else q for q in quarters}
    missing = [str(q) for q in qrange(first, last) if q not in have]
    if missing:
        raise ValidationError(f"{what}: missing quarters {missing} inside required range {first}..{last}")


def releases_complete(rel: pd.DataFrame, name: str, first: Quarter) -> Quarter:
    """Exactly one original (non-amendment) results release per quarter from `first` to the last one."""
    r = rel[(rel["name"] == name) & (rel["is_amendment"] == 0)]
    r = r[r["quarter"].map(Quarter.parse) >= first]
    if r.empty:
        raise ValidationError(f"{name}: no earnings releases from {first}")
    no_duplicates(r, ["name", "quarter"], f"{name} earnings releases (one original per quarter)")
    last = max(r["quarter"].map(Quarter.parse))
    no_missing_quarters(r["quarter"], first, last, f"{name} earnings releases")
    return last


def fy_sums(latest: pd.DataFrame, annual: pd.DataFrame, name: str, years: list[int], tol: float) -> list[dict]:
    """Sum of the latest quarterly versions vs the latest FY figure, per year. Raises beyond `tol`."""
    out = []
    for y in years:
        qs = latest[(latest["name"] == name) & latest["quarter"].str.startswith(str(y))]
        fy = annual[annual["end"].map(lambda d: d.year) == y]
        if len(qs) != 4 or fy.empty:
            continue
        fyv = fy.sort_values("filed").iloc[-1]
        s = qs["value"].sum()
        rel = abs(s - fyv["value"]) / abs(fyv["value"])
        row = {"name": name, "year": y, "sum_q": s, "fy": fyv["value"], "fy_accession": fyv["accession"],
               "rel_diff": rel}
        out.append(row)
        if rel > tol:
            raise ValidationError(f"{name} {y}: Q1+Q2+Q3+Q4 = {s:.1f} vs FY {fyv['value']:.1f} "
                                  f"({rel:.3%} > {tol:.1%})")
    return out


def consistent_across_releases(values: pd.DataFrame, known: list[dict]) -> pd.DataFrame:
    """Every number for one (name, metric, quarter) must agree across releases within rounding,
    unless the difference is a documented restatement (config/reconciliation_notes.yaml
    `restatements`). Both versions are always kept; this only makes a silent change impossible."""
    ok = {(k["name"], k["metric"], k["quarter"]) for k in known}
    x = values[values["kind"] == "value"]
    bad = []
    for key, d in x.groupby(["name", "metric", "quarter"]):
        if d["value"].max() - d["value"].min() > d["precision"].max() / 2 + 1e-9 and key not in ok:
            bad.append((key, d[["value", "release_quarter"]].values.tolist()))
    if bad:
        raise ValidationError(f"values differ across releases without a documented restatement: {bad[:5]}")
    return x
