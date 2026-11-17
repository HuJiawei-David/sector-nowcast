"""Session 5: placebos, GREEN rule, inflections, lead time (src/nowcast/placebo.py)."""
import datetime as dt

import numpy as np
import pandas as pd
import pytest

from nowcast import features as F, placebo as P
from nowcast.quarters import Quarter
from nowcast.rawstore import REPO_ROOT

T = REPO_ROOT / "outputs/tables"


def test_shuffle_is_seeded_and_preserves_call_shares():
    d = np.array([0.3, -0.1, 0.2, -0.4, 0.5, 0.1, -0.2])
    act = np.array([1, -1, 1, -1, 1, 1, -1])
    a, b = P.shuffle_direction(d, act), P.shuffle_direction(d, act)
    assert np.array_equal(a["_sims"], b["_sims"]) and a["placebo_hits_obs"] == 7
    # a perfect cell beats nearly every permutation; percentile is strict (ties count against the cell)
    assert a["placebo_percentile"] == pytest.approx(100 * (a["_sims"] < 7).mean())
    assert a["placebo_p"] == pytest.approx((1 + (a["_sims"] >= 7).sum()) / 1001)
    # all-accelerate calls: every permutation is identical -> percentile 0 (no information beyond the share)
    c = P.shuffle_direction(np.ones(7), act)
    assert c["placebo_percentile"] == 0.0 and c["placebo_p"] == 1.0


def test_zero_call_and_flat_actual_are_misses():
    assert P.hits_of(np.array([0, 1, -1]), np.array([0, 0, -1])) == 1


def test_green_requires_both_baselines_and_placebo_95():
    r = pd.read_csv(T / "results.csv")
    d = r[r.model == "direction"]
    exp = d.beats_both_baselines.fillna(False).astype(bool) & (d.placebo_percentile >= 95)
    assert (d.green.astype(bool) == exp).all()
    assert not r[r.model == "magnitude"].green.astype(bool).any()


def test_placebo_hits_match_results_and_wrong_company_marks():
    r = pd.read_csv(T / "results.csv")
    d = r[(r.model == "direction") & (r.N_realised > 0)]
    assert d.placebo_percentile.notna().all()
    assert d[d.source == "tsa"].wrong_company.str.startswith("n/a: same series").all()
    assert d[d.source == "caac"].wrong_company.str.startswith("n/a: single name").all()
    w = d[d.source == "wikipedia"]
    assert w.wrong_company_percentile.notna().all()
    wc = pd.read_csv(T / "placebo_wrong_company.csv")
    assert (wc.name != wc.series_of).all()
    assert (wc[wc.analysis == "headline"].groupby(["name", "target"]).size() == 6).all()
    mt = pd.read_csv(T / "multiple_testing.csv").iloc[0]
    assert mt.direction_cells_tested == 39 and mt.expected_to_pass_by_chance == pytest.approx(1.95)
    assert mt.green_found == int(r[r.family_member].green.sum())


def test_inflection_definition():
    calls = pd.DataFrame({
        "name": "X", "target": "y", "variant": "base", "checkpoint": "qend", "source": "tsa",
        "quarter": ["2023Q1", "2023Q2", "2023Q3", "2023Q4"], "in_headline": [False, True, True, True],
        "d_t_actual_pp": [1.0, 2.0, -1.0, 3.0], "actual": ["accelerate", "accelerate", "decelerate", "accelerate"],
        "prediction": ["accelerate", "decelerate", "decelerate", "decelerate"], "correct": [True, False, True, False],
        "momentum_prediction": ["x"] * 4, "momentum_correct": [False] * 4})
    inf = P.inflections(calls)
    assert list(inf.quarter) == ["2023Q3", "2023Q4"] and list(inf.caught) == [True, False]
    s = P.inflection_summary(inf).iloc[0]
    assert (s.inflections, s.caught, s.missed) == (2, 1, 1)


def test_lead_time_checkpoints_and_no_data_rule():
    assert F.checkpoint_asof(Quarter(2025, 1), "day28") == dt.date(2025, 1, 28)
    assert F.checkpoint_asof(Quarter(2025, 1), "day56") == dt.date(2025, 2, 25)
    lt = pd.read_csv(T / "lead_time.csv")
    caac28 = lt[(lt.source == "caac") & (lt.checkpoint == "day28")].iloc[0]
    assert caac28.N == 0 and caac28.n_not_run == 9 and "no data" in caac28.not_run_reasons
    q = lt[lt.checkpoint == "qend"].set_index(["name", "source", "target"])
    r = pd.read_csv(T / "results.csv").set_index(["name", "source", "target"])
    r = r[r.model == "direction"]
    # quarter-end lead-time hits are the headline hits before the momentum same-sample rule (LYFT k: 12 vs 14)
    for k, x in q.iterrows():
        if k in r.index and not (k[0] == "LYFT" and k[2] == "k"):
            assert x.hits == r.loc[k, "hits"] and x.N == r.loc[k, "N_realised"]
    assert (lt[lt.checkpoint == "qend"].median_weeks_to_release > 0).all()
