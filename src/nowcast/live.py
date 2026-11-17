"""Live calls (CLAUDE.md "LIVE CALLS"; hypotheses.md sections 1, 3.5, 3.10-3.12).

One function, `live_calls(name, q, asof, ...)`, returns the direction call, the magnitude estimate
and the guidance label for every source of `name` (its volume source, Wikipedia, combined) at an
explicit `asof`. Sessions 4/6 reuse the building blocks (`direction`, `combined_direction`,
`training_pairs`, `beta_origin`, `magnitude`) for the backtest.

Point-in-time (hard rule 2):
- alt data: only observations PUBLISHED on or before asof (features.d_alt -> pit.assert_pit);
- revenue facts: only filings FILED strictly before asof (assert_pit(strict=True) on every row used).

Definitions fixed by the spec and made explicit here:
- d_alt_q (call value) = alt_q - alt_{q-1}, both at the call's asof (features.d_alt).
- Combined: sign(sum_s d_alt_s / std_s). std_s = sample std (ddof=1) of source s's clean d_alt values
  for every clean quarter up to and including q: quarters before q enter with their quarter-end
  checkpoint value (the value the backtest call used, computed at that quarter's end, which is
  before asof), q enters with the call value. Fewer than 4 clean values -> "not run".
- Magnitude: yhat_q = y_{q-1} + beta * d_alt_q (y in %, d_alt as a fraction, so beta is pp per unit
  of d_alt). beta = OLS through the origin on clean (d_y, d_alt) pairs available before asof:
  d_y_p = y_p - y_{p-1}, each the like-for-like YoY from the LATEST filing (or release) filed
  strictly before asof that reports it with its q-4 base (hypotheses 3.11; Session 4 convention ii);
  a pair exists only if both values exist at asof, and d_alt_p is p's quarter-end checkpoint value
  (as known then). < 4 pairs for the name -> pooled pairs of all names with the same source and
  target; < 4 pooled -> "not run". y_{q-1} for the forecast = latest filing before asof (3.11).
  The scored outcome (evaluate.py) uses the FIRST-reported value instead.
- Targets: y = revenue YoY (revenue_pit versions), k = KPI YoY (release values), via TargetData.
- Combined magnitude: the spec defines the combined source as a direction call only -> "not run".
"""
from __future__ import annotations

import datetime as dt
import re

import numpy as np
import pandas as pd

from . import config, features as F
from .filings import html_to_text
from .pit import assert_pit
from .quarters import Quarter, d_clean
from .rawstore import REPO_ROOT, find_snapshot, read_snapshot
from .kpi import yoy_same_release
from .revenue import yoy_same_filing

MIN_VALUES = 4
COMBINED_NOT_RUN_MAG = "not run (spec defines the combined source as a direction call only; no magnitude model)"
GUIDANCE_PATTERNS = [r"business outlook", r"\boutlook\b", r"\bguidance\b", r"\bexpects?\b[^.]{0,120}\b(revenue|growth)\b"]
_BOILERPLATE = re.compile(r"Safe Harbor Statement.*?(?=About Non-GAAP|$)", re.S)


def direction(d: float | None) -> str:
    """Prediction = sign(d_alt); d_alt == 0 is no call (scored as a miss)."""
    if d is None or (isinstance(d, float) and np.isnan(d)):
        return "not run"
    if d > 0:
        return "accelerate"
    if d < 0:
        return "decelerate"
    return "no call (d_alt == 0, scored as a miss)"


def _excl(co: dict) -> tuple[Quarter, Quarter]:
    w = co["exclusion_window"]
    return Quarter.parse(w[0]), Quarter.parse(w[1])


def dalt_history(s: F.Series, q: Quarter, asof: dt.date, exclusion: tuple[Quarter, Quarter],
                 call_value: float, first_q: Quarter = Quarter(2019, 1), dalt_fn=None) -> pd.DataFrame:
    """Clean d_alt values up to and including q: quarter-end values before q (each at its own quarter
    end, which must be on or before asof), then the call value for q."""
    dalt_fn = dalt_fn or F.d_alt
    rows = []
    p = first_q
    while p < q:
        a = F.checkpoint_asof(p, "qend")
        if d_clean(p, exclusion) and a <= asof:
            r = dalt_fn(s, p, a)
            if r["status"] == "ok":
                for u in r["_used"]:
                    assert_pit(u, asof)
                rows.append({"quarter": str(p), "d_alt": r["d_alt"], "asof": a})
        p = p + 1
    if d_clean(q, exclusion):
        rows.append({"quarter": str(q), "d_alt": call_value, "asof": asof})
    return pd.DataFrame(rows, columns=["quarter", "d_alt", "asof"])


def combined_direction(components: dict[str, float], histories: dict[str, pd.DataFrame]) -> dict:
    """sign(sum d_alt_s / std_s); each std over >= 4 clean values up to and including q."""
    parts, notes = {}, []
    for src, d in components.items():
        h = histories[src]
        if d is None:
            return {"status": f"not run (no data: {src})", "z_sum": None, "parts": parts}
        if len(h) < MIN_VALUES:
            return {"status": f"not run ({src} has {len(h)} clean d_alt values, needs >= {MIN_VALUES})",
                    "z_sum": None, "parts": parts}
        sd = float(h.d_alt.std(ddof=1))
        parts[src] = {"d_alt": d, "std": sd, "n": len(h), "z": d / sd,
                      "quarters": f"{h.quarter.iloc[0]}..{h.quarter.iloc[-1]}"}
    z = sum(p["z"] for p in parts.values())
    return {"status": "ok", "z_sum": z, "parts": parts}


class TargetData:
    """Target YoY values (hypotheses 3.11), cached. target 'y' = revenue (revenue_pit versions: XBRL for
    US names, 6-K releases for TCOM); 'k' = headline KPI (release_values, metric 'kpi').

    choice 'asof'  : latest filing/release filed strictly before `asof` that reports q with its q-4 base;
    choice 'first' : the first filing/release that reports q (the realised outcome being scored)."""

    def __init__(self, versions: pd.DataFrame, kpi_values: pd.DataFrame | None = None):
        self._v = {n: g for n, g in versions.groupby("name")}
        kv = kpi_values[kpi_values.metric == "kpi"] if kpi_values is not None else None
        self._k = {n: g for n, g in kv.groupby("name")} if kv is not None else {}
        self._cache: dict = {}

    def get(self, name: str, target: str, q: Quarter, choice: str, asof: dt.date | None = None) -> dict | None:
        key = (name, target, str(q), choice, asof if choice == "asof" else None)
        if key not in self._cache:
            if target == "y":
                v = self._v.get(name)
                r = None if v is None else yoy_same_filing(v, name, q, choice, asof)
            elif target == "k":
                v = self._k.get(name)
                r = None if v is None else yoy_same_release(v, name, q, "kpi", choice, asof)
            else:
                raise ValueError(target)
            if r is not None and choice == "asof":
                assert_pit(pd.DataFrame({"published": [r["filed"]]}), asof, strict=True)
            self._cache[key] = r
        return self._cache[key]


def _td(td) -> TargetData:
    return td if isinstance(td, TargetData) else TargetData(td)


def training_pairs(name: str, s: F.Series, versions, exclusion: tuple[Quarter, Quarter],
                   asof: dt.date, before_q: Quarter, first_q: Quarter = Quarter(2019, 1),
                   target: str = "y", dalt_fn=None) -> pd.DataFrame:
    """Clean (d_t, d_alt) pairs for quarters p before `before_q`: d_t_p = t_p - t_{p-1}, both the 3.11 value
    at asof (latest filing filed strictly before asof); d_alt_p at p's own quarter end.
    `versions` is a TargetData or a revenue_pit DataFrame (target y)."""
    td, dalt_fn = _td(versions), dalt_fn or F.d_alt
    rows = []
    p = first_q
    while p < before_q:
        a = F.checkpoint_asof(p, "qend")
        if d_clean(p, exclusion) and a <= asof:
            cur, prev = td.get(name, target, p, "asof", asof), td.get(name, target, p - 1, "asof", asof)
            if cur is not None and prev is not None:
                r = dalt_fn(s, p, a)
                if r["status"] == "ok":
                    for u in r["_used"]:
                        assert_pit(u, asof)
                    assert_pit(pd.DataFrame({"published": [cur["filed"], prev["filed"]]}), asof, strict=True)
                    rows.append({"name": name, "quarter": str(p), "d_y": cur["yoy_pct"] - prev["yoy_pct"],
                                 "d_alt": r["d_alt"], "y_filed": cur["filed"], "y_prev_filed": prev["filed"]})
        p = p + 1
    return pd.DataFrame(rows, columns=["name", "quarter", "d_y", "d_alt", "y_filed", "y_prev_filed"])


def beta_origin(pairs: pd.DataFrame) -> float:
    x, y = pairs.d_alt.to_numpy(float), pairs.d_y.to_numpy(float)
    return float((x * y).sum() / (x * x).sum())


def magnitude(name_pairs: pd.DataFrame, pooled_pairs_fn, y_prev: float | None, d: float | None) -> dict:
    """yhat = y_{q-1} + beta * d_alt; name beta if >= 4 pairs, else pooled same-source beta."""
    out = {"beta": None, "beta_basis": None, "n_pairs": len(name_pairs), "pair_quarters": "", "yhat": None}
    if d is None or y_prev is None:
        out["status"] = "not run (no d_alt)" if d is None else "not run (no like-for-like base for y_{q-1})"
        return out
    pairs, basis = name_pairs, "name"
    if len(pairs) < MIN_VALUES:
        pairs, basis = pooled_pairs_fn(), "pooled (same source, all names)"
        if len(pairs) < MIN_VALUES:
            out.update(status=f"not run (name has {len(name_pairs)} pairs, pooled has {len(pairs)}; needs >= {MIN_VALUES})",
                       n_pairs=len(pairs))
            return out
    b = beta_origin(pairs)
    out.update(beta=b, beta_basis=basis, n_pairs=len(pairs), yhat=y_prev + b * d, status="ok",
               pair_quarters=f"{pairs.quarter.min()}..{pairs.quarter.max()}")
    return out


# ------------------------------------------------------------------------------------- guidance


def latest_release(releases: pd.DataFrame, name: str, asof: dt.date) -> pd.Series:
    r = releases[(releases.name == name) & (releases.is_amendment == 0)].copy()
    r = r[pd.to_datetime(r.filed).dt.date < asof]
    if r.empty:
        raise F.DataError(f"{name}: no earnings release filed before {asof}")
    return r.sort_values("filed").iloc[-1]


def guidance(name: str, rel: pd.Series, q: Quarter) -> dict:
    """Scan the latest release (snapshot) for a guidance/outlook section. None found -> 'no guidance'.
    Something found -> fail loudly: quantitative guidance must be extracted by hand into the spec's
    fields (metric, low, high, midpoint, basis, URL) before a label can be assigned."""
    snap = f"{name}_{rel.accession}_{rel.document}"
    path = find_snapshot("sec_filings", snap)
    if path is None:
        raise FileNotFoundError(f"release snapshot not found: data/raw/sec_filings/*/{snap}")
    text = re.sub(r"\s+", " ", html_to_text(read_snapshot(path)))
    text = _BOILERPLATE.sub(" ", text)               # safe-harbour boilerplate lists "expect", "anticipate"
    hits = [m.group(0) for pat in GUIDANCE_PATTERNS for m in re.finditer(pat, text, re.I)]
    if hits:
        raise NotImplementedError(f"{name} {rel.quarter} release mentions {hits[:3]}: extract the guidance "
                                  f"for {q} by hand before labelling")
    return {"label": "no guidance", "url": rel.source_url, "release_quarter": rel.quarter, "filed": rel.filed,
            "snapshot": str(path.relative_to(REPO_ROOT)),
            "detail": f"no outlook/guidance section in the {rel.quarter} results release (patterns: "
                      f"{', '.join(GUIDANCE_PATTERNS)}; safe-harbour boilerplate excluded)"}


# ------------------------------------------------------------------------------------- one-offs


def break_notes(name: str, q: Quarter, target: str = "y", breaks: list[dict] | None = None) -> str:
    """Structural breaks (config/breaks.yaml) touching y_q, y_{q-1} or y_{q-4} of a live call
    (hypotheses 3.8, 3.12; CLAUDE.md: live-call memos list one-offs in the base-year period)."""
    want = {str(q): "q", str(q - 1): "q-1", str(q - 4): "q-4"}
    out = []
    for b in breaks if breaks is not None else config.breaks():
        if b["name"] != name or target not in b["targets"]:
            continue
        hit = [f"{want[a]}={a}" for a in b["affected_yoy_quarters"] if a in want]
        if hit:
            out.append(f"{b['materiality'].upper()} {b['type']} ({', '.join(hit)}): {b['event']} [{b['source']}]")
    return " || ".join(out)


# ------------------------------------------------------------------------------------- the call


def _inputs(r: dict, s: F.Series) -> tuple[str, str]:
    cur, prev = [u for u in r["_used"]]
    if s.frequency == "monthly":
        f = lambda u, role: ",".join(sorted(pd.to_datetime(u[u.role == role].obs_date).dt.strftime("%Y-%m")))
    else:
        f = lambda u, role: (f"{u[u.role == role].obs_date.min()}..{u[u.role == role].obs_date.max()} "
                             f"({(u.role == role).sum()} days)")
    return (f"q: {f(cur, 'current')} vs {f(cur, 'base')}; max published {cur.published.max()}",
            f"q-1: {f(prev, 'current')} vs {f(prev, 'base')}; max published {prev.published.max()}")


def _urls(s: F.Series, r: dict, co: dict) -> str:
    if s.source == "caac":
        t = s.meta["table"].set_index("obs_date")
        months = sorted({d for u in r["_used"] for d in u.obs_date})
        return " ".join(t.loc[m, "bulletin_url"] for m in months)
    if s.source == "wikipedia":
        titles = [t for a in co["wikipedia_articles"] for t in a["titles_since_2019"]]
        return ("https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/"
                "{title}/daily/... titles: " + "; ".join(titles))
    if s.source == "tsa":
        return "https://www.tsa.gov/travel/passenger-volumes"
    return ""


def calls_at(name: str, q: Quarter, asof: dt.date, series: dict[str, F.Series], td, cos: dict,
             target: str = "y", dalt_fn=None) -> list[dict]:
    """THE per-quarter call (shared by the live calls and the walk-forward backtest, evaluate.py):
    direction + magnitude for every source of `name` (volume source, Wikipedia) and the combined
    direction, for target t in {y, k}, at an explicit asof. `dalt_fn(s, p, a)` defaults to features.d_alt
    (the evaluator passes a cached / earnings-window-removed version). Rows carry `t_q_minus_1_pct`
    (3.11 value at asof) and internal keys starting with '_'."""
    td, dalt_fn = _td(td), dalt_fn or F.d_alt
    excl = _excl(cos[name])
    srcs = [(src, sid) for n, src, sid in F.source_map(cos) if n == name]
    tp = td.get(name, target, q - 1, "asof", asof)
    t_prev = None if tp is None else tp["yoy_pct"]
    rows, comps, hists, all_used = [], {}, {}, []
    for src, sid in srcs:
        s = series[sid]
        r = dalt_fn(s, q, asof)
        for u in r["_used"]:
            assert_pit(u, asof)
            all_used.append(u)
        d = r["d_alt"]
        comps[src] = d
        hists[src] = (dalt_history(s, q, asof, excl, d, dalt_fn=dalt_fn) if d is not None
                      else pd.DataFrame(columns=["quarter", "d_alt"]))
        name_pairs = training_pairs(name, s, td, excl, asof, q, target=target, dalt_fn=dalt_fn)

        def pooled(src=src):
            return pd.concat([training_pairs(n, series[sd], td, _excl(cos[n]), asof, q, target=target, dalt_fn=dalt_fn)
                              for n, sc, sd in F.source_map(cos) if sc == src], ignore_index=True)

        m = magnitude(name_pairs, pooled, t_prev, d)
        inp_q, inp_p = _inputs(r, s) if r["status"] == "ok" else ("", "")
        rows.append({"name": name, "quarter": str(q), "source": src, "asof": asof,
                     "alt_q": r["alt"], "alt_q_minus_1": r["alt_prev"], "d_alt": d, "status": r["status"],
                     "call": direction(d) if r["status"] == "ok" else r["status"],
                     "t_q_minus_1_pct": t_prev,
                     "beta_pp_per_unit_d_alt": m["beta"], "beta_basis": m["beta_basis"], "n_pairs": m["n_pairs"],
                     "pair_quarters": m["pair_quarters"],
                     "yhat_pct": m["yhat"], "magnitude_status": m["status"],
                     "inputs_q": inp_q, "inputs_q_minus_1": inp_p,
                     "combined_detail": "", "_r": r, "_series": s, "_t_prev": tp})
    c = combined_direction(comps, hists)
    detail = "; ".join(f"{k}: d_alt {v['d_alt']:.6f} / std {v['std']:.6f} (n={v['n']}, {v['quarters']}) = {v['z']:.4f}"
                       for k, v in c["parts"].items())
    rows.append({"name": name, "quarter": str(q), "source": "combined", "asof": asof,
                 "alt_q": None, "alt_q_minus_1": None, "d_alt": c["z_sum"], "status": c["status"],
                 "call": direction(c["z_sum"]) if c["status"] == "ok" else c["status"],
                 "t_q_minus_1_pct": t_prev,
                 "beta_pp_per_unit_d_alt": None, "beta_basis": None, "n_pairs": None, "pair_quarters": "",
                 "yhat_pct": None, "magnitude_status": COMBINED_NOT_RUN_MAG,
                 "inputs_q": " | ".join(x["inputs_q"] for x in rows),
                 "inputs_q_minus_1": " | ".join(x["inputs_q_minus_1"] for x in rows),
                 "combined_detail": ("d_alt column = sum of d_alt/std (std: ddof=1 over clean d_alt values up to and "
                                     "including q; earlier quarters at their quarter-end checkpoint). " + detail),
                 "_r": None, "_series": None, "_t_prev": tp})
    if all_used:
        assert_pit(pd.concat(all_used, ignore_index=True), asof)
    return rows


LIVE_COLUMNS = ["name", "quarter", "source", "asof", "alt_q", "alt_q_minus_1", "d_alt", "status", "call",
                "y_q_minus_1_pct", "beta_pp_per_unit_d_alt", "beta_basis", "n_pairs", "pair_quarters", "yhat_pct",
                "magnitude_status", "inputs_q", "inputs_q_minus_1", "combined_detail", "guidance_label",
                "guidance_url", "source_urls", "y_q_minus_1_url", "notes"]


def live_calls(name: str, q: Quarter, asof: dt.date, series: dict[str, F.Series], versions: pd.DataFrame,
               releases: pd.DataFrame, cos: dict, extra_notes: str = "", target: str = "y",
               kpi_values: pd.DataFrame | None = None) -> list[dict]:
    """Direction + magnitude + guidance rows for every source of `name` (volume, Wikipedia, combined).
    `extra_notes` (e.g. whether the company reports an adjusted metric, hypotheses 3.12) is copied
    into every row next to the structural-break notes."""
    notes = " || ".join(x for x in (break_notes(name, q, target), extra_notes) if x)
    co = cos[name]
    rel = latest_release(releases, name, asof)
    g = guidance(name, rel, q)
    td = TargetData(versions, kpi_values)
    core = calls_at(name, q, asof, series, td, cos, target)
    out = []
    for c in core:
        tp = c["_t_prev"]
        if c["source"] == "combined":
            urls = " ".join(x["source_urls"] for x in out)
        else:
            urls = _urls(c["_series"], c["_r"], co)
        row = {k: v for k, v in c.items() if not k.startswith("_") and k != "t_q_minus_1_pct"}
        row.update(y_q_minus_1_pct=c["t_q_minus_1_pct"], guidance_label=g["label"], guidance_url=g["url"],
                   source_urls=urls, y_q_minus_1_url=None if tp is None else tp["source_url"], notes=notes)
        out.append({k: row[k] for k in LIVE_COLUMNS})
    return out
