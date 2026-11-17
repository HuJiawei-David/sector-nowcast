"""Session 6: live calls, guidance benchmark, base-period sensitivity, tracker (src/nowcast/livecalls.py)."""
import datetime as dt
import re

import pandas as pd
import pytest

from nowcast import features as F, livecalls as LC
from nowcast.quarters import Quarter
from nowcast.rawstore import REPO_ROOT

T = REPO_ROOT / "outputs/tables"
norm = lambda s: re.sub(r"\s+", " ", s).strip()


def test_every_guidance_and_event_quote_is_in_its_snapshot():
    g = LC.guidance_config()
    n = 0
    for e in g["guidance"] + g["base_period_events"]:
        if "snapshot" not in e:
            continue
        text = LC.snapshot_text(e["snapshot"])
        for k in ("quote", "prev_quote", "base_quote", "quote2"):
            if k in e:
                assert norm(e[k]) in text, (e.get("name", e.get("id")), k)
                n += 1
        if "start_quote" in e:                      # Session 8: official source for the start of an event window
            assert norm(e["start_quote"]) in LC.snapshot_text(e["start_snapshot"]), e["id"]
            n += 1
    assert n >= 16


def test_event_windows_are_sourced_not_from_a_brief():
    """Rule 6 (coach review 2026-11-17): every base-period event date must come from a saved official document."""
    for e in LC.guidance_config()["base_period_events"]:
        blob = " ".join(str(v) for v in e.values()).lower()
        assert "brief" not in blob, e["id"]
    lapse = next(e for e in LC.guidance_config()["base_period_events"] if e["id"] == "us_federal_lapse_2025")
    assert lapse["window"] == ["2025-10-01", "2025-11-12"]
    assert "October 1, 2025, through November 12, 2025" in lapse["start_quote"]


def test_public_hashes_of_the_timestamped_files():
    """The three SHA-256 values posted publicly (gist) must never change."""
    import hashlib
    want = {"docs/hypotheses.md": "28056437cdfd7c3baeb512aeb764adbc25457a0d4562ab0647eee400db35fb4d",
            "outputs/tables/live_calls_tcom_2026Q3.csv": "8dbd2227c16a33a2c7607eeb83dabb2482d041b83c323c00549fe0bc9db24f84",
            "outputs/tables/live_calls.csv": "875b9a34f69033d64acd1057db635c890c202b749fe5fd5ce4d7a392310c08fd"}
    for path, sha in want.items():
        assert hashlib.sha256((REPO_ROOT / path).read_bytes()).hexdigest() == sha, path


def test_live_calls_read_pinned_snapshots():
    assert F.live_snapshots() == {"tsa": "2026-11-17", "wikipedia_pageviews": "2026-11-17", "caac": "2026-11-17"}
    assert "F.load_series(snapshots=F.live_snapshots())" in (REPO_ROOT / "scripts/s6_live.py").read_text()


@pytest.mark.parametrize("call,prev,label", [("accelerate", 10.0, "above guidance"), ("decelerate", 10.0, "in line"),
                                             ("accelerate", 1.0, "in line"), ("decelerate", 1.0, "below guidance"),
                                             ("insufficient data", 1.0, "n/a (call: insufficient data)")])
def test_guidance_label_rule(call, prev, label):
    cfg = {"guidance": [{"name": "X", "quarter": "2026Q4", "metric": "Revenue", "target": "y", "applies_to_targets": ["y"],
                         "basis": "reported", "low_yoy_pct": 4, "high_yoy_pct": 6, "quote": "q", "source_url": "u"}]}
    g = LC.guidance_for("X", Quarter(2026, 4), "y", call, 5.6, prev, cfg)
    assert g["guidance_mid_pct"] == 5.0 and g["guidance_label"] == label
    if call in ("accelerate", "decelerate"):
        assert g["yhat_vs_guidance"].startswith("in line")          # |5.6 - 5.0| <= 1.0 pp
    assert LC.guidance_for("Y", Quarter(2026, 4), "y", call, None, prev, cfg)["guidance_label"] == "no guidance"


def test_level_guidance_implied_yoy():
    cfg = {"guidance": [{"name": "D", "quarter": "2026Q4", "metric": "GOV", "target": None, "applies_to_targets": ["y"],
                         "basis": "reported", "low_level": 110, "high_level": 130, "base_level": 100,
                         "prev_level": 150, "prev_base_level": 100, "quote": "q", "source_url": "u"}]}
    g = LC.guidance_for("D", Quarter(2026, 4), "y", "accelerate", 99.0, 0.0, cfg)
    assert g["guidance_mid_pct"] == pytest.approx(20.0) and g["guidance_prev_yoy_pct"] == pytest.approx(50.0)
    assert g["guided_direction"] == "decelerate" and g["guidance_label"] == "above guidance" and g["yhat_vs_guidance"] == ""


def test_locked_tcom_rows_carried_unchanged():
    lk = pd.read_csv(LC.LOCKED)
    lv = pd.read_csv(T / "live_calls.csv")
    b = lv[lv.live_call.str.startswith("(b)")].reset_index(drop=True)
    assert len(b) == len(lk) == 3
    for c_lv, c_lk in [("source", "source"), ("call", "call"), ("asof", "asof"), ("combined_detail", "combined_detail"),
                       ("inputs_q", "inputs_q"), ("guidance_label", "guidance_label")]:
        assert (b[c_lv].fillna("").astype(str) == lk[c_lk].fillna("").astype(str)).all(), c_lv
    for c_lv, c_lk in [("d_alt", "d_alt"), ("yhat_pct", "yhat_pct"), ("t_q_minus_1_pct", "y_q_minus_1_pct")]:
        pd.testing.assert_series_equal(b[c_lv], lk[c_lk], check_names=False)


def test_live_calls_use_only_data_published_by_asof():
    lv = pd.read_csv(T / "live_calls.csv")
    a = lv[lv.live_call.str.startswith("(a)")]
    assert a["asof"].nunique() == 1
    asof = dt.date.fromisoformat(a["asof"].iloc[0])
    for v in pd.concat([a.inputs_q, a.inputs_q_minus_1]).fillna(""):
        for part in v.split(" | "):
            if "max published" in part:
                assert dt.date.fromisoformat(part.rsplit(" ", 1)[1]) <= asof
    # a source without published data inside the quarter is "insufficient data", never a guess
    nodata = a[a.status.str.startswith("not run (no data")]
    assert (nodata.call == "insufficient data").all()


def test_tsa_sensitivity_drops_pairs_by_base_day():
    s = F.load_series(snapshots=F.backtest_snapshots())["tsa"]
    q, asof = Quarter(2025, 4), dt.date(2025, 12, 1)
    ev = [{"id": "w", "window": ["2024-10-10", "2024-10-19"]}]
    out = LC.tsa_sensitivity(s, q, asof, ev)
    assert out.n_days.iloc[0] - out.n_days.iloc[1] == 10
    assert out.alt_q_minus_1.nunique() == 1


def test_tracker_workbook():
    from openpyxl import load_workbook
    wb = load_workbook(REPO_ROOT / "outputs/tracker/sector_nowcast_tracker.xlsx")
    assert wb.sheetnames == ["Tracker", "Data relevancy", "Lead time", "Backtest", "Notes"]
    res = pd.read_csv(T / "results.csv")
    n_green = int(res[res.model == "direction"].green.astype(bool).sum())
    ws = wb["Data relevancy"]
    fills = [c.fill.fgColor.rgb for row in ws.iter_rows(min_row=2) for c in row[2:] if c.value is not None
             and c.fill is not None and c.fill.fill_type == "solid"]
    assert set(f[-6:] for f in fills) <= {"C6EFCE", "D9D9D9"}
    assert sum(f.endswith("C6EFCE") for f in fills) == n_green
    t = wb["Tracker"]
    assert any(isinstance(c.value, str) and c.value.startswith("=IF(") for row in t.iter_rows(min_row=2) for c in row)
    assert t.max_row >= 9                                      # 7 names (2026Q4) + TCOM 2026Q3 locked
