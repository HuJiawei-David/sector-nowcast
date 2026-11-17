# Independent audit — Session 8 (2026-11-17)

Auditor: Claude Fable 5.2, a different model than the one that built the repo (Sessions 1–7). The repo was
treated as someone else's work. Every number below is produced by `scripts/s8_audit_*.py` and names its file
in `outputs/tables/`. Audited commit: f79f891.

## Verdict

- **No look-ahead found.** No headline number changed. The three public hashes are unchanged.
- **One fragility found and now disclosed:** a single TSA quarter (2024Q2) is a knife-edge call; one day less
  data flips it for all six U.S. names (section 1a).
- **One robustness bug fixed:** the live-call script read "the latest pull", so any later data refresh would
  have rewritten the publicly hashed `live_calls.csv` (section 6).
- **Four coach items:** three fixed, one pending because Trip.com has not filed (section 8).

## 1. Look-ahead

### 1a. Every as-of moved one day earlier

`scripts/s8_audit_lookahead.py` reruns the whole walk-forward backtest with every as-of date one day earlier
(the call's own as-of, and the quarter-end as-of of every past quarter used for the combined std and the
magnitude pairs). Files: `audit_asof_minus_1.csv` (call by call), `audit_asof_minus_1_cells.csv` (cell by cell).

| Check | Result |
|---|---|
| Calls compared | 1,165 |
| Momentum-baseline calls changed | 0 |
| Cells with a different N | 0 |
| Model calls changed | 14: the 2024Q2 TSA call (12 rows = 6 names × 2 targets) and the 2024Q2 UBER combined call in the Wikipedia earnings-window variant (2 rows) |
| Wikipedia, CAAC, base-variant combined calls changed | 0 |
| Largest magnitude change | yhat 0.6834 pp; cell MAE 0.0803 pp |
| Family cells with a different hit count | 12 of 39 (the 12 TSA cells, each by exactly one hit) |
| Cells crossing the minimum hit count | 0 |
| Cells changing GREEN status | 1 (LYFT TSA revenue) |

**Reading.** This is not a look-ahead. The 2024Q2 TSA value is d_alt = −0.0004 at the pre-registered
quarter-end as-of and +0.0001 one day earlier: the only difference is one fewer day of throughput. A call that
close to zero has no information. Its effect is not small, though: LYFT TSA revenue moves from 11 to 12 of 14
and its placebo percentile from 93.8 to 98.2, which would make it GREEN; EXPE TSA revenue moves from 10 to 9.
The pre-registered results stand (as-of = quarter end is the frozen spec), but the U.S. cells are that close to
the line. Disclosed in README Limitations and in the LYFT memo.

### 1b. As-of revenue selection on restated quarters

`audit_restated_quarters.csv`: 5 (name, quarter) pairs have more than one filed value, all Airbnb
(2021Q4, 2022Q1–Q4); the largest difference is $0.45m (later filings round to whole millions). 25 as-of checks,
one per restated quarter at each of the next five quarter ends: every one selects the latest version filed
strictly before the as-of. Example, ABNB 2022Q4: $1,901.55m (10-K filed 2023-02-17) is used at every as-of
through 2023-12-31; $1,902.00m (10-K filed 2024-02-16) first appears at as-of 2024-03-31. Trip.com has no
restated revenue quarter in its 6-K releases.

### 1c. CAAC publication dates

`audit_caac_publication.csv`: 65 CAAC months are used by some backtest or lead-time call. None is used before
its recorded publication date. Smallest gap: 0 days, once (January 2026, published 2026-02-25, first used by the
day-56 checkpoint of 2026Q1 on 2026-02-25). Rule 2 allows "on or before", and no quarter-end (headline) call
depends on a same-day publication. Not checkable from the repo: whether caac.gov.cn ever re-dated a bulletin
page (already listed as a limitation in Session 3).

## 2. Spec drift

- `git diff prereg..HEAD -- docs/hypotheses.md` is empty. SHA-256 unchanged (28056437…).
- "## Deviations" is empty, so there is no logged deviation to label.
- Analyses that exist but were **not** pre-registered, and how they are now labelled:

| Analysis | Where used | Label |
|---|---|---|
| TSA live call with 2025 shutdown / FAA-cut base days removed (`live_tsa_sensitivity.csv`) | six U.S. memos, sector memo | **fixed in S8:** "sensitivity, not pre-registered" added to each memo's source line (it already said "not a model change" in the CSV) |
| Trip.com small-moves table (`tcom_caac_small_moves.csv`, coach item 8c) | TCOM memo, README | "descriptive, not pre-registered" |
| As-of minus one day rerun (this audit) | README, LYFT memo | described as an audit check; pre-registered result stated to stand |
| Pandemic-era catch counts | separate chart only | already labelled "excluded from every result" |
| BKNG rounding check, Wikipedia revision check | data-quality notes | not results |

- **Open point for David and the coach (not changed).** Rule 1 says deviations are appended under
  "## Deviations", but the public hash covers the whole file, so the first appended deviation would change the
  posted SHA-256. If a deviation is ever needed, post a new hash alongside the old one and say why.

## 3. Traceability

`scripts/s8_audit_trace.py` → `audit_traceability.csv`, one row per number checked (13,080 rows):

| Document | Numbers checked | Unmatched |
|---|---|---|
| README.md, 8 memos, cv_bullets.md: plain numbers | 399 | 0 |
| Same documents: "H of N" and "H/N" pairs | 152 | 0 |
| Tracker workbook: numeric cells (Tracker, Lead time, Backtest sheets) | 12,505 | 0 |
| Tracker workbook: formulas (hit rate = hits / N, computed from matched cells) | 24 | – |

Method and its limit: a number with d decimals matches if some cell of the cited files (that name's rows for a
name memo) rounds to it; an "H of N" pair must equal a (hits, N) pair of that name. This is strict for decimals
(99.0, 93.8, 8.1, 0.43) and for pairs, but loose for bare small integers. So the headline claims are also
checked exactly, cell by cell, in `scripts/s8_audit_checks.py` → `audit_checks.csv` (25 checks, all PASS):
Trip.com CAAC 9 of 9, needed 8, momentum 3 of 9, placebo percentile 99.0, lead 8.1 weeks, BH q 0.43; 39 cells,
1.95 expected, 1 GREEN and which cell it is. `tests/test_deliverables.py` already checks every README matrix
cell against results.csv.

## 4. Independence and windows

All in `audit_checks.csv` and `audit_windows.csv`:

- Headline windows equal rule 4 for all 39 series: U.S. 2023Q2–2026Q3, TCOM 2024Q2–2026Q2, clean d only. The
  windows are written out independently in the audit script, not read from config.
- Robustness window U.S. 2024Q1–2026Q3; TCOM none.
- Fitting uses clean values only: the earliest magnitude pair and the earliest combined-std value are 2023Q2
  (U.S.) and 2024Q2 (TCOM).
- TSA: one identical call for all six names in each of the 28 (quarter, target) groups; `tsa_dependence.csv`
  has one row per quarter and target; no document quotes a hit rate pooled across names; every TSA row in
  results.csv carries the not-independent note.
- "Not run" cells are present: 44 direction cells, 5 not run with reasons (HKIA fallback not triggered; TCOM
  has no KPI). Excluded quarters are counted in every cell. The family is 39 cells.

## 5. Reproducibility

Fresh `git clone` into a temporary folder, new virtual environment, `pip install -r requirements.txt`, then
`bash scripts/run_all.sh`: exit 0 in about 3 minutes, `git status` clean (every committed table, chart and the
tracker reproduced byte for byte), pytest 97 passed and 1 skipped (the CLAUDE.md copy test; CLAUDE.md is
gitignored). Repeated after the Session 8 changes; result in STATUS.md.

## 6. Bugs fixed

| # | Bug | Fix | Headline number changed? |
|---|---|---|---|
| 1 | `scripts/s6_live.py` read the latest snapshot folder. Any later TSA / Wikipedia / CAAC pull followed by `run_all.sh` would have silently rewritten `live_calls.csv`, whose hash is public. | `config/pipeline.yaml` `live_snapshots` pins the 2026-11-17 pull; `features.live_snapshots()`; test. Output is byte-identical. | No |
| 2 | No test guarded two of the three public hashes. | `tests/test_live6.py::test_public_hashes_of_the_timestamped_files` checks all three. | No |
| 3 | The base-day sensitivity was used in memos without a "not pre-registered" label. | Label added to the source line of seven memos. | No |

No fix changed a result, so no result document needed a consistency update beyond the labels above.

## 7. Publishing (prepared, NOT run)

```bash
gh repo create HuJiawei-David/sector-nowcast --public --source . --push
```

To know before running it: the repo has no remote yet; `.env`, CLAUDE.md and STATUS.md are gitignored and
will not be published; no email address is in the tree or the history; the SEC request records keep the name
"Jiawei Hu" (email redacted); `data/raw` is 90 MB and `.git` 37 MB; public sources' pages are redistributed
as saved snapshots.

## 8. Coach review items (2026-11-17)

| Item | Status | What was done |
|---|---|---|
| a. Source for the 1 Oct start of the 2025 shutdown | Fixed | Official source found, so the window is unchanged and no sensitivity rerun was needed. Federal Register notice 2025-20331 (USMCA Secretariat, published 2025-11-19): "Due to a lapse in appropriations for the U.S. federal government, the United States Section of the USMCA Secretariat was closed from October 1, 2025, through November 12, 2025." Snapshot: `data/raw/federal_register/2026-11-17/doc_2025-20331_raw.txt` (pulled by `scripts/s8_pull.py`). `config/guidance.yaml` now cites it (`start_quote`, `start_snapshot`, `start_source_url`); the reference to a brief is gone; two tests check the quote against the snapshot and that no event cites a brief. The fields that feed `live_calls.csv` were not touched. |
| b. CV bullet 2 | Fixed | Now states "not significant after multiple-testing correction (BH q = 0.43)" (results.csv, `bh_q_placebo`, TCOM caac y); 29 words. |
| c. Trip.com small moves | Fixed | `tcom_caac_small_moves.csv`, produced by `scripts/s8_audit_checks.py` from calls.csv. 3 of the 9 hits were on very small moves: 2025Q2 (d_y +0.05 pp) and 2025Q3 (d_y −0.69 pp) have \|d_y\| < 1 pp; 2024Q3 has \|d_alt\| < 0.01. Added to the TCOM memo and README Limitations, labelled "descriptive, not pre-registered". |
| d. Score the locked TCOM 2026Q3 call | **Pending** | EDGAR submissions for CIK 1269238 pulled 2026-11-17 (`data/raw/sec_submissions_s8/2026-11-17/`): the latest 6-Ks are the two of 2026-09-16; the only later filing is a Schedule 13G/A (2026-11-13). No Q3 2026 results 6-K, so nothing was scored and `live_calls_scored.csv` was not created. `live_calls.csv` and `live_calls_tcom_2026Q3.csv` were not edited. TCOM memo and README say "pending". |

## 9. Things an interviewer could still push on (not bugs)

- The one GREEN cell rests on 9 quarters, 3 of them tiny moves, and is not significant after correction.
- The U.S. TSA cells move by one hit on a one-day change of as-of (section 1a).
- The 39-cell family counts the six TSA cells per target as six tests although they share one call series; the
  chance benchmark of 1.95 is therefore approximate. The documents say so.
- Wikipedia pageviews are not available as point-in-time vintages; Wikimedia revised recent days between pulls.
- The pooled TSA beta (used only while a name has fewer than 4 pairs) pools six names with identical x values,
  as the spec says; it affects the secondary magnitude model only.
