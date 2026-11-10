"""Session 3 charts: each source's YoY against each company's revenue YoY (descriptive only).

    .venv/bin/python scripts/s3_charts.py

Inputs: data/processed/alt_features.csv (alt_q at the quarter-end checkpoint, base variant: what the
model sees at asof = quarter end), outputs/tables/revenue_yoy.csv (y as first reported).
Outputs: outputs/charts/{tsa,wikipedia,caac}_yoy_vs_revenue_yoy.png and
outputs/tables/chart_data_yoy.csv (every plotted value).

Each panel shades the name's own pandemic exclusion window ("excluded: pandemic") and hatches the
following four quarters, whose YoY is not clean because the base year is excluded (hard rule 4).
Values outside the y-range are drawn at the edge with their value written next to them.
"""
import sys

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from nowcast import config  # noqa: E402
from nowcast.quarters import Quarter, qrange  # noqa: E402
from nowcast.rawstore import REPO_ROOT  # noqa: E402

CHARTS = REPO_ROOT / "outputs" / "charts"
TABLES = REPO_ROOT / "outputs" / "tables"
FIRST, LAST = Quarter(2020, 1), Quarter(2026, 3)
YLIM = (-100, 200)
INK, INK2, MUTED, GRID, SURFACE = "#0b0b0b", "#52514e", "#8a8984", "#e4e3df", "#fcfcfb"
C_REV, C_ALT = "#2a78d6", "#eb6834"          # categorical slots 1 and 2 (dataviz reference palette)
LABEL = {"tsa": "TSA throughput YoY", "wikipedia": "Wikipedia pageviews YoY", "caac": "CAAC passenger traffic YoY"}


def qx(q: Quarter) -> float:
    return q.year + (q.q - 1) / 4


def panel(ax, name, alt, rev, excl, source):
    ax.set_facecolor(SURFACE)
    e0, e1 = excl
    ax.axvspan(qx(e0) - 0.125, qx(e1) + 0.125, color="#d9d8d3", alpha=0.6, lw=0, zorder=0)
    ax.text(qx(e0) - 0.1, YLIM[0] + 6, "excluded: pandemic", fontsize=7.5, color=INK2, va="bottom")
    ax.axvspan(qx(e1 + 1) - 0.125, qx(e1 + 4) + 0.125, facecolor="none", edgecolor="#c9c8c2",
               hatch="///", lw=0, zorder=0)
    ax.text(qx(e1 + 1) - 0.1, YLIM[0] + 6, "YoY base excluded", fontsize=7, color=MUTED, va="bottom")
    ax.axhline(0, color=MUTED, lw=0.8, zorder=1)
    for df, col, lab in ((rev, C_REV, "Revenue YoY (first reported)"), (alt, C_ALT, LABEL[source])):
        x = [qx(Quarter.parse(q)) for q in df.quarter]
        y = df.pct.clip(*YLIM)
        ax.plot(x, y, color=col, lw=2, marker="o", ms=3.5, label=lab, zorder=3,
                markeredgecolor=SURFACE, markeredgewidth=0.8)
        for xi, v in zip(x, df.pct):
            if v > YLIM[1] or v < YLIM[0]:
                yy = YLIM[1] - 2 if v > YLIM[1] else YLIM[0] + 2
                ax.annotate(f"{v:+.0f}%", (xi, yy), xytext=(-14, 5 if v > YLIM[1] else -11),
                            textcoords="offset points", fontsize=6.5, color=INK2)
    ax.set_title(name, fontsize=10, color=INK, loc="left", fontweight="bold")
    ax.set_ylim(*YLIM)
    ax.set_xlim(qx(FIRST) - 0.2, qx(LAST) + 0.2)
    ax.set_xticks(range(2020, 2027))
    ax.grid(axis="y", color=GRID, lw=0.6)
    ax.tick_params(colors=INK2, labelsize=8, length=0)
    for sp in ax.spines.values():
        sp.set_visible(False)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%"))


def main():
    cos = config.companies()
    ft = pd.read_csv(REPO_ROOT / "data" / "processed" / "alt_features.csv")
    ft = ft[(ft.variant == "base") & (ft.checkpoint == "qend") & ft.alt.notna()]
    rev = pd.read_csv(TABLES / "revenue_yoy.csv")
    rev = rev[rev.status == "ok"]
    quarters = {str(q) for q in qrange(FIRST, LAST)}
    out_rows = []
    for source in ("tsa", "wikipedia", "caac"):
        names = sorted(ft.loc[ft.source == source, "name"].unique(), key=list(cos).index)
        ncols = 2 if len(names) > 1 else 1
        nrows = -(-len(names) // ncols)
        head_in = 1.35                                       # fixed header: title, subtitle, legend
        fig_w, fig_h = (12.4 if ncols == 2 else 9.0), 2.9 * nrows + head_in
        fig, axes = plt.subplots(nrows, ncols, figsize=(fig_w, fig_h), squeeze=False, facecolor=SURFACE)
        for ax, name in zip(axes.flat, names):
            a = ft[(ft.source == source) & (ft.name == name) & ft.quarter.isin(quarters)].sort_values("quarter")
            a = a.assign(pct=100 * a.alt)[["quarter", "pct"]]
            r = rev[(rev.name == name) & rev.quarter.isin(quarters)].sort_values("quarter")
            r = r.assign(pct=r.y_pct_first_reported)[["quarter", "pct"]]
            ew = cos[name]["exclusion_window"]
            panel(ax, name, a, r, (Quarter.parse(ew[0]), Quarter.parse(ew[1])), source)
            out_rows += [{"chart": source, "name": name, "series": "alt_yoy_qend", **x} for x in a.to_dict("records")]
            out_rows += [{"chart": source, "name": name, "series": "revenue_yoy_first_reported", **x}
                         for x in r.to_dict("records")]
        for ax in list(axes.flat)[len(names):]:
            ax.set_visible(False)
        h, lab = axes.flat[0].get_legend_handles_labels()
        title = f"{LABEL[source]} vs revenue YoY, 2020Q1–2026Q3"
        sub = ("Alt YoY = alt_q at the quarter-end checkpoint (only data published by quarter end; daily sources "
               "364-day aligned, CAAC published months only).\nRevenue YoY from 2022Q1 (Session 2 tables). "
               "Points beyond the axis are drawn at the edge, labelled with their value. "
               "Descriptive only: no statistic is computed here.")
        if source == "tsa":
            sub += " TSA is one national series, identical in every panel."
        top = lambda inches: 1 - inches / fig_h  # noqa: E731
        fig.text(0.01, top(0.12), title, fontsize=12, color=INK, fontweight="bold", va="top")
        fig.text(0.01, top(0.45), sub, fontsize=7.5, color=INK2, va="top", wrap=True)
        fig.legend(h, lab, loc="upper left", ncol=2, frameon=False, fontsize=8, bbox_to_anchor=(0.005, top(0.95)))
        fig.tight_layout(rect=(0, 0, 1, top(head_in)))
        fig.savefig(CHARTS / f"{source}_yoy_vs_revenue_yoy.png", dpi=150, facecolor=SURFACE)
        plt.close(fig)
    pd.DataFrame(out_rows).to_csv(TABLES / "chart_data_yoy.csv", index=False)


if __name__ == "__main__":
    main()
