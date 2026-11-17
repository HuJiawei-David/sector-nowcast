"""Session 4: walk-forward evaluation (src/nowcast/evaluate.py) and the shared per-quarter call (live.py)."""
import dataclasses
import datetime as dt
import hashlib
import io
import sys

import numpy as np
import pandas as pd
import pytest

from nowcast import config, evaluate as E, features as F, live
from nowcast.quarters import Quarter
from nowcast.rawstore import REPO_ROOT

LOCKED = REPO_ROOT / "outputs/tables/live_calls_tcom_2026Q3.csv"
LOCKED_SHA = "8dbd2227c16a33a2c7607eeb83dabb2482d041b83c323c00549fe0bc9db24f84"


@pytest.fixture(scope="module")
def inp():
    return E.load_inputs()


@pytest.fixture(scope="module")
def calls(inp):
    return E.make_calls(inp)


def test_locked_tcom_2026q3_call_is_reproduced_byte_for_byte(inp):
    """The shared call (live.calls_at, 3.11 fitting pairs) reproduces the Session L forward call unchanged."""
    assert hashlib.sha256(LOCKED.read_bytes()).hexdigest() == LOCKED_SHA
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    import sL_live_tcom as S
    versions = pd.read_csv(REPO_ROOT / "data/processed/revenue_pit.csv", dtype={"accession": str})
    rows = live.live_calls(S.NAME, S.Q, S.ASOF, inp["series"], versions, inp["releases"], inp["cos"], S.ADJUSTED_NOTE)
    buf = io.StringIO()
    pd.DataFrame(rows).to_csv(buf, index=False, float_format="%.6f")
    assert buf.getvalue().encode() == LOCKED.read_bytes()


def test_call_inputs_and_outcomes_match_session_2_3_tables(calls):
    """d_alt equals the S3 feature table (qend, base); outcomes equal the S2 first-reported YoY tables."""
    feat = pd.read_csv(REPO_ROOT / "data/processed/alt_features.csv")
    feat = feat[(feat.checkpoint == "qend") & (feat.status == "ok")]
    c = calls[calls.source != "combined"].merge(feat[["name", "source", "variant", "quarter", "d_alt"]],
                                               on=["name", "source", "variant", "quarter"], suffixes=("", "_s3"))
    c = c[c.d_alt.notna()]
    assert len(c) > 500
    assert np.allclose(c.d_alt, c.d_alt_s3, atol=1e-12)
    y = pd.read_csv(REPO_ROOT / "outputs/tables/revenue_yoy.csv")
    k = pd.read_csv(REPO_ROOT / "outputs/tables/kpi_yoy.csv")
    m = calls[calls.target == "y"].merge(y[["name", "quarter", "y_pct_first_reported"]], on=["name", "quarter"])
    m = m[m.t_q_first_pct.notna()]
    assert len(m) > 300 and np.allclose(m.t_q_first_pct, m.y_pct_first_reported, atol=1e-3)
    m = calls[calls.target == "k"].merge(k[["name", "quarter", "k_pct_first_reported"]], on=["name", "quarter"])
    m = m[m.t_q_first_pct.notna()]
    assert len(m) > 300 and np.allclose(m.t_q_first_pct, m.k_pct_first_reported, atol=1e-3)


def test_tsa_call_is_identical_across_us_names(calls):
    t = calls[(calls.source == "tsa") & (calls.variant == "base")]
    assert t.groupby(["quarter", "target"]).prediction.nunique().max() == 1
    assert (E.tsa_dependence(calls).groupby("target").size() == 14).all()   # 14 quarters, each counted once


def test_every_input_was_public_before_asof(calls):
    ok = calls[calls.t_q_minus_1_asof_pct.notna()]
    # the scored outcome is reported after asof by construction
    assert (pd.to_datetime(ok.t_q_first_filed).dt.date >= ok["asof"]).all()
    for s in ("inputs_q", "inputs_q_minus_1"):
        for v, a in zip(calls[s].fillna(""), calls["asof"]):
            for part in v.split(" | "):
                if "max published" in part:
                    assert dt.date.fromisoformat(part.rsplit(" ", 1)[1]) <= a


def _poison_after(s: F.Series, asof: dt.date) -> F.Series:
    o = s.obs.copy()
    o.loc[pd.to_datetime(o.published).dt.date > asof, "value"] *= 10
    return dataclasses.replace(s, obs=o)


@pytest.mark.parametrize("name,target,q", [("LYFT", "k", Quarter(2024, 3)), ("EXPE", "y", Quarter(2025, 2)),
                                           ("TCOM", "y", Quarter(2025, 3))])
def test_backtest_call_ignores_data_published_or_filed_at_or_after_asof(inp, name, target, q):
    """Alt data published after asof x10, and KPI/revenue values filed ON asof added: the call is unchanged."""
    asof = F.checkpoint_asof(q, "qend")
    series, cos = inp["series"], inp["cos"]
    versions = pd.read_csv(REPO_ROOT / "data/processed/revenue_pit.csv", dtype={"accession": str})
    values = pd.read_csv(REPO_ROOT / "data/processed/release_values.csv", dtype={"accession": str})
    base = live.calls_at(name, q, asof, series, live.TargetData(versions, values), cos, target)
    poisoned = {k: _poison_after(s, asof) for k, s in series.items()}
    fv = versions[versions.name == name].tail(3).assign(filed=str(asof), accession="0000000000-99-999999", value=1.0)
    fk = values[values.name == name].tail(3).assign(filed=str(asof), accession="0000000000-99-999999", value=1.0)
    after = live.calls_at(name, q, asof, poisoned,
                          live.TargetData(pd.concat([versions, fv]), pd.concat([values, fk])), cos, target)
    cols = ["source", "d_alt", "call", "t_q_minus_1_pct", "beta_pp_per_unit_d_alt", "n_pairs", "yhat_pct", "combined_detail"]
    pd.testing.assert_frame_equal(pd.DataFrame(base)[cols], pd.DataFrame(after)[cols])


def test_same_sample_rule_and_misses():
    sub = pd.DataFrame({
        "quarter": ["2024Q1", "2024Q2", "2024Q3", "2024Q4"],
        "prediction": ["accelerate", "no call", "decelerate", "accelerate"],
        "correct": [True, False, True, None],                      # 2024Q4: model not run
        "momentum_correct": [None, True, False, True],             # 2024Q1: momentum not run
        "actual": ["accelerate", "decelerate", "decelerate", "flat"]})
    m = E.score_direction(sub)
    assert m["N_realised"] == 2 and m["quarters_scored"] == "2024Q2,2024Q3"
    assert m["hits"] == 1 and m["momentum_hits"] == 1 and m["n_excluded_same_sample"] == 2
    assert not m["beats_momentum"] and not m["beats_50"]
    assert E._correct("no call", "accelerate") is False and E._correct("accelerate", "flat") is False


def test_family_is_39_cells_and_bh_is_monotone_in_p(calls, inp):
    res = E.results(calls, inp["cos"])
    fam = res[res.family_member]
    assert len(fam) == 39 and fam.bh_q_binom.notna().all()
    f = fam.sort_values("binom_p_one_sided")
    assert (np.diff(f.bh_q_binom.to_numpy()) >= -1e-12).all() and (f.bh_q_binom >= f.binom_p_one_sided - 1e-12).all()
    head = res[res.analysis == "headline"]
    # rule 5: every (name, source, target, model) cell present, incl. not-run ones
    assert len(head) == len(E.cell_list(inp["cos"])) * 2
    assert head[head.N_realised == 0].status.str.startswith("not run").all()


def test_predictions_parsed_from_hypotheses():
    p = E.predictions_from_hypotheses()
    exp = {k for k, v in p.items() if v == "signal expected"}
    assert exp == {("EXPE", "tsa", "y"), ("EXPE", "combined", "y"), ("LYFT", "tsa", "k"), ("LYFT", "combined", "k"),
                   ("TCOM", "caac", "y"), ("TCOM", "combined", "y")}
    assert p[("TCOM", "hkia", "y")] == "signal NOT expected" and len(p) == 40
