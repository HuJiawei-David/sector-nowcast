"""Revenue versions: Q4 derivation, YTD-only 10-Qs, as-of selection with restatements, look-ahead."""
import datetime as dt
import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from nowcast import revenue as RV
from nowcast.pit import LookaheadError, assert_pit
from nowcast.quarters import Quarter

ROOT = Path(__file__).resolve().parents[1]
D = dt.date


def _fact(start, end, val, accn, filed, form="10-Q", tag="Revenues"):
    return {"tag": tag, "tag_priority": 0, "start": start, "end": end, "value": float(val), "accession": accn,
            "fy": None, "fp": None, "form": form, "filed": filed, "frame": None}


def _facts(rows):
    df = pd.DataFrame(rows)
    days = (pd.to_datetime(df["end"]) - pd.to_datetime(df["start"])).dt.days + 1
    df["period"] = days.map(lambda d: "3m" if d < 100 else "6m" if d < 200 else "9m" if d < 300 else "12m")
    return df


def _url(a):
    return f"u/{a}"


def test_q4_is_fy_minus_nine_month_ytd():
    rows = [
        _fact(D(2024, 1, 1), D(2024, 3, 31), 100, "q1", D(2024, 5, 1)),
        _fact(D(2024, 4, 1), D(2024, 6, 30), 110, "q2", D(2024, 8, 1)),
        _fact(D(2024, 1, 1), D(2024, 6, 30), 210, "q2", D(2024, 8, 1)),
        _fact(D(2024, 7, 1), D(2024, 9, 30), 120, "q3", D(2024, 11, 1)),
        _fact(D(2024, 1, 1), D(2024, 9, 30), 330, "q3", D(2024, 11, 1)),
        _fact(D(2024, 1, 1), D(2024, 12, 31), 460, "k", D(2025, 2, 10), form="10-K"),
    ]
    v = RV.versions_from_facts(_facts(rows), "X", "USD", _url)
    q4 = v[v["quarter"] == "2024Q4"]
    assert len(q4) == 1
    assert q4.iloc[0]["value"] == 130 and q4.iloc[0]["method"] == "derived_ytd"
    assert q4.iloc[0]["accession"] == "k" and q4.iloc[0]["filed"] == D(2025, 2, 10)
    assert "q3" in q4.iloc[0]["derivation"]          # 9M taken from the Q3 10-Q (latest filed before)


def test_ytd_only_10q_is_differenced():
    """A 10-Q that reports only the 6-month YTD amount yields Q2 = 6M - Q1."""
    rows = [
        _fact(D(2024, 1, 1), D(2024, 3, 31), 100, "q1", D(2024, 5, 1)),
        _fact(D(2024, 1, 1), D(2024, 6, 30), 215, "q2", D(2024, 8, 1)),       # no 3-month fact
    ]
    v = RV.versions_from_facts(_facts(rows), "X", "USD", _url)
    q2 = v[v["quarter"] == "2024Q2"].iloc[0]
    assert q2["value"] == 115 and q2["method"] == "derived_ytd"


def test_prior_year_q4_comparative_in_10k_uses_same_year_9m():
    rows = [
        _fact(D(2023, 1, 1), D(2023, 9, 30), 300, "q3_23", D(2023, 11, 1)),
        _fact(D(2023, 1, 1), D(2023, 9, 30), 300, "q3_24", D(2024, 11, 1)),   # comparative in next 10-Q
        _fact(D(2024, 1, 1), D(2024, 9, 30), 330, "q3_24", D(2024, 11, 1)),
        _fact(D(2023, 1, 1), D(2023, 12, 31), 410, "k24", D(2025, 2, 10), form="10-K"),
        _fact(D(2024, 1, 1), D(2024, 12, 31), 460, "k24", D(2025, 2, 10), form="10-K"),
    ]
    v = RV.versions_from_facts(_facts(rows), "X", "USD", _url)
    k = v[v["accession"] == "k24"].set_index("quarter")["value"]
    assert k["2024Q4"] == 130 and k["2023Q4"] == 110


def _restatement_fixture():
    return pd.DataFrame([
        {"name": "X", "quarter": "2023Q1", "value": 100.0, "filed": D(2023, 5, 1), "accession": "a",
         "method": "reported_3m", "form": "10-Q", "source_url": "u"},
        {"name": "X", "quarter": "2023Q1", "value": 110.0, "filed": D(2024, 5, 1), "accession": "b",
         "method": "reported_3m", "form": "10-Q", "source_url": "u"},       # restated comparative
        {"name": "X", "quarter": "2024Q1", "value": 121.0, "filed": D(2024, 5, 1), "accession": "b",
         "method": "reported_3m", "form": "10-Q", "source_url": "u"},
        {"name": "X", "quarter": "2022Q1", "value": 80.0, "filed": D(2023, 5, 1), "accession": "a",
         "method": "reported_3m", "form": "10-Q", "source_url": "u"},
    ])


def test_asof_picks_latest_version_filed_strictly_before():
    v = _restatement_fixture()
    get = lambda asof: RV.asof_view(v, asof).set_index("quarter")["value"].to_dict()  # noqa: E731
    assert get(D(2023, 5, 1)) == {}                                   # filed == asof is not usable
    assert get(D(2023, 5, 2)) == {"2022Q1": 80.0, "2023Q1": 100.0}
    assert get(D(2024, 5, 2))["2023Q1"] == 110.0                      # restatement visible after filing
    assert get(D(2024, 5, 1))["2023Q1"] == 100.0


def test_like_for_like_yoy_uses_one_filing():
    v = _restatement_fixture()
    first = RV.yoy_same_filing(v, "X", Quarter(2024, 1), "first")
    assert first["accession"] == "b" and first["base_value"] == 110.0       # not the original 100
    assert first["yoy_pct"] == pytest.approx(10.0)
    assert RV.first_reported(v).set_index("quarter").loc["2023Q1", "value"] == 100.0


def test_no_lookahead_on_real_data():
    """Look-ahead test (hard rule 2) on the built tables: at every checkpoint of every quarter
    2022Q1-2026Q4 the as-of views use only filings dated strictly before asof."""
    from nowcast import kpi as K
    from nowcast.filings import quarter_end
    rev = pd.read_csv(ROOT / "data" / "processed" / "revenue_pit.csv", parse_dates=["filed"])
    rev["filed"] = rev["filed"].dt.date
    vals = pd.read_csv(ROOT / "data" / "processed" / "release_values.csv", parse_dates=["filed"])
    vals["filed"] = vals["filed"].dt.date
    q = Quarter(2022, 1)
    while q <= Quarter(2026, 4):
        start = quarter_end(q - 1) + dt.timedelta(days=1)
        for asof in (start + dt.timedelta(days=27), start + dt.timedelta(days=55), quarter_end(q)):
            r = RV.asof_view(rev, asof)
            assert (r["filed"] < asof).all()
            k = K.asof_view(vals, asof)
            assert (k["filed"] < asof).all()
            for name in ("UBER", "TCOM"):
                src = rev if name == "UBER" else None
                y = (RV.yoy_same_filing(src, name, q - 1, "asof", asof=asof) if src is not None
                     else K.yoy_same_release(vals, name, q - 1, "revenue", "asof", asof=asof))
                assert y is None or y["filed"] < asof
        q = q + 1
    with pytest.raises(LookaheadError):
        assert_pit(pd.DataFrame({"published": [D(2025, 3, 31)]}), D(2025, 3, 31), strict=True)


def test_sql_asof_matches_python():
    db = ROOT / "data" / "nowcast.db"
    if not db.exists():
        pytest.skip("data/nowcast.db not built (run scripts/s2_build.py)")
    sql = (ROOT / "sql" / "revenue_asof.sql").read_text()
    rev = pd.read_csv(ROOT / "data" / "processed" / "revenue_pit.csv", parse_dates=["filed"])
    rev["filed"] = rev["filed"].dt.date
    with sqlite3.connect(db) as con:
        for asof in ("2023-06-30", "2025-03-31", "2026-11-11"):
            s = pd.read_sql_query(sql, con, params={"asof": asof})
            p = RV.asof_view(rev, D.fromisoformat(asof))
            m = s.merge(p, on=["name", "quarter"], suffixes=("_sql", "_py"))
            assert len(m) == len(s) == len(p)
            assert (m["accession_sql"] == m["accession_py"]).all()
