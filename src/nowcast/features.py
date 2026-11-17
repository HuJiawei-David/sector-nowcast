"""Alt-data features alt_q and d_alt_q (CLAUDE.md model spec; hypotheses.md sections 1-3).

    alt_q(asof)   = YoY growth of the source summed over quarter q, using only observations whose
                    PUBLICATION date is on or before `asof` (quarter-to-date when asof < quarter end).
                    Daily sources: each used day d is compared with day d - 364 (same weekday);
                    alt = sum(v[d]) / sum(v[d - 364]) - 1 over the same set of days.
                    Monthly sources: months of q published by asof vs the same months one year
                    earlier; alt = sum(level) / sum(level one year earlier) - 1.
    d_alt_q(asof) = alt_q(asof) - alt_{q-1}(asof), both computed at the same asof.

Publication dates come from config/sources.yaml `publication_rule` (hard rule 2): daily = observation
date + 1 day; monthly = release date recorded from the source page (fallback month end + 45 days).
Every function that builds a feature takes an explicit `asof` and calls pit.assert_pit() on every
row it used (current period AND base period).

Checkpoints (lead time): day28 = quarter start + 27 days, day56 = quarter start + 55 days,
qend = quarter end. Variant `ewr` (Wikipedia only, pre-registered robustness): the 7 days starting on
each earnings release date of that name (8-K Item 2.02 / 6-K filing date, original releases filed
on or before asof) are removed from both years: a day pair (d, d - 364) is dropped if d or d - 364
falls inside a window.

Status values: "ok"; "not run (no data)" (hypotheses 3.10: no observation of q published by asof);
"not run (no earnings dates)" (ewr variant for periods before the first collected release date);
"not run (before alt history start)" (the base year precedes 2019-01-01, hypotheses 3.1).
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

import pandas as pd

from . import config
from .filings import quarter_end
from .pit import assert_pit, publication_date
from .quarters import Quarter, d_clean, qrange, yoy_clean

SHIFT_DAYS = 364
CHECKPOINTS = {"day28": 27, "day56": 55, "qend": None}
EWR_DAYS = 7


class DataError(ValueError):
    """Rule 9: fail loudly."""


def quarter_start(q: Quarter) -> dt.date:
    return dt.date(q.year, 3 * q.q - 2, 1)


def checkpoint_asof(q: Quarter, checkpoint: str) -> dt.date:
    off = CHECKPOINTS[checkpoint]
    return quarter_end(q) if off is None else quarter_start(q) + dt.timedelta(days=off)


@dataclass
class Series:
    """One observed series. obs: columns obs_date (date; month start for monthly), value, published."""
    series_id: str
    source: str
    frequency: str                       # daily | monthly
    rule: dict                           # publication rule from config/sources.yaml
    obs: pd.DataFrame
    meta: dict = field(default_factory=dict)

    def __post_init__(self):
        o = self.obs
        if o.obs_date.duplicated().any():
            raise DataError(f"{self.series_id}: duplicate observation dates")
        if (o.value <= 0).any():
            bad = o.loc[o.value <= 0, "obs_date"].head().tolist()
            raise DataError(f"{self.series_id}: zero/negative values on {bad}")
        expected = o.obs_date.map(lambda d: publication_date(d, self.rule) if self.frequency == "daily" else None)
        if self.frequency == "daily" and (expected != o.published).any():
            raise DataError(f"{self.series_id}: published dates differ from the daily publication rule")
        self.obs = o.sort_values("obs_date").reset_index(drop=True)
        self._by_date = self.obs.set_index("obs_date")


@dataclass
class AltValue:
    value: float | None
    status: str
    n_obs: int = 0
    first_obs: dt.date | None = None
    last_obs: dt.date | None = None
    max_published: dt.date | None = None
    used: pd.DataFrame | None = None     # every row used (current + base), with `published`


def _daily_alt(s: Series, q: Quarter, asof: dt.date, exclude: set[dt.date] | None,
               exclude_valid_from: dt.date | None) -> AltValue:
    q0, q1 = quarter_start(q), quarter_end(q)
    # Days of q whose publication date (by rule) is on or before asof: these must all be present.
    expected = [d.date() for d in pd.date_range(q0, q1, freq="D") if publication_date(d.date(), s.rule) <= asof]
    if not expected:
        return AltValue(None, "not run (no data)")
    if exclude is not None and exclude_valid_from is not None and expected[0] - dt.timedelta(days=SHIFT_DAYS) < exclude_valid_from:
        return AltValue(None, "not run (no earnings dates)")
    pairs = [(d, d - dt.timedelta(days=SHIFT_DAYS)) for d in expected]
    if pairs[0][1] < s.obs.obs_date.iloc[0]:
        return AltValue(None, "not run (before alt history start)")
    if exclude is not None:
        pairs = [(d, b) for d, b in pairs if d not in exclude and b not in exclude]
        if not pairs:
            return AltValue(None, "not run (no data)")
    need = [d for p in pairs for d in p]
    missing = [d for d in need if d not in s._by_date.index]
    if missing:
        raise DataError(f"{s.series_id}: gap in daily series, {len(missing)} day(s) needed for {q} at asof "
                        f"{asof} are missing (first {missing[0]})")
    cur = s._by_date.loc[[d for d, _ in pairs]].reset_index()
    base = s._by_date.loc[[b for _, b in pairs]].reset_index()
    used = pd.concat([cur.assign(role="current"), base.assign(role="base")], ignore_index=True)
    assert_pit(used, asof)
    val = cur.value.sum() / base.value.sum() - 1.0
    return AltValue(float(val), "ok", len(pairs), cur.obs_date.min(), cur.obs_date.max(), used.published.max(), used)


def _monthly_alt(s: Series, q: Quarter, asof: dt.date) -> AltValue:
    months = [dt.date(q.year, 3 * q.q - 2 + i, 1) for i in range(3)]
    o = s._by_date
    cur_months = [m for m in months if m in o.index and o.loc[m, "published"] <= asof]
    if not cur_months:
        return AltValue(None, "not run (no data)")
    base_months = [m.replace(year=m.year - 1) for m in cur_months]
    if base_months[0] < s.obs.obs_date.iloc[0]:
        return AltValue(None, "not run (before alt history start)")
    missing = [m for m in base_months if m not in o.index]
    if missing:
        raise DataError(f"{s.series_id}: base-year month(s) missing for {q}: {missing}")
    cur = o.loc[cur_months].reset_index()
    base = o.loc[base_months].reset_index()
    used = pd.concat([cur.assign(role="current"), base.assign(role="base")], ignore_index=True)
    assert_pit(used, asof)
    val = cur.value.sum() / base.value.sum() - 1.0
    return AltValue(float(val), "ok", len(cur_months), cur.obs_date.min(), cur.obs_date.max(), used.published.max(), used)


def alt_q(s: Series, q: Quarter, asof: dt.date, exclude: set[dt.date] | None = None,
          exclude_valid_from: dt.date | None = None) -> AltValue:
    """YoY growth of `s` over quarter q (quarter-to-date at `asof`), point-in-time by publication date."""
    if s.frequency == "daily":
        return _daily_alt(s, q, asof, exclude, exclude_valid_from)
    if s.frequency == "monthly":
        if exclude is not None:
            raise ValueError("earnings-window removal applies to daily (Wikipedia) series only")
        return _monthly_alt(s, q, asof)
    raise ValueError(s.frequency)


def earnings_windows(release_dates: list[dt.date], asof: dt.date, days: int = EWR_DAYS) -> set[dt.date]:
    """Days in the `days`-day windows starting on each release date filed on or before asof."""
    out = set()
    for r in release_dates:
        if r <= asof:
            out.update(r + dt.timedelta(days=i) for i in range(days))
    return out


def d_alt(s: Series, q: Quarter, asof: dt.date, release_dates: list[dt.date] | None = None,
          exclude_valid_from: dt.date | None = None) -> dict:
    """alt_q, alt_{q-1} and d_alt_q at one asof. release_dates given -> earnings-window variant."""
    excl = earnings_windows(release_dates, asof) if release_dates is not None else None
    a = alt_q(s, q, asof, excl, exclude_valid_from)
    p = alt_q(s, q - 1, asof, excl, exclude_valid_from)
    if a.status != "ok":
        status = a.status
    elif p.status != "ok":
        status = p.status + " (q-1)"
    else:
        status = "ok"
    return {"alt": a.value, "alt_prev": p.value,
            "d_alt": (a.value - p.value) if status == "ok" else None, "status": status,
            "n_obs": a.n_obs, "n_obs_prev": p.n_obs, "first_obs": a.first_obs, "last_obs": a.last_obs,
            "max_published": max([x for x in (a.max_published, p.max_published) if x], default=None),
            "_used": [x.used for x in (a, p) if x.used is not None]}


# --------------------------------------------------------------------------------------------
# Validations (rule 9)


def validate_series(s: Series) -> dict:
    """Daily: every calendar day from first to last observation present (no gaps), no duplicate
    dates, no zero days. Monthly: every month present, no duplicates, no zero months.
    Duplicates and zero/negative values already fail in Series.__post_init__; gaps fail here."""
    o = s.obs
    if s.frequency == "daily":
        full = pd.date_range(o.obs_date.min(), o.obs_date.max(), freq="D").date
    else:
        full = [p.to_timestamp().date() for p in pd.period_range(o.obs_date.min(), o.obs_date.max(), freq="M")]
    missing = sorted(set(full) - set(o.obs_date))
    if missing:
        raise DataError(f"{s.series_id}: {len(missing)} missing {s.frequency} observation(s), first {missing[0]}")
    return {"series_id": s.series_id, "frequency": s.frequency, "first_obs": o.obs_date.min(),
            "last_obs": o.obs_date.max(), "n_obs": len(o), "gaps": 0, "zero_or_negative": int((o.value <= 0).sum()),
            "duplicate_dates": int(o.obs_date.duplicated().sum()), "last_published": o.published.max()}


def data_run_date(series: dict[str, Series]) -> dt.date:
    """Live-call as-of: the latest date on which every daily series has all its observations published
    (min over daily series of the last observation's publication date)."""
    return min(s.obs.published.max() for s in series.values() if s.frequency == "daily")


# --------------------------------------------------------------------------------------------
# Building the series from snapshots (no network)


def backtest_snapshots() -> dict[str, str]:
    """Snapshot folders the backtest and the locked forward call use (config/pipeline.yaml)."""
    return dict(config.load_yaml("pipeline.yaml")["backtest_snapshots"])


def live_snapshots() -> dict[str, str]:
    """Snapshot folders the Session 6 live calls were computed from (config/pipeline.yaml)."""
    return dict(config.load_yaml("pipeline.yaml")["live_snapshots"])


def load_series(run_end: dt.date | None = None, snapshots: dict[str, str] | None = None) -> dict[str, Series]:
    """All configured alt series, keyed by series_id: 'tsa', 'caac', 'wikipedia:<NAME>'.
    snapshots: {raw_dir: pull_date} to read specific snapshot folders (default: latest pull of each)."""
    from . import caac, tsa, wiki
    from .rawstore import RAW_DIR

    snap = lambda raw: (RAW_DIR / raw / snapshots[raw]) if snapshots and raw in snapshots else None
    src = config.sources()
    out = {}
    t = tsa.parse(snap("tsa"))
    t = t.rename(columns={"date": "obs_date"})
    t["published"] = t.obs_date.map(lambda d: publication_date(d, src["tsa"]["publication_rule"]))
    out["tsa"] = Series("tsa", "tsa", "daily", src["tsa"]["publication_rule"], t[["obs_date", "value", "published"]])

    tv = wiki.load_title_views(snap("wikipedia_pageviews"))
    start = dt.date.fromisoformat(src["wikipedia"]["history_start"])
    end = run_end or tv.date.max()
    ws = wiki.daily_series(tv, start, end)
    for name, g in ws.groupby("name"):
        g = g.rename(columns={"date": "obs_date"})
        g["published"] = g.obs_date.map(lambda d: publication_date(d, src["wikipedia"]["publication_rule"]))
        out[f"wikipedia:{name}"] = Series(f"wikipedia:{name}", "wikipedia", "daily",
                                          src["wikipedia"]["publication_rule"], g[["obs_date", "value", "published"]].reset_index(drop=True))

    c = caac.parse(snap("caac"), fallback_lag_days=src["caac"]["publication_rule"]["fallback_lag_days_after_month_end"])
    out["caac"] = Series("caac", "caac", "monthly", src["caac"]["publication_rule"],
                         c[["obs_date", "value", "published"]], meta={"table": c})
    return out


def source_map(cos: dict | None = None) -> list[tuple[str, str, str]]:
    """(name, source, series_id) for every pre-registered cell source (combined is built later)."""
    cos = cos or config.companies()
    out = []
    for name, c in cos.items():
        vs = c["volume_source"]
        out.append((name, vs, vs))
        if c.get("wikipedia_articles"):
            out.append((name, "wikipedia", f"wikipedia:{name}"))
    return out


def build_feature_table(series: dict[str, Series], releases: pd.DataFrame, first_q: Quarter, last_q: Quarter,
                        run_date: dt.date, releases_since: dt.date, cos: dict | None = None) -> pd.DataFrame:
    """Every (name, source, variant, quarter, checkpoint) row with asof <= run_date, plus live rows.

    Live rows (checkpoint 'live', asof = run_date): 2026Q4-style current quarter for every name, and
    the previous quarter for any name whose results release for it is not filed by run_date.
    """
    cos = cos or config.companies()
    rel = releases[releases.is_amendment == 0].copy()
    rel["filed"] = pd.to_datetime(rel.filed).dt.date
    rows = []
    current_q = Quarter(run_date.year, (run_date.month - 1) // 3 + 1)
    for name, source, sid in source_map(cos):
        s = series[sid]
        # hypotheses 3.2: alt values are clean under the name's own window (TSA maps to US names only)
        excl = Quarter.parse(cos[name]["exclusion_window"][0]), Quarter.parse(cos[name]["exclusion_window"][1])
        rdates = sorted(rel.loc[rel.name == name, "filed"].tolist())
        variants = [("base", None)] + ([("ewr", rdates)] if source == "wikipedia" else [])
        reported = set(rel.loc[rel.name == name, "quarter"])
        jobs = [(q, cp, checkpoint_asof(q, cp)) for q in qrange(first_q, last_q) for cp in CHECKPOINTS]
        jobs = [j for j in jobs if j[2] <= run_date]
        jobs.append((current_q, "live", run_date))
        if str(current_q - 1) not in reported:
            jobs.append((current_q - 1, "live", run_date))
        for variant, rd in variants:
            for q, cp, asof in jobs:
                r = d_alt(s, q, asof, rd, releases_since if rd is not None else None)
                rows.append({"name": name, "source": source, "series_id": sid, "variant": variant,
                             "quarter": str(q), "checkpoint": cp, "asof": asof,
                             "alt": r["alt"], "alt_prev": r["alt_prev"], "d_alt": r["d_alt"], "status": r["status"],
                             "n_obs": r["n_obs"], "n_obs_prev": r["n_obs_prev"], "first_obs": r["first_obs"],
                             "last_obs": r["last_obs"], "max_published": r["max_published"],
                             "alt_clean": yoy_clean(q, excl), "d_alt_clean": d_clean(q, excl)})
    df = pd.DataFrame(rows)
    if df.duplicated(["name", "source", "variant", "quarter", "checkpoint"]).any():
        raise DataError("duplicate feature keys")
    bad = df[(df.status == "ok") & (pd.to_datetime(df["max_published"]).dt.date > df["asof"])]
    if len(bad):
        raise DataError(f"look-ahead in feature table: {bad.head().to_dict('records')}")
    return df
