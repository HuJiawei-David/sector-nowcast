"""Point-in-time guard (hard rule 2). Feature builders arriving in later sessions must call
nowcast.pit.assert_pit on their inputs; this test pins the guard's behaviour."""
import datetime as dt

import pandas as pd
import pytest

from nowcast.pit import LookaheadError, assert_pit, publication_date

DAILY = {"type": "daily_lag", "lag_days": 1}
MONTHLY = {"type": "monthly_release", "release_date": "recorded_from_source_page",
           "fallback_lag_days_after_month_end": 45}


def test_publication_rules():
    assert publication_date(dt.date(2025, 3, 31), DAILY) == dt.date(2025, 4, 1)
    assert publication_date(dt.date(2025, 2, 1), MONTHLY) == dt.date(2025, 4, 14)
    assert publication_date(dt.date(2025, 2, 1), MONTHLY, dt.date(2025, 3, 20)) == dt.date(2025, 3, 20)


def test_guard_rejects_lookahead():
    asof = dt.date(2025, 3, 31)
    obs = pd.date_range("2025-03-25", "2025-03-31").date
    ok = pd.DataFrame({"obs": obs, "published": [publication_date(d, DAILY) for d in obs]})
    assert_pit(ok[ok.published <= asof], asof)          # last usable day is 2025-03-30
    with pytest.raises(LookaheadError):
        assert_pit(ok, asof)                            # 2025-03-31 obs is published 2025-04-01


def test_guard_strict_for_filed_facts():
    asof = dt.date(2025, 3, 31)
    facts = pd.DataFrame({"published": [dt.date(2025, 3, 31)]})
    with pytest.raises(LookaheadError):
        assert_pit(facts, asof, strict=True)            # filed must be strictly before asof
