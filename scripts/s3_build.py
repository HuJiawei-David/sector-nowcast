"""Session 3: alt-data series, validations and features from snapshots (no network).

    .venv/bin/python scripts/s3_build.py

Outputs
  data/processed/tsa_daily.csv            TSA national daily throughput (parsed CSV) + publication date
  data/processed/wikipedia_daily.csv      per-name daily pageviews summed over all titles + per-title columns
  data/processed/caac_monthly.csv         CAAC monthly passenger traffic, recorded release dates, URLs
  data/processed/alt_features.csv         alt_q / d_alt_q per (name, source, variant, quarter, checkpoint)
  outputs/tables/alt_validation.csv       rule-9 checks per series
  outputs/tables/caac_yoy_check.csv       CAAC level-based YoY vs the YoY % stated in the bulletin
"""
import datetime as dt
import sys

import pandas as pd

sys.path.insert(0, "src")
from nowcast import config, features as F, wiki  # noqa: E402
from nowcast.quarters import Quarter  # noqa: E402
from nowcast.rawstore import REPO_ROOT  # noqa: E402

PROC = REPO_ROOT / "data" / "processed"
TABLES = REPO_ROOT / "outputs" / "tables"


def main():
    pipe = config.load_yaml("pipeline.yaml")
    series = F.load_series()
    run_date = F.data_run_date(series)
    print("run date (live as-of):", run_date)

    val = pd.DataFrame([F.validate_series(s) for s in series.values()])
    val.to_csv(TABLES / "alt_validation.csv", index=False)
    print(val.to_string(index=False))

    series["tsa"].obs.to_csv(PROC / "tsa_daily.csv", index=False)
    tv = wiki.load_title_views()
    per_title = tv.pivot_table(index=["name", "date"], columns="title", values="views").reset_index()
    wd = pd.concat([s.obs.assign(name=k.split(":")[1]) for k, s in series.items() if k.startswith("wikipedia:")])
    wd = wd.merge(per_title.rename(columns={"date": "obs_date"}), on=["name", "obs_date"], how="left")
    wd.to_csv(PROC / "wikipedia_daily.csv", index=False)
    c = series["caac"].meta["table"]
    c.to_csv(PROC / "caac_monthly.csv", index=False)

    # CAAC: stated Y/Y (bulletin, vs revised prior-year) vs level-based Y/Y (prior-year flash level)
    c2 = c.set_index("obs_date")
    chk = []
    for d, r in c2.iterrows():
        b = d.replace(year=d.year - 1)
        if b in c2.index:
            chk.append({"month": r.month, "level": r.value, "level_prior_year": c2.loc[b, "value"],
                        "yoy_from_levels_pct": 100 * (r.value / c2.loc[b, "value"] - 1),
                        "yoy_stated_pct": r.yoy_stated_pct})
    chk = pd.DataFrame(chk)
    chk["diff_pp"] = chk.yoy_from_levels_pct - chk.yoy_stated_pct
    chk.to_csv(TABLES / "caac_yoy_check.csv", index=False)

    rel = pd.read_csv(PROC / "earnings_releases.csv")
    ft = F.build_feature_table(series, rel, Quarter.parse("2020Q1"), Quarter(run_date.year, (run_date.month - 1) // 3 + 1),
                               run_date, dt.date.fromisoformat(pipe["releases_since"]))
    ft.to_csv(PROC / "alt_features.csv", index=False)
    print(ft.groupby(["source", "variant", "checkpoint", "status"]).size().to_string())


if __name__ == "__main__":
    main()
