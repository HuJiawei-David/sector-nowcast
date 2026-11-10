"""Session 2: build revenue / KPI point-in-time tables from raw snapshots (no network).

    .venv/bin/python scripts/s2_build.py

Outputs
  data/processed/earnings_releases.csv   one row per earnings release (8-K Item 2.02 / 6-K results)
  data/processed/revenue_pit.csv         every filed version of quarterly revenue
  data/processed/kpi_pit.csv             every KPI number (levels + stated Y/Y %) read from releases
  data/processed/release_values.csv      every number read from releases (KPI and revenue)
  outputs/tables/revenue_yoy.csv         revenue YoY 2022Q1-2026Q3 per name with CLEAN flags
  outputs/tables/kpi_yoy.csv             KPI YoY per name with CLEAN flags
  outputs/tables/fy_sum_check.csv        Q1+Q2+Q3+Q4 vs FY (rule 9)
  outputs/tables/reconciliation.csv      known-answer reconciliation (task 6b)
  data/nowcast.db                        SQLite tables (sql/schema.sql)
"""
import datetime as dt
import sqlite3
import sys

import pandas as pd

sys.path.insert(0, "src")
from nowcast import config, kpi as K, reconcile, releases as R, revenue as RV, validate as V  # noqa: E402
from nowcast.quarters import Quarter, d_clean, qrange, yoy_clean  # noqa: E402
from nowcast.rawstore import REPO_ROOT  # noqa: E402

PROC = REPO_ROOT / "data" / "processed"
TABLES = REPO_ROOT / "outputs" / "tables"
DB = REPO_ROOT / "data" / "nowcast.db"


def build():
    pipe = config.load_yaml("pipeline.yaml")
    ext = config.load_yaml("extraction.yaml")["companies"]
    notes = config.load_yaml("reconciliation_notes.yaml")
    cos = config.companies()
    since = dt.date.fromisoformat(pipe["releases_since"])
    first_data = Quarter.parse(pipe["data_first_quarter"])
    first_kpi = Quarter.parse(pipe["kpi_first_quarter"])
    rep_first, rep_last = Quarter.parse(pipe["report_first_quarter"]), Quarter.parse(pipe["report_last_quarter"])

    # ---------------------------------------------------------------- releases + values
    rel_rows, val_rows = [], []
    for name, co in cos.items():
        rels = R.release_table(name, co, since, pipe["tcom_results_release_regex"])
        for r in rels:
            rel_rows.append({"name": name, "quarter": str(r.quarter), "filed": r.filed, "accession": r.accession,
                             "form": r.form, "is_amendment": int(r.form.endswith("/A")), "document": r.document,
                             "source_url": r.url})
            rows, missing = R.extract(r, ext[name])
            if missing:
                raise R.ExtractionError(f"{name} {r.quarter} {r.accession}: required extractor(s) {missing} "
                                        f"did not match ({r.url})")
            val_rows += rows
    releases = pd.DataFrame(rel_rows).sort_values(["name", "quarter", "filed"]).reset_index(drop=True)
    values = K.dedupe(pd.DataFrame(val_rows))

    # ---------------------------------------------------------------- revenue versions
    vers = []
    for name, co in cos.items():
        if co["revenue"]["source"] == "xbrl":
            vers.append(RV.us_revenue_versions(name, co, pipe["xbrl"], first_data))
        else:
            vers.append(RV.release_revenue_versions(values, name, co["revenue"]["currency"]))
    rev = pd.concat(vers, ignore_index=True)
    rev = rev[rev["quarter"].map(Quarter.parse) >= first_data].reset_index(drop=True)

    # ---------------------------------------------------------------- validations (rule 9)
    last_release, last_rev = {}, {}
    V.no_duplicates(releases, ["name", "accession"], "earnings releases")
    V.no_duplicates(rev, ["name", "quarter", "accession"], "revenue versions")
    V.no_duplicates(values, K.KEY, "release values")
    V.consistent_across_releases(values, notes.get("restatements", []))
    fy_rows = []
    annual = {}
    for name, co in cos.items():
        last_release[name] = V.releases_complete(releases, name, first_kpi)
        rq = rev.loc[rev["name"] == name, "quarter"]
        last_rev[name] = max(rq.map(Quarter.parse))
        V.no_missing_quarters(rq, first_data, last_rev[name], f"{name} revenue")
        if co.get("kpi"):
            kq = values[(values["name"] == name) & (values["metric"] == "kpi") & (values["kind"] == "value")]
            V.no_missing_quarters(kq["quarter"], first_kpi, last_release[name], f"{name} KPI values")
        if co["revenue"]["source"] == "xbrl":
            ann = RV.annual_facts(name, co, co["revenue"]["xbrl_tags"], co["revenue"]["currency"], pipe["xbrl"])
        else:
            ann = RV.annual_facts(name, co, co["revenue"]["annual_check_xbrl_tags"], "CNY", pipe["xbrl"])
        annual[name] = ann
        latest = RV.asof_view(rev[rev["name"] == name], dt.date.today() + dt.timedelta(days=1))
        years = list(range(first_data.year, last_rev[name].year + 1))
        fy_rows += V.fy_sums(latest, ann, name, years, pipe["fy_sum_tolerance"])

    # ---------------------------------------------------------------- YoY tables
    yrows, krows = [], []
    for name, co in cos.items():
        excl = config.window(co["exclusion_window"])
        for q in qrange(rep_first, rep_last):
            base = {"name": name, "quarter": str(q), "yoy_clean": yoy_clean(q, excl), "d_clean": d_clean(q, excl)}
            if co["revenue"]["source"] == "xbrl":
                f = RV.yoy_same_filing(rev, name, q, "first")
                lt = RV.yoy_same_filing(rev, name, q, "asof", asof=dt.date.today() + dt.timedelta(days=1))
            else:
                f = K.yoy_same_release(values, name, q, "revenue", "first")
                lt = K.yoy_same_release(values, name, q, "revenue", "asof", asof=dt.date.today() + dt.timedelta(days=1))
            if f is None:
                status = "not yet reported" if q > last_rev[name] else "not run (no like-for-like base)"
                yrows.append({**base, "status": status})
            else:
                yrows.append({**base, "status": "ok", "revenue": f["value"], "revenue_q_minus_4": f["base_value"],
                              "y_pct_first_reported": f["yoy_pct"], "filed": f["filed"], "accession": f["accession"],
                              "y_pct_latest": lt["yoy_pct"], "latest_accession": lt["accession"],
                              "source_url": f["source_url"]})
            if co.get("kpi"):
                k = K.yoy_same_release(values, name, q, "kpi", "first")
                if k is None:
                    status = "not yet reported" if q > last_release[name] else "not run (no like-for-like base)"
                    krows.append({**base, "kpi": co["kpi"]["name"], "status": status})
                else:
                    krows.append({**base, "kpi": co["kpi"]["name"], "status": "ok", "kpi_value": k["value"],
                                  "kpi_q_minus_4": k["base_value"], "k_pct_first_reported": k["yoy_pct"],
                                  "yoy_basis": k["yoy_basis"], "release_quarter": k["release_quarter"],
                                  "filed": k["filed"], "accession": k["accession"], "source_url": k["source_url"]})
    ytab, ktab = pd.DataFrame(yrows), pd.DataFrame(krows)

    # ---------------------------------------------------------------- reconciliation
    rec_last = {n: min(rep_last, last_release[n], last_rev[n]) for n in cos}
    rec = reconcile.run(list(cos), cos, rev, values, annual, rep_first, rec_last, notes)

    # ---------------------------------------------------------------- write
    PROC.mkdir(parents=True, exist_ok=True)
    TABLES.mkdir(parents=True, exist_ok=True)
    releases.to_csv(PROC / "earnings_releases.csv", index=False)
    rev.to_csv(PROC / "revenue_pit.csv", index=False, float_format="%.6g")
    vcols = ["name", "metric", "kind", "quarter", "value", "unit", "decimals", "precision", "role",
             "release_quarter", "filed", "accession", "form", "extractors", "source_url", "snippet"]
    values[vcols].to_csv(PROC / "release_values.csv", index=False, float_format="%.6g")
    kp = values[values["metric"] == "kpi"].copy()
    kp.insert(1, "kpi", kp["name"].map(lambda n: cos[n]["kpi"]["name"]))
    kp[["name", "kpi"] + vcols[2:]].to_csv(PROC / "kpi_pit.csv", index=False, float_format="%.6g")
    ytab.to_csv(TABLES / "revenue_yoy.csv", index=False, float_format="%.4f")
    ktab.to_csv(TABLES / "kpi_yoy.csv", index=False, float_format="%.4f")
    pd.DataFrame(fy_rows).to_csv(TABLES / "fy_sum_check.csv", index=False, float_format="%.6g")
    rec.to_csv(TABLES / "reconciliation.csv", index=False, float_format="%.4f")
    write_db(cos, releases, rev, values, rec)
    return dict(releases=releases, values=values, rev=rev, ytab=ytab, ktab=ktab, rec=rec, fy=pd.DataFrame(fy_rows),
                last_release=last_release, last_rev=last_rev)


def write_db(cos, releases, rev, values, rec):
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(DB)
    con.executescript((REPO_ROOT / "sql" / "schema.sql").read_text())
    comp = pd.DataFrame([{"name": n, "legal_name": c["name"], "cik": c["cik"], "region": c["region"],
                          "revenue_source": c["revenue"]["source"], "currency": c["revenue"]["currency"],
                          "kpi_name": (c.get("kpi") or {}).get("name")} for n, c in cos.items()])
    comp.to_sql("companies", con, if_exists="append", index=False)
    releases.assign(filed=releases["filed"].astype(str)).to_sql("earnings_releases", con, if_exists="append", index=False)
    rc = ["name", "quarter", "value", "unit", "currency", "period_start", "period_end", "fy", "fp", "form", "filed",
          "accession", "tag", "method", "derivation", "source_url"]
    r2 = rev[rc].copy()
    for c in ("filed", "period_start", "period_end"):
        r2[c] = r2[c].map(lambda d: None if d is None or pd.isna(d) else str(d))
    r2.to_sql("revenue_versions", con, if_exists="append", index=False)
    v = values.rename(columns={"precision": "value_precision"})
    v = v[["name", "metric", "kind", "quarter", "value", "unit", "decimals", "value_precision", "role",
           "release_quarter", "filed", "accession", "form", "extractors", "source_url"]].copy()
    v["filed"] = v["filed"].astype(str)
    v.to_sql("release_values", con, if_exists="append", index=False)
    rec.rename(columns={"check": "check_name"}).to_sql("reconciliation", con, if_exists="append", index=False)
    con.commit()
    con.close()


if __name__ == "__main__":
    out = build()
    print("built:", {k: len(v) for k, v in out.items() if hasattr(v, "__len__") and not isinstance(v, dict)})
