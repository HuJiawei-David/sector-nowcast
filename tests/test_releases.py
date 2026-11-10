"""Release parsing engine: periods per layout, numbers, titles, qualifier rejection, dedupe."""
import datetime as dt

import pandas as pd
import pytest

from nowcast import kpi as K
from nowcast import releases as R
from nowcast import validate as V
from nowcast.quarters import Quarter

RQ = Quarter(2026, 3)


def test_parse_num():
    assert R.parse_num("(1,234.5)") == (-1234.5, 1)
    assert R.parse_num("$22.9B") == (22.9, 1)
    assert R.parse_num("—") == (0.0, 0)
    assert R.numbers("133.6M 155.0M 411.1M") == [(133.6, 1), (155.0, 1), (411.1, 1)]


def test_layouts():
    assert R.periods_for({"kind": "relative", "offsets": [-4, -1, 0]}, None, 4, RQ) == \
        [Quarter(2025, 3), Quarter(2026, 2), Quarter(2026, 3), "nonquarter"]
    assert R.periods_for({"kind": "explicit"}, "3Q25 4Q25 1Q26 FY 2025", 4, RQ) == \
        [Quarter(2025, 3), Quarter(2025, 4), Quarter(2026, 1), "nonquarter"]
    assert R.periods_for({"kind": "explicit"}, "Sept. 30, 2026 June 30, 2026 Mar.31, 2026", 3, RQ) == \
        [Quarter(2026, 3), Quarter(2026, 2), Quarter(2026, 1)]
    assert R.periods_for({"kind": "years_same_quarter"}, "September 30 2025 2026 2025 2026", 2, RQ) == \
        [Quarter(2025, 3), Quarter(2026, 3)]
    assert R.periods_for({"kind": "consecutive", "count_from_header": True}, "2025 2026 Q1 Q2 Q3 Q4 Q1 Q2 Q3",
                         8, RQ)[:7] == [Quarter(2025, i) for i in (1, 2, 3, 4)] + [Quarter(2026, i) for i in (1, 2, 3)]
    with pytest.raises(R.ExtractionError):        # Q tokens that do not end at the release quarter
        R.periods_for({"kind": "consecutive", "count_from_header": True}, "Q1 Q2 Q3 Q4", 4, RQ)


def test_year_groups_handles_skipped_year():
    hdr = "2019 2021 2022 Q1 Q2 Q3 Q4 Q1 Q2 Q3 Q4 Q1"
    per = R.periods_for({"kind": "year_groups"}, hdr, 9, Quarter(2022, 1))
    assert per[:4] == [Quarter(2019, i) for i in (1, 2, 3, 4)]
    assert per[4:] == [Quarter(2021, i) for i in (1, 2, 3, 4)] + [Quarter(2022, 1)]


def test_title_quarter():
    assert R._title_quarter("Booking Holdings Reports Financial Results for 4 th Quarter and Full-Year 2021") \
        == Quarter(2021, 4)
    assert R._title_quarter("in the period from Q1 2020 through Q3 2022 ... Third Quarter 2022 Key") \
        == Quarter(2022, 3)


def _release(text_q=Quarter(2025, 1)):
    return R.Release("X", 1, "acc", "8-K", dt.date(2025, 5, 1), "d.htm", text_q, "u", None)


def test_qualified_sentence_is_rejected():
    spec = {"extractors": [{
        "id": "s", "metric": "kpi", "reject_groups": ["qual"],
        "regex": r"(?P<qual>(?:Excluding|In) [A-Z][A-Za-z ]{1,30}, )?Nights grew (?P<yoy>\d+)% year-over-year"}]}
    text = "Excluding North America, Nights grew 11% year-over-year. Overall, Nights grew 8% year-over-year."
    rows, _ = R.extract(_release(), spec, text=text)
    assert [r["value"] for r in rows] == [8.0]


def test_dedupe_keeps_most_precise_and_rejects_conflicts():
    base = {"name": "X", "metric": "kpi", "kind": "stated_yoy_pct", "quarter": "2025Q1", "accession": "a",
            "filed": dt.date(2025, 5, 1), "release_quarter": "2025Q1", "source_url": "u", "role": "current"}
    ok = pd.DataFrame([{**base, "value": 100.0, "precision": 1.0, "extractor": "sentence"},
                       {**base, "value": 99.7, "precision": 0.1, "extractor": "table"}])
    d = K.dedupe(ok)
    assert len(d) == 1 and d.iloc[0]["value"] == 99.7
    bad = pd.DataFrame([{**base, "value": 11.0, "precision": 1.0, "extractor": "sentence"},
                        {**base, "value": 7.9, "precision": 0.1, "extractor": "table"}])
    with pytest.raises(K.ConflictError):
        K.dedupe(bad)


def test_cross_release_change_fails_unless_documented():
    rows = [{"name": "X", "metric": "kpi", "kind": "value", "quarter": "2024Q1", "value": v, "precision": 0.1,
             "release_quarter": rq} for v, rq in ((10.0, "2024Q1"), (10.5, "2025Q1"))]
    df = pd.DataFrame(rows)
    with pytest.raises(V.ValidationError):
        V.consistent_across_releases(df, [])
    V.consistent_across_releases(df, [{"name": "X", "metric": "kpi", "quarter": "2024Q1"}])


def test_like_for_like_prefers_release_with_both_quarters():
    def r(q, v, acc, filed):
        return {"name": "X", "metric": "kpi", "kind": "value", "quarter": q, "value": v, "precision": 0.1,
                "filed": filed, "accession": acc, "release_quarter": "", "source_url": "u"}
    vals = pd.DataFrame([r("2025Q1", 110.0, "r1", dt.date(2025, 5, 1)), r("2024Q1", 100.0, "r1", dt.date(2025, 5, 1)),
                         r("2025Q1", 111.0, "r2", dt.date(2026, 5, 1))])          # q only as comparative
    latest = K.yoy_same_release(vals, "X", Quarter(2025, 1), choice="asof", asof=dt.date(2026, 6, 1))
    assert latest["accession"] == "r1" and latest["yoy_pct"] == pytest.approx(10.0)
