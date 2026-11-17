"""Session 6: outputs/tracker/sector_nowcast_tracker.xlsx (openpyxl).

Sheets: Tracker (one row per name x live quarter), Data relevancy (name x source matrix; green only if the
GREEN rule holds, otherwise grey; multiple-testing line underneath), Lead time (lead_time.csv), Backtest
(calls.csv), Notes (method in 10 lines + limitations). Hit rates are visible formulas (hits / N).
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

GREEN = PatternFill("solid", fgColor="C6EFCE")
GREY = PatternFill("solid", fgColor="D9D9D9")
BOLD = Font(bold=True)
WRAP = Alignment(wrap_text=True, vertical="top")


def _write_df(ws, df: pd.DataFrame, start_row: int = 1):
    for j, c in enumerate(df.columns, 1):
        ws.cell(start_row, j, str(c)).font = BOLD
    for i, row in enumerate(df.itertuples(index=False), start_row + 1):
        for j, v in enumerate(row, 1):
            if v is None or (isinstance(v, float) and pd.isna(v)):
                continue
            ws.cell(i, j, v.item() if hasattr(v, "item") else (str(v) if not isinstance(v, (int, float, str, bool)) else v))
    ws.freeze_panes = ws.cell(start_row + 1, 1)


def _widths(ws, default: int = 14, wide: dict | None = None):
    for j in range(1, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(j)].width = (wide or {}).get(j, default)


SRC_LABEL = {"tsa": "TSA", "caac": "CAAC", "wikipedia": "Wikipedia", "combined": "Combined"}


def tracker_sheet(ws, live: pd.DataFrame, results: pd.DataFrame, cos: dict):
    """One row per (name, live quarter); per source: call, guidance label, implied revenue YoY (yhat, target y),
    headline hit rate for y (hits, N, formula hit rate, min hits, momentum hits, placebo percentile)."""
    r = results[results.model == "direction"].set_index(["name", "source", "target"])
    hdr = ["Name", "Live quarter", "Live call", "As-of", "Last actual revenue YoY % (y_q-1)", "Guidance (metric, range, guided direction)"]
    per = ["call", "read vs guidance", "implied revenue YoY % (yhat)", "headline y hits", "headline y N",
           "hit rate (=hits/N)", "min hits p<0.05", "momentum hits (same quarters)", "placebo percentile", "GREEN"]
    cols = hdr + [f"{s}: {p}" for s in ("Volume", "Wikipedia", "Combined") for p in per] + \
        ["Base-period caveat", "Adjusted-metric note (3.12)", "Next earnings date", "Score"]
    for j, c in enumerate(cols, 1):
        ws.cell(1, j, c).font = BOLD
        ws.cell(1, j).alignment = WRAP
    i = 2
    ly = live[live.target == "y"]
    for (name, q, lc), g in ly.groupby(["name", "quarter", "live_call"], sort=False):
        g = g.set_index("source")
        vol = cos[name]["volume_source"]
        first = g.iloc[0]
        gtxt = ""
        if "guidance_metric" in g.columns and isinstance(first.get("guidance_metric"), str):
            gtxt = (f"{first['guidance_metric']} {first['guidance_low_pct']:.1f}% to {first['guidance_high_pct']:.1f}% "
                    f"(mid {first['guidance_mid_pct']:.2f}%, {first['guidance_basis']}); prev {first['guidance_prev_yoy_pct']:.2f}%; "
                    f"guided {first['guided_direction']}")
        else:
            gtxt = str(first.get("guidance_label", ""))
        vals = [name, q, lc, str(first["asof"]), first["t_q_minus_1_pct"], gtxt]
        for j, v in enumerate(vals, 1):
            if v is not None and not (isinstance(v, float) and pd.isna(v)):
                ws.cell(i, j, v)
        col = len(hdr) + 1
        for src in (vol, "wikipedia", "combined"):
            x = g.loc[src] if src in g.index else None
            key = (name, src, "y")
            rr = r.loc[key] if key in r.index else None
            hits_col, n_col = get_column_letter(col + 3), get_column_letter(col + 4)
            cells = [None if x is None else x["call"], None if x is None else x.get("guidance_label"),
                     None if x is None else x["yhat_pct"],
                     None if rr is None else rr["hits"], None if rr is None else rr["N_realised"],
                     f"=IF({n_col}{i}>0,{hits_col}{i}/{n_col}{i},\"\")" if rr is not None and rr["N_realised"] else None,
                     None if rr is None else rr["min_hits_p05_realised"], None if rr is None else rr["momentum_hits"],
                     None if rr is None else rr["placebo_percentile"], None if rr is None else bool(rr["green"])]
            for k, v in enumerate(cells):
                if v is not None and not (isinstance(v, float) and pd.isna(v)):
                    ws.cell(i, col + k, v.item() if hasattr(v, "item") else v)
            ws.cell(i, col + 5).number_format = "0%"
            col += len(per)
        for v in (first["base_period_notes"], first.get("adjusted_metric_note", ""), first["next_earnings_estimate"],
                  first["score"]):
            if isinstance(v, str):
                ws.cell(i, col, v).alignment = WRAP
            col += 1
        i += 1
    ws.freeze_panes = "C2"
    _widths(ws, 13, {1: 7, 2: 9, 3: 26, 6: 40, len(cols) - 3: 70, len(cols) - 2: 50, len(cols) - 1: 26, len(cols): 30})
    ws.cell(i + 1, 1, "Calls for target k (KPI) and every field per source: Backtest-style detail in "
                      "outputs/tables/live_calls.csv. Direction calls are identical for y and k (same d_alt); "
                      "hit rates above are for target y.").font = Font(italic=True)


def relevancy_sheet(ws, results: pd.DataFrame, mt: dict, cos: dict):
    d = results[results.model == "direction"]
    sources = ["tsa", "caac", "hkia", "wikipedia", "combined"]
    ws.cell(1, 1, "Name").font = BOLD
    ws.cell(1, 2, "Target").font = BOLD
    for j, s in enumerate(sources, 3):
        ws.cell(1, j, s).font = BOLD
    i = 2
    for name in cos:
        for t in ("y", "k"):
            ws.cell(i, 1, name)
            ws.cell(i, 2, t)
            for j, s in enumerate(sources, 3):
                x = d[(d.name == name) & (d.source == s) & (d.target == t)]
                if x.empty:
                    continue
                x = x.iloc[0]
                if x.N_realised:
                    txt = (f"{int(x.hits)}/{int(x.N_realised)} (need {int(x.min_hits_p05_realised)}; momentum "
                           f"{int(x.momentum_hits)}; placebo pct {x.placebo_percentile:.0f})")
                    if x.green:
                        txt += " GREEN"
                else:
                    txt = x.status
                c = ws.cell(i, j, txt)
                c.fill = GREEN if (x.N_realised and bool(x.green)) else GREY
                c.alignment = WRAP
            i += 1
    i += 1
    ws.cell(i, 1, (f"Multiple testing: {mt['direction_cells_tested']} pre-registered direction cells tested; "
                   f"{mt['expected_to_pass_by_chance']} expected to pass by chance (0.05 x cells); GREEN found: "
                   f"{mt['green_found']} ({mt['green_cells'] or 'none'}). BH q (placebo p) < 0.05: "
                   f"{mt['cells_bh_q_placebo_below_0.05']}. Note: {mt['note']}.")).font = BOLD
    ws.cell(i + 1, 1, "GREEN = beats both baselines (50% and momentum, same quarters) AND shuffle-placebo "
                      "percentile >= 95 (docs/hypotheses.md). Green fill only for GREEN cells; every other cell grey. "
                      "Source: outputs/tables/results.csv, multiple_testing.csv.")
    _widths(ws, 34, {1: 7, 2: 7})


def notes_sheet(ws, method: list[str], limits: list[str]):
    ws.cell(1, 1, "Method").font = BOLD
    for i, line in enumerate(method, 2):
        ws.cell(i, 1, line).alignment = WRAP
    r = len(method) + 3
    ws.cell(r, 1, "Limitations").font = BOLD
    for i, line in enumerate(limits, r + 1):
        ws.cell(i, 1, line).alignment = WRAP
    ws.column_dimensions["A"].width = 150


def build(path: Path, live: pd.DataFrame, results: pd.DataFrame, lead: pd.DataFrame, calls: pd.DataFrame,
          mt: dict, cos: dict, method: list[str], limits: list[str]) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tracker"
    tracker_sheet(ws, live, results, cos)
    relevancy_sheet(wb.create_sheet("Data relevancy"), results, mt, cos)
    ws = wb.create_sheet("Lead time")
    _write_df(ws, lead)
    _widths(ws)
    ws = wb.create_sheet("Backtest")
    _write_df(ws, calls)
    _widths(ws)
    notes_sheet(wb.create_sheet("Notes"), method, limits)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
