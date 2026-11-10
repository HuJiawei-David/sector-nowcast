"""Point-in-time rules (hard rule 2).

publication_date() maps an observation to the date it became public; assert_pit() is the guard
every feature builder must call on the rows it used, so a feature can never see data published
after `asof`.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd


class LookaheadError(AssertionError):
    """Raised when a feature uses data published after its as-of date."""


def month_end(d: dt.date) -> dt.date:
    nxt = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return nxt - dt.timedelta(days=1)


def publication_date(obs_date: dt.date, rule: dict, recorded_release: dt.date | None = None) -> dt.date:
    """rule comes from config/sources.yaml `publication_rule`."""
    kind = rule["type"]
    if kind == "daily_lag":
        return obs_date + dt.timedelta(days=int(rule["lag_days"]))
    if kind == "monthly_release":
        if recorded_release is not None:
            return recorded_release
        return month_end(obs_date) + dt.timedelta(days=int(rule["fallback_lag_days_after_month_end"]))
    raise ValueError(f"unknown publication rule: {kind}")


def assert_pit(used: pd.DataFrame, asof: dt.date, pub_col: str = "published", strict: bool = False) -> None:
    """Fail loudly if any row used by a feature was published after `asof`.

    Alt-data: published on or before asof is allowed (strict=False).
    Revenue/KPI facts: `filed` must be strictly before asof (strict=True).
    """
    if pub_col not in used.columns:
        raise LookaheadError(f"feature input lacks a '{pub_col}' column; cannot verify point-in-time")
    pub = pd.to_datetime(used[pub_col]).dt.date
    bad = used[pub >= asof] if strict else used[pub > asof]
    if len(bad):
        raise LookaheadError(f"{len(bad)} row(s) published after as-of {asof}: first {bad.iloc[0].to_dict()}")
