"""Session 8 audit, items 4 and 8c, plus strict checks of the headline claims. No network.

    .venv/bin/python scripts/s8_audit_checks.py

outputs/tables/audit_windows.csv          per (name, target): headline / robustness quarters in calls.csv vs hard rule 4
outputs/tables/audit_checks.csv           one row per check (PASS / FAIL) : windows, clean fitting, TSA dependence,
                                          "not run" cells, multiple-testing family, headline claims in the documents
outputs/tables/tcom_caac_small_moves.csv  coach item 8c (descriptive, not pre-registered): the 9 headline quarters of
                                          the TCOM CAAC y cell with |d_y| and |d_alt| and flags for very small moves
"""
import re
import sys

import pandas as pd

sys.path.insert(0, "src")
from nowcast import config  # noqa: E402
from nowcast.quarters import Quarter, d_clean, qrange  # noqa: E402
from nowcast.rawstore import REPO_ROOT  # noqa: E402

T = REPO_ROOT / "outputs" / "tables"
SMALL_D_Y_PP, SMALL_D_ALT = 1.0, 0.01            # thresholds fixed by the coach review (2026-11-17)
# hard rule 4 / hypotheses 3.5, written out independently of config/companies.yaml
RULE4 = {"US": {"excl": ("2020Q1", "2021Q4"), "head": ("2023Q2", "2026Q3"), "rob": ("2024Q1", "2026Q3")},
         "TCOM": {"excl": ("2020Q1", "2022Q4"), "head": ("2024Q2", "2026Q2"), "rob": None}}
checks = []


def check(name: str, ok: bool, detail: str) -> None:
    checks.append({"check": name, "result": "PASS" if ok else "FAIL", "detail": detail})


def small_moves(calls: pd.DataFrame) -> pd.DataFrame:
    c = calls[(calls.name == "TCOM") & (calls.source == "caac") & (calls.target == "y") & (calls.variant == "base")
              & (calls.checkpoint == "qend") & calls.in_headline].sort_values("quarter")
    out = c[["quarter", "asof", "d_alt", "prediction", "t_q_minus_1_first_pct", "t_q_first_pct", "d_t_actual_pp",
             "actual", "correct"]].copy()
    out["correct"] = out.correct.astype(bool)
    out["abs_d_y_pp"] = out.d_t_actual_pp.abs()
    out["abs_d_alt"] = out.d_alt.abs()
    out["small_d_y"] = out.abs_d_y_pp < SMALL_D_Y_PP
    out["small_d_alt"] = out.abs_d_alt < SMALL_D_ALT
    out["small_either"] = out.small_d_y | out.small_d_alt
    out["label"] = "descriptive, not pre-registered"
    return out


def main() -> None:
    calls = pd.read_csv(T / "calls.csv")
    res = pd.read_csv(T / "results.csv")
    rob = pd.read_csv(T / "robustness.csv")
    cos = config.companies()
    base = calls[(calls.variant == "base") & (calls.checkpoint == "qend")]

    # ---- windows (rule 4)
    rows = []
    for name, co in cos.items():
        r4 = RULE4["TCOM" if name == "TCOM" else "US"]
        excl = tuple(Quarter.parse(x) for x in r4["excl"])
        exp_head = [str(q) for q in qrange(*(Quarter.parse(x) for x in r4["head"])) if d_clean(q, excl)]
        exp_rob = [str(q) for q in qrange(*(Quarter.parse(x) for x in r4["rob"])) if d_clean(q, excl)] if r4["rob"] else []
        for target in sorted(base[base.name == name].target.unique()):
            g = base[(base.name == name) & (base.target == target)]
            for src in sorted(g.source.unique()):
                s = g[g.source == src]
                got_h, got_r = sorted(s[s.in_headline].quarter), sorted(s[s.in_robustness_window].quarter)
                rows.append({"name": name, "target": target, "source": src, "headline_quarters": ",".join(got_h),
                             "headline_matches_rule4": got_h == exp_head, "robustness_quarters": ",".join(got_r),
                             "robustness_matches_rule4": got_r == exp_rob,
                             "clean_flag_matches_rule4": bool((s.clean == s.quarter.map(
                                 lambda q: d_clean(Quarter.parse(q), excl))).all())})
    w = pd.DataFrame(rows)
    w.to_csv(T / "audit_windows.csv", index=False)
    check("headline windows = rule 4 (US 2023Q2-2026Q3, TCOM 2024Q2-2026Q2, clean d only)",
          bool(w.headline_matches_rule4.all()), f"{len(w)} (name, target, source) series checked")
    check("robustness window = rule 4 (US 2024Q1-2026Q3; TCOM none)", bool(w.robustness_matches_rule4.all()), "")
    check("clean flag = rule 4 exclusion windows (US 2020Q1-2021Q4, TCOM 2020Q1-2022Q4)",
          bool(w.clean_flag_matches_rule4.all()), "")

    # ---- every scored quarter of every headline cell lies inside the headline window
    d = res[(res.model == "direction") & (res.N_realised > 0)]
    bad = []
    for _, r in d.iterrows():
        hw = w[(w.name == r["name"]) & (w.target == r.target) & (w.source == r.source)].headline_quarters.iloc[0].split(",")
        bad += [q for q in str(r.quarters_scored).split(",") if q not in hw]
    check("scored quarters of every headline cell are inside the headline window", not bad, f"{len(d)} cells")

    # ---- fitting on clean values only: every magnitude pair range starts at the first clean quarter or later
    m = base[base.pair_quarters.notna() & (base.pair_quarters != "")]
    first_pair = m.pair_quarters.str.split("..", regex=False).str[0]
    first_clean = {"US": "2023Q2", "TCOM": "2024Q2"}
    okp = all(fp >= (first_clean["TCOM"] if (n == "TCOM" and b == "name") else first_clean["US"])
              for fp, n, b in zip(first_pair, m.name, m.beta_basis))
    check("magnitude fitting pairs start at the first clean quarter or later (pooled Wikipedia may use US pairs)",
          okp, f"{len(m)} calls with a fitted beta; earliest pair quarter {first_pair.min()}")
    comb = base[(base.source == "combined") & (base.status == "ok")]
    starts = set(re.findall(r"\((?:n=\d+, )(\d{4}Q\d)\.\.", " ".join(comb.combined_detail)))
    check("combined std uses clean d_alt values only", starts <= {"2023Q2", "2024Q2"}, f"std windows start at {sorted(starts)}")

    # ---- TSA dependence
    t = base[(base.source == "tsa") & base.in_headline]
    per_q = t.groupby(["quarter", "target"]).agg(n_calls=("prediction", "nunique"), n_dalt=("d_alt", "nunique"))
    check("TSA: one identical call for all six US names in every quarter", bool((per_q.n_calls == 1).all() and (per_q.n_dalt == 1).all()),
          f"{len(per_q)} (quarter, target) groups")
    td = pd.read_csv(T / "tsa_dependence.csv")
    check("tsa_dependence.csv counts each quarter once (one row per quarter and target)",
          not td.duplicated(["quarter", "target"]).any() and len(td) == 28, f"{len(td)} rows = 14 quarters x 2 targets")
    docs = {p: (REPO_ROOT / p).read_text() for p in ["README.md", "docs/cv_bullets.md", "docs/case_framework.md",
                                                       "docs/presentation_script.md"]
            + [f"outputs/memos/{n}.md" for n in list(cos) + ["SECTOR"]]}
    pooled_n = {84, 168, 82, 80}                 # 6 x 14 (or with LYFT k 12): a pooled-across-names TSA denominator
    hits = [(p, m_.group(0)) for p, txt in docs.items() for m_ in re.finditer(r"\b(\d+) (?:of|/) ?(\d+)\b", txt)
            if int(m_.group(2)) in pooled_n]
    check("no document quotes a TSA hit rate pooled across names (denominators 80/82/84/168)", not hits, str(hits))
    check("every TSA results row carries the not-independent note", bool(res[res.source == "tsa"].tsa_note.str.contains("not independent").all()), "")

    # ---- not-run cells present (rule 5)
    cells = res[res.model == "direction"]
    exp_cells = 6 * 3 * 2 + 4 * 2                # six US names x 3 sources x {y,k}; TCOM x {caac,hkia,wikipedia,combined} x {y,k}
    check("results.csv has every (name, source, target) direction cell incl. not-run ones", len(cells) == exp_cells,
          f"{len(cells)} direction cells, {int((cells.N_realised == 0).sum())} not run: "
          + "; ".join(sorted(set(cells[cells.N_realised == 0].status))))
    check("HKIA and TCOM k cells are present as 'not run' with a reason",
          bool(cells[(cells.source == "hkia") | ((cells.name == "TCOM") & (cells.target == "k"))].status.str.startswith("not run").all()), "")
    check("every not-run / excluded quarter is counted (n_excluded_same_sample + N = window length)",
          bool(all(int(r.N_realised + r.n_excluded_same_sample) == len(
              w[(w.name == r["name"]) & (w.target == r.target) & (w.source == r.source)].headline_quarters.iloc[0].split(","))
              for _, r in d.iterrows() if r.source != "combined")), "single-source headline cells")
    check("multiple-testing family = 39 cells", int(res.family_member.sum()) == 39, "")
    check("robustness.csv has the same cells for each of the 3 robustness analyses", bool((rob.groupby("analysis").size() == len(res)).all()),
          str(rob.groupby("analysis").size().to_dict()))

    # ---- strict checks of the headline claims
    def cell(n, s, t_, model="direction"):
        return res[(res.name == n) & (res.source == s) & (res.target == t_) & (res.model == model)].iloc[0]
    tc = cell("TCOM", "caac", "y")
    mt = pd.read_csv(T / "multiple_testing.csv").iloc[0]
    lt = pd.read_csv(T / "lead_time.csv")
    ltq = lt[(lt.name == "TCOM") & (lt.source == "caac") & (lt.checkpoint == "qend")].iloc[0]
    claim = (f"9 of 9" if (tc.hits, tc.N_realised) == (9, 9) else "?")
    for p in ("README.md", "outputs/memos/TCOM.md", "outputs/memos/SECTOR.md", "docs/cv_bullets.md"):
        check(f"{p}: TCOM CAAC y '9 of 9' = results.csv hits/N", claim in docs[p] and (tc.hits, tc.N_realised) == (9, 9), "")
    for p in ("README.md", "outputs/memos/TCOM.md"):
        txt = docs[p]
        check(f"{p}: need {int(tc.min_hits_p05_realised)}, momentum {int(tc.momentum_hits)} of 9, placebo {tc.placebo_percentile:.1f}, "
              f"lead {ltq.median_weeks_to_release:.1f} weeks, BH q {tc.bh_q_placebo:.2f}",
              all(x in txt for x in (f"≥ {int(tc.min_hits_p05_realised)}", f"momentum {int(tc.momentum_hits)} of 9",
                                     f"{tc.placebo_percentile:.1f}", f"{ltq.median_weeks_to_release:.1f} weeks",
                                     f"{tc.bh_q_placebo:.2f}")), "")
    check("README: '1.95 would pass by chance', 39 cells, 1 GREEN = multiple_testing.csv",
          (mt.direction_cells_tested, mt.green_found) == (39, 1) and f"{mt.expected_to_pass_by_chance:.2f}" in docs["README.md"], "")
    check("only GREEN cell is TCOM caac y", list(res[res.green == True][["name", "source", "target"]].itertuples(index=False, name=None))  # noqa: E712
          == [("TCOM", "caac", "y")], "")
    cv = docs["docs/cv_bullets.md"].splitlines()
    b2 = [x for x in cv if x.startswith("- ")][1]
    check("cv_bullets bullet 2 states the BH q-value from results.csv and is under 30 words",
          f"{tc.bh_q_placebo:.2f}" in b2 and len(b2[2:].split()) < 30, f"{len(b2[2:].split())} words: {b2[2:]}")

    sm = small_moves(calls)
    sm.to_csv(T / "tcom_caac_small_moves.csv", index=False, float_format="%.6f")
    check("TCOM CAAC y small-moves table has the 9 headline quarters, all hits", len(sm) == 9 and bool(sm.correct.all()), "")

    out = pd.DataFrame(checks)
    out.to_csv(T / "audit_checks.csv", index=False)
    pd.set_option("display.width", 250, "display.max_colwidth", 150)
    print(out.to_string(index=False))
    print(sm[["quarter", "d_alt", "d_t_actual_pp", "correct", "small_d_y", "small_d_alt", "small_either"]].to_string(index=False))
    print(f"small |d_y| < {SMALL_D_Y_PP} pp: {int(sm.small_d_y.sum())}; small |d_alt| < {SMALL_D_ALT}: {int(sm.small_d_alt.sum())}; "
          f"either: {int(sm.small_either.sum())} of {len(sm)}")
    if (out.result == "FAIL").any():
        raise SystemExit("audit checks FAILED")


if __name__ == "__main__":
    main()
