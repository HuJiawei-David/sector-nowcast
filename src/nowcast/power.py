"""Pre-registration power table (docs/hypotheses.md).

For every (name, source, target) direction cell: the number of headline quarters N that can be
scored, the minimum hit count h* with one-sided binomial P(X >= h* | N, 0.5) < 0.05, and the
probability of reaching h* if the true hit rate were 0.6 / 0.7 / 0.8 (power of the binomial
reference test), and the N left in the structural-break robustness run after dropping calls whose
y_q or y_{q-1} (k_q, k_{q-1}) is listed in a MAJOR break (config/breaks.yaml). Headline windows are
fixed at prereg (config/companies.yaml). Computed from config only, before any alt-data is downloaded.

Run: .venv/bin/python -m nowcast.power  (from repo root with src on the path)
Writes outputs/tables/power_table.csv and outputs/tables/power_table.md.
"""
from __future__ import annotations

import csv
from pathlib import Path

from scipy.stats import binom

from . import config
from .quarters import Quarter, d_clean, qrange

ALPHA = 0.05
TRUE_RATES = (0.6, 0.7, 0.8)
COMBINED_MIN_CLEAN = 4  # combined source needs >= 4 clean d_alt values up to and including q
# Alt-data history starts 2019-01 (config/sources.yaml history_start), so the first YoY is
# 2020 and no pre-pandemic clean d_alt values exist; the first clean d_alt is the first clean d.
ALT_HISTORY_START = Quarter(2019, 1)
BREAK_ROBUSTNESS_MIN_N = 6  # below this the structural-break robustness run is "not informative"

def min_hits(n: int, alpha: float = ALPHA) -> int | None:
    """Smallest h with P(X >= h | n, 0.5) < alpha (one-sided); None if unattainable."""
    for h in range(n + 1):
        if binom.sf(h - 1, n, 0.5) < alpha:
            return h
    return None


def power_at(n: int, h: int | None, p: float) -> float | None:
    return None if h is None else float(binom.sf(h - 1, n, p))


def scored_quarters(headline: tuple[Quarter, Quarter], exclusion: tuple[Quarter, Quarter],
                    combined: bool) -> list[Quarter]:
    qs = [q for q in qrange(*headline) if d_clean(q, exclusion)]
    if not combined:
        return qs
    out = []
    for q in qs:
        n_clean = sum(1 for p in qrange(ALT_HISTORY_START + 4, q) if d_clean(p, exclusion))
        if n_clean >= COMBINED_MIN_CLEAN:
            out.append(q)
    return out


def major_break_quarters(name: str, target: str) -> set[Quarter]:
    """YoY quarters of `name`'s `target` listed in a MAJOR structural break."""
    out: set[Quarter] = set()
    for b in config.breaks():
        if b["name"] == name and target in b["targets"] and b["materiality"] == "major":
            out |= {Quarter.parse(q) for q in b["affected_yoy_quarters"]}
    return out


def drop_major_breaks(qs: list[Quarter], major: set[Quarter]) -> list[Quarter]:
    """hypotheses.md 3.8: drop the call for q if y_q or y_{q-1} is in a MAJOR break."""
    return [q for q in qs if q not in major and (q - 1) not in major]


def build_rows() -> list[dict]:
    rows = []
    for name, c in config.companies().items():
        exclusion = config.window(c["exclusion_window"])
        headline = config.window(c["headline_window"])
        targets = ["y"] + (["k"] if c.get("kpi") else [])
        sources = [c["volume_source"], "wikipedia", "combined"]
        for target in targets:
            major = major_break_quarters(name, target)
            for src in sources:
                qs = scored_quarters(headline, exclusion, combined=(src == "combined"))
                n = len(qs)
                h = min_hits(n)
                row = {
                    "name": name, "source": src, "target": target,
                    "first_q": str(qs[0]) if qs else "", "last_q": str(qs[-1]) if qs else "",
                    "N": n, "min_hits_p05": h,
                    "p_at_min_hits": round(float(binom.sf(h - 1, n, 0.5)), 4) if h is not None else None,
                }
                for p in TRUE_RATES:
                    pw = power_at(n, h, p)
                    row[f"power_if_true_{p}"] = round(pw, 3) if pw is not None else None
                rq = drop_major_breaks(qs, major)
                row["N_excl_major_breaks"] = len(rq)
                row["min_hits_excl_major"] = min_hits(len(rq))
                row["break_robustness"] = ("robustness not informative"
                                           if len(rq) < BREAK_ROBUSTNESS_MIN_N else "")
                rows.append(row)
    return rows


def family_summary(rows: list[dict]) -> dict:
    n_cells = len(rows)
    return {"direction_cells": n_cells, "expected_false_passes": round(ALPHA * n_cells, 2)}


def to_markdown(rows: list[dict]) -> str:
    cols = ["name", "source", "target", "first_q", "last_q", "N", "min_hits_p05",
            "p_at_min_hits", "power_if_true_0.6", "power_if_true_0.7", "power_if_true_0.8",
            "N_excl_major_breaks", "min_hits_excl_major", "break_robustness"]
    lines = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        lines.append("| " + " | ".join("" if r[c] is None else str(r[c]) for c in cols) + " |")
    s = family_summary(rows)
    lines.append("")
    lines.append(f"Headline direction cells: {s['direction_cells']}; "
                 f"expected to pass p<0.05 by chance alone: {s['expected_false_passes']} (= 0.05 x cells).")
    return "\n".join(lines)


def main() -> None:
    rows = build_rows()
    out = config.REPO_ROOT / "outputs" / "tables"
    out.mkdir(parents=True, exist_ok=True)
    with open(out / "power_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    md = to_markdown(rows)
    Path(out / "power_table.md").write_text(md + "\n")
    print(md)


if __name__ == "__main__":
    main()
