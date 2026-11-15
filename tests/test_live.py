"""Session L: live calls (src/nowcast/live.py). Point-in-time cut-off at `asof` (hard rule 2) on the real
Session 3 snapshots, plus unit tests of the combined source and the magnitude fallback."""
import dataclasses
import datetime as dt

import pandas as pd
import pytest

from nowcast import config, features as F, live
from nowcast.quarters import Quarter

ASOF = dt.date(2026, 11, 10)
Q = Quarter(2026, 3)


@pytest.fixture(scope="module")
def inputs():
    series = F.load_series()
    versions = pd.read_csv("data/processed/revenue_pit.csv", dtype={"accession": str})
    releases = pd.read_csv("data/processed/earnings_releases.csv", dtype={"accession": str})
    return series, versions, releases, config.companies()


def _key(rows):
    cols = ["source", "alt_q", "alt_q_minus_1", "d_alt", "call", "y_q_minus_1_pct", "beta_pp_per_unit_d_alt",
            "n_pairs", "yhat_pct", "magnitude_status", "inputs_q", "inputs_q_minus_1", "combined_detail"]
    return pd.DataFrame(rows)[cols]


def _poison_after(s: F.Series, asof: dt.date) -> F.Series:
    """Multiply every observation published after asof by 10 (a look-ahead would change the call)."""
    o = s.obs.copy()
    o.loc[pd.to_datetime(o.published).dt.date > asof, "value"] *= 10
    return dataclasses.replace(s, obs=o)


@pytest.mark.parametrize("asof", [dt.date(2026, 10, 19), ASOF])
def test_live_call_ignores_everything_published_or_filed_at_or_after_asof(inputs, asof):
    """Alt data published after asof poisoned x10; fake revenue filings dated ON asof added.
    At 2026-10-19 the poison hits real Q3/Q4 observations (CAAC Sep, Wikipedia Oct-Nov); at the live
    asof the snapshots end on it, so that case tests the revenue cut-off (filed strictly before asof)."""
    ASOF_ = asof
    series, versions, releases, cos = inputs
    base = live.live_calls("TCOM", Q, ASOF_, series, versions, releases, cos)
    poisoned = {k: _poison_after(s, ASOF_) for k, s in series.items()}
    n_poisoned = sum(int((pd.to_datetime(s.obs.published).dt.date > ASOF_).sum()) for s in series.values())
    assert (n_poisoned > 0) == (asof < ASOF)
    # a fake 2026Q3 release (and a restated 2026Q2) filed ON asof: revenue facts must be filed BEFORE asof
    fake = versions[(versions.name == "TCOM") & (versions.quarter == "2026Q2")].iloc[[0]].copy()
    fake = pd.concat([fake.assign(quarter="2026Q3", value=99999.0), fake.assign(value=1.0),
                      versions[(versions.name == "TCOM") & (versions.quarter == "2025Q3")].iloc[[0]].assign(value=1.0)])
    fake = fake.assign(filed=str(ASOF_), accession="0000000000-26-999999")
    v2 = pd.concat([versions, fake], ignore_index=True)
    r2 = pd.concat([releases, pd.DataFrame([{"name": "TCOM", "quarter": "2026Q3", "filed": str(ASOF_),
                                              "accession": "0000000000-26-999999", "form": "6-K", "is_amendment": 0,
                                              "document": "fake.htm", "source_url": "fake"}])], ignore_index=True)
    after = live.live_calls("TCOM", Q, ASOF_, poisoned, v2, r2, cos)
    pd.testing.assert_frame_equal(_key(base), _key(after))
    # and the rows themselves never report inputs published after asof
    for r in base:
        for part in r["inputs_q"].split(" | ") + r["inputs_q_minus_1"].split(" | "):
            if "max published" in part:
                assert dt.date.fromisoformat(part.rsplit(" ", 1)[1]) <= ASOF_


def test_caac_september_enters_only_on_its_publication_day(inputs):
    series, versions, releases, cos = inputs
    t = series["caac"].meta["table"]
    pub_sep = t.loc[t.month == "2026-09", "published"].iloc[0]
    before = {r["source"]: r for r in live.live_calls("TCOM", Q, pub_sep - dt.timedelta(days=1), series, versions, releases, cos)}
    on = {r["source"]: r for r in live.live_calls("TCOM", Q, pub_sep, series, versions, releases, cos)}
    assert before["caac"]["inputs_q"].startswith("q: 2026-07,2026-08 vs")
    assert on["caac"]["inputs_q"].startswith("q: 2026-07,2026-08,2026-09 vs")
    assert before["caac"]["d_alt"] != on["caac"]["d_alt"]


def test_training_pairs_need_filings_before_asof(inputs):
    series, versions, releases, cos = inputs
    ex = (Quarter(2020, 1), Quarter(2022, 4))
    # the 2026Q2 release was filed 2026-09-16: the 2026Q2 pair exists from 2026-09-17, not on 2026-09-16
    on = live.training_pairs("TCOM", series["caac"], versions, ex, dt.date(2026, 9, 16), Q)
    after = live.training_pairs("TCOM", series["caac"], versions, ex, dt.date(2026, 9, 17), Q)
    assert "2026Q2" not in set(on.quarter) and "2026Q2" in set(after.quarter)
    assert (pd.to_datetime(after.y_filed).dt.date < dt.date(2026, 9, 17)).all()


# ---------------------------------------------------------------- unit tests


def test_direction_zero_is_a_miss():
    assert live.direction(0.1) == "accelerate" and live.direction(-0.1) == "decelerate"
    assert live.direction(0.0).startswith("no call")


def test_combined_needs_four_clean_values_per_source():
    h3 = pd.DataFrame({"quarter": ["a", "b", "c"], "d_alt": [0.1, -0.1, 0.2]})
    h4 = pd.DataFrame({"quarter": ["a", "b", "c", "d"], "d_alt": [0.1, -0.1, 0.2, 0.0]})
    assert live.combined_direction({"x": 0.1, "y": 0.1}, {"x": h4, "y": h3})["status"].startswith("not run")
    c = live.combined_direction({"x": 0.3, "y": -0.1}, {"x": h4, "y": h4.assign(d_alt=h4.d_alt * 10)})
    sd = h4.d_alt.std(ddof=1)
    assert c["status"] == "ok" and c["z_sum"] == pytest.approx(0.3 / sd - 0.1 / (10 * sd))


def test_magnitude_name_then_pooled_then_not_run():
    pairs = lambda n: pd.DataFrame({"quarter": [f"2024Q{i % 4 + 1}" for i in range(n)],
                                    "d_alt": [0.1 * (i + 1) for i in range(n)], "d_y": [2.0 * (i + 1) for i in range(n)]})
    m = live.magnitude(pairs(4), lambda: pairs(0), 10.0, 0.05)
    assert m["beta_basis"] == "name" and m["beta"] == pytest.approx(20.0) and m["yhat"] == pytest.approx(11.0)
    m = live.magnitude(pairs(3), lambda: pairs(6), 10.0, 0.05)
    assert m["beta_basis"].startswith("pooled") and m["n_pairs"] == 6
    m = live.magnitude(pairs(3), lambda: pairs(3), 10.0, 0.05)
    assert m["status"].startswith("not run") and m["yhat"] is None
