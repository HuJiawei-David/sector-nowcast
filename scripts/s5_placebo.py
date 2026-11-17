"""Session 5: placebos, GREEN flags, multiple testing, inflections, lead time, charts. No network.

    .venv/bin/python scripts/s5_placebo.py        (after scripts/s4_evaluate.py)

Recomputes the Session 4 calls (asserting they equal outputs/tables/calls.csv byte-for-byte), then:
  outputs/tables/results.csv, robustness.csv   + placebo_percentile, placebo_p, GREEN, bh_q_placebo,
                                                 wrong_company, wrong_company_percentile
  outputs/tables/relevancy_matrix.csv          sql/results_summary.sql (now with placebo pct and GREEN)
  outputs/tables/multiple_testing.csv          cells tested, expected by chance, GREEN found
  outputs/tables/placebo_wrong_company.csv     every (name, other name's Wikipedia series) score
  outputs/tables/inflections.csv, inflections_summary.csv
  outputs/tables/calls_checkpoints.csv         day28 / day56 calls (same function as quarter end)
  outputs/tables/lead_time.csv                 hit rate per checkpoint + median weeks to the print
  outputs/charts/lead_time.png                 (data: lead_time.csv)
  outputs/charts/pandemic_inflections_excluded.png  (data: outputs/tables/chart_data_pandemic.csv)
"""
import io
import sys

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from nowcast import config, evaluate as E, features as F, placebo as P, revenue as RV  # noqa: E402
from nowcast.quarters import Quarter, d_clean, qrange  # noqa: E402
from nowcast.rawstore import REPO_ROOT  # noqa: E402

T = REPO_ROOT / "outputs" / "tables"
CH = REPO_ROOT / "outputs" / "charts"
VARIANT_OF = {a: v for a, _, v in E.ANALYSES}
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"
C_VOL, C_WIKI, C_COMB = "#eb6834", "#2a78d6", "#7b5cc4"


def csv_text(df: pd.DataFrame) -> str:
    b = io.StringIO()
    df.to_csv(b, index=False, float_format="%.6f")
    return b.getvalue()


def chart_lead_time(lt: pd.DataFrame, cos: dict) -> None:
    names = list(cos)
    fig, axes = plt.subplots(2, 4, figsize=(15, 7.2), sharey=True, facecolor=SURFACE)
    axes = axes.ravel()
    for ax, name in zip(axes, names):
        ax.set_facecolor(SURFACE)
        g = lt[lt.name == name]
        for (src, tgt), h in g.groupby(["source", "target"]):
            h = h.sort_values("checkpoint_order")
            col = C_WIKI if src == "wikipedia" else C_COMB if src == "combined" else C_VOL
            ax.plot(h.median_weeks_to_release, 100 * h.hit_rate, color=col, lw=2,
                    ls="-" if tgt == "y" else "--", marker="o", ms=4, markeredgecolor=SURFACE,
                    label=f"{src} {tgt}")
        ax.axhline(50, color=MUTED, lw=0.8)
        ax.set_title(name, loc="left", fontsize=10, fontweight="bold", color=INK)
        ax.invert_xaxis()
        ax.set_ylim(0, 105)
        ax.grid(axis="y", color=GRID, lw=0.6)
        ax.tick_params(colors=INK2, labelsize=8, length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
        ax.set_xlabel("median weeks before the earnings release", fontsize=8, color=INK2)
    axes[0].set_ylabel("direction hit rate (%)", color=INK2, fontsize=9)
    axes[4].set_ylabel("direction hit rate (%)", color=INK2, fontsize=9)
    leg = axes[-1]
    leg.axis("off")
    from matplotlib.lines import Line2D
    handles = [Line2D([], [], color=C_VOL, lw=2, label="volume source (TSA / CAAC)"),
               Line2D([], [], color=C_WIKI, lw=2, label="Wikipedia"),
               Line2D([], [], color=C_COMB, lw=2, label="combined"),
               Line2D([], [], color=MUTED, lw=1.5, ls="-", label="line style: target y (revenue)"),
               Line2D([], [], color=MUTED, lw=1.5, ls="--", label="line style: target k (KPI)"),
               Line2D([], [], color=MUTED, lw=0.8, label="50% baseline")]
    leg.legend(handles=handles, loc="center left", frameon=False, fontsize=9)
    leg.text(0, 0.05, "Points: day 28, day 56, quarter end (left to right).\nHeadline windows only; "
             "CAAC and TCOM combined have no\ndata at day 28 (not run). Source: outputs/tables/lead_time.csv",
             fontsize=7.5, color=INK2, transform=leg.transAxes)
    fig.suptitle("Lead time: quarter-to-date direction hit rate vs weeks before the print", x=0.01, ha="left",
                 fontsize=13, color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(CH / "lead_time.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def pandemic_data(inp: dict) -> pd.DataFrame:
    """Excluded-era (non-clean) quarters with a computable d_y: revenue YoY as first reported (US: XBRL
    snapshot read from 2019Q1, the same companyfacts files; TCOM: 6-K versions), alt d_alt at quarter end."""
    pipe = config.load_yaml("pipeline.yaml")
    cos, series = inp["cos"], inp["series"]
    rows = []
    for name, co in cos.items():
        excl = config.window(co["exclusion_window"])
        if co["revenue"]["source"] == "xbrl":
            v = RV.us_revenue_versions(name, co, pipe["xbrl"], Quarter(2019, 1))
        else:
            v = pd.read_csv(REPO_ROOT / "data/processed/revenue_pit.csv", dtype={"accession": str})
            v = v[v.name == name]
        y = {}
        for q in qrange(Quarter(2020, 1), Quarter(2024, 2)):
            r = RV.yoy_same_filing(v, name, q, "first")
            if r is not None:
                y[q] = r["yoy_pct"]
        for q in qrange(Quarter(2020, 2), Quarter(2024, 1)):
            if d_clean(q, excl) or q not in y or (q - 1) not in y:
                continue
            row = {"name": name, "quarter": str(q), "y_pct": y[q], "y_prev_pct": y[q - 1], "d_y_pp": y[q] - y[q - 1]}
            for src, sid in (("volume", co["volume_source"]), ("wikipedia", f"wikipedia:{name}")):
                r = F.d_alt(series[sid], q, F.checkpoint_asof(q, "qend"))
                row[f"{src}_d_alt"] = r["d_alt"]
            rows.append(row)
    df = pd.DataFrame(rows)
    df["inflection"] = False
    for name, g in df.groupby("name"):
        s = np.sign(g.d_y_pp.to_numpy())
        df.loc[g.index[1:], "inflection"] = s[1:] != s[:-1]
    for src in ("volume", "wikipedia"):
        df[f"{src}_caught"] = np.where(df[f"{src}_d_alt"].isna(), np.nan,
                                       (np.sign(df[f"{src}_d_alt"]) == np.sign(df.d_y_pp)).astype(float))
    return df


def chart_pandemic(df: pd.DataFrame, cos: dict) -> None:
    names = [n for n in cos if n in set(df.name)]
    fig, axes = plt.subplots(2, 4, figsize=(15, 7.6), facecolor=SURFACE)
    axes = axes.ravel()
    for ax, name in zip(axes, names):
        ax.set_facecolor("#f1f0ec")
        g = df[df.name == name].reset_index(drop=True)
        x = np.arange(len(g))
        ax.bar(x, g.d_y_pp.clip(-150, 150), color=["#b9b8b2" if not f else INK2 for f in g.inflection], width=0.7)
        ax.axhline(0, color=MUTED, lw=0.8)
        for i, r in g.iterrows():
            if r.inflection:
                lab = "".join([("V" if r.volume_caught == 1 else "v" if r.volume_caught == 0 else "-"),
                               ("W" if r.wikipedia_caught == 1 else "w" if r.wikipedia_caught == 0 else "-")])
                yv = float(np.clip(r.d_y_pp, -150, 150))
                ax.annotate(lab, (i, yv), xytext=(0, 4 if yv >= 0 else -11), textcoords="offset points",
                            ha="center", fontsize=7.5, color=INK)
        inf = g[g.inflection]
        vol = cos[name]["volume_source"].upper()
        ax.set_title(f"{name}  (EXCLUDED quarters)", loc="left", fontsize=10, fontweight="bold", color=INK)
        ax.text(0.01, 0.97, f"inflections {len(inf)}: {vol} caught {int(inf.volume_caught.sum())}, "
                f"Wikipedia caught {int(inf.wikipedia_caught.sum())}", transform=ax.transAxes, fontsize=7.5,
                color=INK2, va="top")
        ax.set_xticks(x)
        ax.set_xticklabels(g.quarter, rotation=90, fontsize=7)
        ax.set_ylim(-180, 180)
        ax.tick_params(colors=INK2, labelsize=7.5, length=0)
        for sp in ax.spines.values():
            sp.set_visible(False)
    axes[0].set_ylabel("change in revenue YoY growth, d_y (pp)", fontsize=8.5, color=INK2)
    axes[4].set_ylabel("change in revenue YoY growth, d_y (pp)", fontsize=8.5, color=INK2)
    for ax in axes[len(names):]:
        ax.axis("off")
    axes[-1].text(0, 0.95, (
        "EXCLUDED FROM EVERY RESULT (hard rule 4).\n\n"
        "Bars: quarter-on-quarter change in revenue YoY growth\nin quarters whose YoY uses a pandemic quarter "
        "(US\n2020Q1-2021Q4, TCOM 2020Q1-2022Q4). Dark bars =\ninflections (sign of d_y flips). Labels: V/W = the\n"
        "volume source / Wikipedia call caught it, v/w = missed,\n- = not computable. Bars clipped at +/-150 pp.\n\n"
        "Why they are excluded (they could inflate the hit\nrate): lockdown and reopening moved air traffic,\n"
        "attention and every company's growth together, and\nYoY against a collapsed base flips sign mechanically.\n"
        "A proxy that only tracks that common shock can\n'call' these swings, so counting them could add hits\n"
        "that say nothing about name-specific information.\nThe catch counts are shown for transparency only.\n\n"
        "ABNB and DASH listed in Dec 2020: d_y from 2021Q2.\nData: outputs/tables/chart_data_pandemic.csv"),
        fontsize=7.6, color=INK2, va="top", transform=axes[-1].transAxes)
    fig.suptitle("Pandemic-era inflections - excluded quarters, shown separately (not part of any result)",
                 x=0.01, ha="left", fontsize=13, color=INK, fontweight="bold")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    fig.savefig(CH / "pandemic_inflections_excluded.png", dpi=150, facecolor=SURFACE)
    plt.close(fig)


def main() -> None:
    inp = E.load_inputs()
    cos = inp["cos"]
    calls = E.make_calls(inp)
    if csv_text(calls) != (T / "calls.csv").read_text():
        raise SystemExit("recomputed calls differ from outputs/tables/calls.csv: rerun scripts/s4_evaluate.py first")
    res = E.results(calls, cos)
    res = P.add_shuffle(res, calls, VARIANT_OF)
    cache = E.DaltCache(E.release_dates(inp["releases"]), inp["releases_since"]).fn("base")
    wiki = lambda o, q, a: cache(inp["series"][f"wikipedia:{o}"], Quarter.parse(q), a)["d_alt"]
    res, wc = P.wrong_company(res, calls, wiki, VARIANT_OF)
    head = res[res.analysis == "headline"].drop(columns="analysis")
    head.to_csv(T / "results.csv", index=False, float_format="%.6f")
    res[res.analysis != "headline"].to_csv(T / "robustness.csv", index=False, float_format="%.6f")
    E.results_db(res, cos).to_csv(T / "relevancy_matrix.csv", index=False)
    mt = P.multiple_testing_line(head)
    pd.DataFrame([mt]).to_csv(T / "multiple_testing.csv", index=False, float_format="%.6f")
    wc.to_csv(T / "placebo_wrong_company.csv", index=False)

    inf = P.inflections(calls)
    inf.to_csv(T / "inflections.csv", index=False, float_format="%.6f")
    P.inflection_summary(inf).to_csv(T / "inflections_summary.csv", index=False)

    cp = E.make_calls(inp, variants=("base",), checkpoints=("day28", "day56"))
    cp.to_csv(T / "calls_checkpoints.csv", index=False, float_format="%.6f")
    allcp = pd.concat([cp, calls[calls.variant == "base"]], ignore_index=True)
    lt = P.lead_time(allcp, inp["releases"])
    lt.to_csv(T / "lead_time.csv", index=False, float_format="%.6f")
    chart_lead_time(lt, cos)

    pdm = pandemic_data(inp)
    pdm.to_csv(T / "chart_data_pandemic.csv", index=False, float_format="%.6f")
    chart_pandemic(pdm, cos)
    print("multiple testing:", mt)


if __name__ == "__main__":
    main()
