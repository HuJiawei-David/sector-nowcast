"""Rule 9 validations and the known-answer reconciliation output."""
import datetime as dt
from pathlib import Path

import pandas as pd
import pytest
import yaml

from nowcast import revenue as RV
from nowcast import validate as V
from nowcast.quarters import Quarter

ROOT = Path(__file__).resolve().parents[1]


def test_missing_quarter_raises():
    with pytest.raises(V.ValidationError):
        V.no_missing_quarters(["2024Q1", "2024Q3"], Quarter(2024, 1), Quarter(2024, 3), "x")
    V.no_missing_quarters(["2024Q1", "2024Q2"], Quarter(2024, 1), Quarter(2024, 2), "x")


def test_duplicates_raise():
    df = pd.DataFrame({"a": [1, 1], "b": [2, 2]})
    with pytest.raises(V.ValidationError):
        V.no_duplicates(df, ["a", "b"], "x")


def test_fy_sum_tolerance():
    latest = pd.DataFrame({"name": "X", "quarter": ["2024Q1", "2024Q2", "2024Q3", "2024Q4"],
                           "value": [100.0, 100.0, 100.0, 100.0]})
    ann = pd.DataFrame({"end": [dt.date(2024, 12, 31)], "filed": [dt.date(2025, 2, 1)], "value": [401.0],
                        "accession": ["k"]})
    V.fy_sums(latest, ann, "X", [2024], 0.005)                       # 0.25% passes
    ann["value"] = 410.0
    with pytest.raises(V.ValidationError):
        V.fy_sums(latest, ann, "X", [2024], 0.005)                   # 2.4% fails


def test_non_calendar_quarter_raises():
    df = pd.DataFrame([{"start": dt.date(2024, 2, 1), "end": dt.date(2024, 4, 30), "period": "3m",
                        "accession": "a"}])
    with pytest.raises(RV.DataError):
        RV.check_calendar(df, "X", Quarter(2024, 1))


def _rec():
    p = ROOT / "outputs" / "tables" / "reconciliation.csv"
    if not p.exists():
        pytest.skip("reconciliation.csv not built (run scripts/s2_build.py)")
    return pd.read_csv(p)


def test_every_reconciliation_mismatch_has_a_status():
    rec = _rec()
    assert len(rec) > 0
    allowed = rec["status"].str.match(r"^(match( \(bug fixed: [A-Z0-9, ]+\))?|definitional: .+)$")
    assert allowed.all(), rec.loc[~allowed, ["name", "quarter", "check", "status"]]
    out_of_tol = (rec["diff"].abs() > rec["tolerance"] + 1e-9) | rec["diff"].isna()
    assert rec.loc[out_of_tol, "status"].str.startswith("definitional: ").all()


def test_bug_log_entries_are_complete():
    notes = yaml.safe_load((ROOT / "config" / "reconciliation_notes.yaml").read_text())
    for b in notes["bugs_fixed"]:
        assert {"id", "description", "before", "after", "affected"} <= set(b), b.get("id")
    for d in notes.get("definitional", []):
        assert d.get("reason") and d.get("evidence"), d
