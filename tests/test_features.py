"""Session 3: alt-data features (point-in-time by PUBLICATION date, 364-day alignment, former
Wikipedia titles, earnings-window variant, rule-9 validations, source parsers)."""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from nowcast import caac, features as F, tsa, wiki
from nowcast.pit import LookaheadError, assert_pit, publication_date
from nowcast.quarters import Quarter
from nowcast.rawstore import RAW_DIR

DAILY = {"type": "daily_lag", "lag_days": 1}
MONTHLY = {"type": "monthly_release", "release_date": "recorded_from_source_page",
           "fallback_lag_days_after_month_end": 45}


def daily_series(start="2019-01-01", end="2026-12-31", f=None, sid="x"):
    days = pd.date_range(start, end, freq="D").date
    vals = [f(d) if f else 100 + (d - dt.date(2019, 1, 1)).days for d in days]
    obs = pd.DataFrame({"obs_date": days, "value": vals, "published": [publication_date(d, DAILY) for d in days]})
    return F.Series(sid, "test", "daily", DAILY, obs)


def monthly_series(published: dict, values: dict | None = None):
    months = sorted(published)
    obs = pd.DataFrame({"obs_date": months, "value": [values[m] if values else 1000.0 for m in months],
                        "published": [published[m] for m in months]})
    return F.Series("m", "test", "monthly", MONTHLY, obs)


# ---------------------------------------------------------------- point-in-time (hard rule 2)

def test_caac_month_observed_before_asof_but_published_after_is_excluded():
    # 2025-05 observed before asof 2025-06-30 but published 2025-07-02 -> excluded.
    pub = {}
    for y in (2024, 2025):
        for m in range(1, 13):
            pub[dt.date(y, m, 1)] = dt.date(y, m, 1) + dt.timedelta(days=50)
    pub[dt.date(2025, 4, 1)] = dt.date(2025, 5, 20)
    pub[dt.date(2025, 5, 1)] = dt.date(2025, 7, 2)
    pub[dt.date(2025, 6, 1)] = dt.date(2025, 7, 20)
    vals = {m: (2000.0 if m == dt.date(2025, 5, 1) else 1000.0) for m in pub}
    s = monthly_series(pub, vals)
    a = F.alt_q(s, Quarter(2025, 2), dt.date(2025, 6, 30))
    assert a.status == "ok" and a.n_obs == 1 and a.last_obs == dt.date(2025, 4, 1)
    assert a.value == pytest.approx(0.0)              # the 2000 in May would have made it +50%
    assert (a.used.published <= dt.date(2025, 6, 30)).all()
    # the day it is published it enters
    b = F.alt_q(s, Quarter(2025, 2), dt.date(2025, 7, 2))
    assert b.n_obs == 2 and b.value == pytest.approx(0.5)


def test_caac_no_month_published_is_not_run():
    pub = {dt.date(y, m, 1): dt.date(y, m, 1) + dt.timedelta(days=50) for y in (2024, 2025) for m in range(1, 13)}
    s = monthly_series(pub)
    a = F.alt_q(s, Quarter(2025, 1), F.checkpoint_asof(Quarter(2025, 1), "day28"))
    assert a.status == "not run (no data)" and a.value is None


def test_daily_asof_cutoff_by_publication_date():
    s = daily_series()
    q = Quarter(2025, 1)
    a = F.alt_q(s, q, dt.date(2025, 3, 31))          # 2025-03-31 obs is published 2025-04-01
    assert a.last_obs == dt.date(2025, 3, 30) and a.n_obs == 89
    assert (a.used.published <= dt.date(2025, 3, 31)).all()
    b = F.alt_q(s, q, dt.date(2025, 4, 1))
    assert b.last_obs == dt.date(2025, 3, 31) and b.n_obs == 90


def test_feature_is_invariant_to_data_published_after_asof():
    """Look-ahead test: deleting every observation published after asof must not change any feature."""
    s = daily_series(f=lambda d: 1000 + 5 * d.weekday() + d.toordinal() % 17)
    rng = np.random.default_rng(0)
    for q in [Quarter(2023, 2), Quarter(2024, 4), Quarter(2026, 1)]:
        for cp in F.CHECKPOINTS:
            asof = F.checkpoint_asof(q, cp)
            full = F.d_alt(s, q, asof)
            trunc_obs = s.obs[s.obs.published <= asof]
            t = F.Series("t", "test", "daily", DAILY, trunc_obs.copy())
            cut = F.d_alt(t, q, asof)
            assert full["d_alt"] == pytest.approx(cut["d_alt"]) and full["n_obs"] == cut["n_obs"]
            for u in full["_used"]:
                assert_pit(u, asof)
    # a planted look-ahead row must be caught by the guard
    with pytest.raises(LookaheadError):
        assert_pit(pd.DataFrame({"published": [dt.date(2025, 4, 1)]}), dt.date(2025, 3, 31))
    assert rng is not None


def test_real_feature_table_has_no_lookahead():
    path = RAW_DIR.parent / "processed" / "alt_features.csv"
    if not path.exists():
        pytest.skip("data/processed/alt_features.csv not built")
    ft = pd.read_csv(path, parse_dates=["asof", "max_published", "last_obs"])
    ok = ft[ft.status == "ok"]
    assert len(ok) > 1000
    assert (ok.max_published <= ok["asof"]).all()
    # daily sources: the last observation used is at least one day before asof
    d = ok[ok.source.isin(["tsa", "wikipedia"])]
    assert (d.last_obs < d["asof"]).all()


def test_real_series_truncation_invariance():
    """On the real snapshots: recomputing features from data cut at asof gives identical values."""
    if not (RAW_DIR / "tsa").exists() or not (RAW_DIR / "caac").exists():
        pytest.skip("alt snapshots not present")
    series = F.load_series()
    for sid in ["tsa", "caac", "wikipedia:EXPE"]:
        s = series[sid]
        for q in [Quarter(2023, 2), Quarter(2024, 3), Quarter(2026, 3)]:
            for cp in F.CHECKPOINTS:
                asof = F.checkpoint_asof(q, cp)
                full = F.d_alt(s, q, asof)
                t = F.Series("t", s.source, s.frequency, s.rule, s.obs[s.obs.published <= asof].copy())
                cut = F.d_alt(t, q, asof)
                assert full["status"] == cut["status"]
                if full["status"] == "ok":
                    assert full["d_alt"] == pytest.approx(cut["d_alt"])


# ---------------------------------------------------------------- 364-day alignment

def test_364_day_alignment_is_weekday_aligned():
    # A pure day-of-week pattern has zero YoY growth under a 364-day shift (not under 365).
    s = daily_series(f=lambda d: [10, 20, 30, 40, 50, 300, 500][d.weekday()])
    for q in [Quarter(2024, 1), Quarter(2024, 3), Quarter(2025, 4)]:
        a = F.alt_q(s, q, F.checkpoint_asof(q, "qend"))
        assert a.value == pytest.approx(0.0, abs=1e-12)
        cur = a.used[a.used.role == "current"].obs_date.tolist()
        base = a.used[a.used.role == "base"].obs_date.tolist()
        assert all((c - b).days == 364 and c.weekday() == b.weekday() for c, b in zip(cur, base))


def test_d_alt_uses_same_asof_for_both_quarters():
    s = daily_series(f=lambda d: 100 if d.year < 2025 else (110 if d < dt.date(2025, 4, 1) else 130))
    r = F.d_alt(s, Quarter(2025, 2), dt.date(2025, 6, 30))
    assert r["alt_prev"] == pytest.approx(0.10) and r["alt"] == pytest.approx(0.30)
    assert r["d_alt"] == pytest.approx(0.20)


def test_checkpoint_dates():
    q = Quarter(2025, 1)
    assert F.checkpoint_asof(q, "day28") == dt.date(2025, 1, 28)
    assert F.checkpoint_asof(q, "day56") == dt.date(2025, 2, 25)
    assert F.checkpoint_asof(q, "qend") == dt.date(2025, 3, 31)


def test_before_history_start_is_not_run():
    s = daily_series()
    a = F.alt_q(s, Quarter(2019, 4), dt.date(2019, 12, 31))
    assert a.status == "not run (before alt history start)"


# ---------------------------------------------------------------- Wikipedia earnings-window variant

def test_earnings_window_removed_from_both_years():
    rel = [dt.date(2025, 2, 10), dt.date(2024, 2, 20)]
    excl = F.earnings_windows(rel, dt.date(2025, 3, 31))
    assert len(excl) == 14 and dt.date(2025, 2, 16) in excl and dt.date(2025, 2, 17) not in excl
    spike25 = {dt.date(2025, 2, 10) + dt.timedelta(days=i) for i in range(7)}
    spike24 = {dt.date(2024, 2, 20) + dt.timedelta(days=i) for i in range(7)}
    s = daily_series(f=lambda d: 20_000 if d in spike25 else (10_000 if d in spike24 else 100))
    q = Quarter(2025, 1)
    a = F.alt_q(s, q, dt.date(2025, 3, 31), excl, dt.date(2022, 1, 1))
    assert a.value == pytest.approx(0.0)
    used = set(a.used.obs_date)
    assert not used & excl
    # pairs whose base day (d - 364) falls in the 2024 window are dropped too
    assert dt.date(2025, 2, 18) not in used and (dt.date(2025, 2, 18) - dt.timedelta(days=364)) in excl
    base = F.alt_q(s, q, dt.date(2025, 3, 31))
    assert base.value != pytest.approx(0.0)


def test_earnings_windows_only_releases_filed_by_asof():
    excl = F.earnings_windows([dt.date(2025, 4, 1)], dt.date(2025, 3, 31))
    assert excl == set()


# ---------------------------------------------------------------- Wikipedia titles

def _tv(rows):
    return pd.DataFrame(rows, columns=["name", "title", "date", "views"])


def test_former_titles_are_summed():
    cos = {"TCOM": {"wikipedia_articles": [{"current_title": "Trip.com Group", "titles_since_2019": ["Ctrip", "Trip.com Group"]},
                                           {"current_title": "Trip.com", "titles_since_2019": ["Trip.com"]}]}}
    d0, d1, d2 = dt.date(2019, 11, 6), dt.date(2019, 11, 7), dt.date(2019, 11, 8)
    tv = _tv([("TCOM", "Ctrip", d0, 50), ("TCOM", "Ctrip", d1, 5), ("TCOM", "Ctrip", d2, 3),
              ("TCOM", "Trip.com Group", d1, 40), ("TCOM", "Trip.com Group", d2, 45),
              ("TCOM", "Trip.com", d0, 7), ("TCOM", "Trip.com", d1, 8), ("TCOM", "Trip.com", d2, 9)])
    out = wiki.daily_series(tv, d0, d2, cos).set_index("date")
    assert out.loc[d0, "value"] == 57              # move target did not exist yet: counts 0
    assert out.loc[d1, "value"] == 53 and out.loc[d2, "value"] == 57
    assert out.loc[d0, "n_titles_with_data"] == 2


def test_missing_configured_title_or_interior_gap_fails():
    cos = {"X": {"wikipedia_articles": [{"current_title": "A", "titles_since_2019": ["A", "B"]}]}}
    d = [dt.date(2020, 1, i) for i in (1, 2, 3)]
    with pytest.raises(wiki.DataError):
        wiki.daily_series(_tv([("X", "A", x, 1) for x in d]), d[0], d[-1], cos)
    tv = _tv([("X", "A", x, 1) for x in d] + [("X", "B", d[0], 1), ("X", "B", d[2], 1)])
    with pytest.raises(wiki.DataError):
        wiki.daily_series(tv, d[0], d[-1], cos)


def test_titles_by_name_reads_config_including_former_titles():
    t = wiki.titles_by_name()
    assert t["TCOM"] == ["Ctrip", "Trip.com Group", "Trip.com"]
    assert t["BKNG"] == ["Booking Holdings", "Booking.com"]


# ---------------------------------------------------------------- rule 9 validations

def test_gap_zero_and_duplicate_days_fail():
    s = daily_series(end="2020-12-31")
    with pytest.raises(F.DataError):
        F.validate_series(F.Series("g", "t", "daily", DAILY, s.obs.drop(index=400).reset_index(drop=True)))
    with pytest.raises(F.DataError):
        F.alt_q(F.Series("g", "t", "daily", DAILY, s.obs.drop(index=500).reset_index(drop=True)),
                Quarter(2020, 2), dt.date(2020, 6, 30))
    z = s.obs.copy(); z.loc[10, "value"] = 0
    with pytest.raises(F.DataError):
        F.Series("z", "t", "daily", DAILY, z)
    dup = pd.concat([s.obs, s.obs.iloc[[5]]], ignore_index=True)
    with pytest.raises(F.DataError):
        F.Series("d", "t", "daily", DAILY, dup)
    bad_pub = s.obs.copy(); bad_pub.loc[3, "published"] = bad_pub.loc[3, "obs_date"]
    with pytest.raises(F.DataError):
        F.Series("p", "t", "daily", DAILY, bad_pub)


def test_monthly_gap_fails():
    pub = {dt.date(2024, m, 1): dt.date(2024, m, 25) for m in range(1, 13) if m != 6}
    with pytest.raises(F.DataError):
        F.validate_series(monthly_series(pub))


# ---------------------------------------------------------------- parsers

def test_tsa_parse_page_and_conflicts(tmp_path):
    html = b"""<table><thead><tr><th>Date</th><th>Numbers</th></tr></thead><tbody>
    <tr><td>1/2/2019</td><td>2,424,225</td></tr><tr><td>1/1/2019</td><td>2,201,765</td></tr></tbody></table>"""
    df = tsa.parse_page(html, "2019")
    assert df.set_index("date").loc[dt.date(2019, 1, 1), "value"] == 2201765
    (tmp_path / "passenger-volumes_2019.html").write_bytes(html)
    (tmp_path / "passenger-volumes_current.html").write_bytes(html.replace(b"2,201,765", b"2,201,766"))
    with pytest.raises(tsa.DataError):
        tsa.parse(tmp_path)


def test_caac_parsers():
    text = "一、运输完成情况\n旅客运输量 万人 6430.0 2.6 59318.6 2.0\n  国内航线 万人 5755.5 2.4"
    assert caac.parse_pax(text) == (6430.0, 2.6)
    html = "<div>发文日期：</div><div>2026-10-20</div>".encode()
    assert caac.page_release_date(html) == dt.date(2026, 10, 20)
    rows, n = caac.parse_listing("<table><tr><td><a href='u'>中国民航2019年4月份主要运输生产指标统计</a></td>"
                                 "<td>2019年06月20日</td></tr></table><div>共25页</div>".encode())
    assert rows[0]["year"] == 2019 and rows[0]["month"] == 4 and rows[0]["listing_date"] == dt.date(2019, 6, 20) and n == 25


def test_real_caac_snapshot_complete():
    if not (RAW_DIR / "caac").exists():
        pytest.skip("no CAAC snapshot")
    df = caac.parse()
    cov = caac.coverage(df)
    assert cov["missing_months"] == [] and cov["unparsed_months"] == [] and cov["fallback_date_months"] == []
    assert (pd.to_datetime(df.published).dt.date > df.obs_date.map(lambda d: d)).all()
