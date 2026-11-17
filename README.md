# Sector Nowcast: alt-data direction calls for online travel & mobility

Can free public data (U.S. airport security throughput, China's monthly air-passenger statistics,
English Wikipedia pageviews) tell, before the print, whether revenue or KPI growth will speed up or slow
down at BKNG, EXPE, ABNB, UBER, LYFT, DASH and TCOM? The plan was frozen and hashed before any of these
data were downloaded; every number below is produced by code in this repo and names its file.

## Findings

**One of 39 pre-registered cells is GREEN; 1.95 would pass by chance.** CAAC called the direction of
Trip.com's revenue right in 9 of 9 quarters at quarter end (needed ≥ 8; momentum 3 of 9; shuffle-placebo
percentile 99.0), about 8.1 weeks before the print. No cell has a Benjamini-Hochberg q-value below 0.05
(smallest 0.43). For the six U.S. names there is no detectable signal at this sample size.
(outputs/tables/multiple_testing.csv, results.csv, lead_time.csv)

**Relevancy matrix**: headline windows, call at quarter end. Cell = hits/N (hits needed for one-sided
binomial p < 0.05; momentum baseline on the same quarters; shuffle-placebo percentile). GREEN = beats
both baselines AND placebo percentile ≥ 95. Full text: outputs/tables/relevancy_matrix.csv.

| Name | Target | Volume source (TSA / CAAC) | Wikipedia | Combined |
|---|---|---|---|---|
| BKNG | revenue | 8/14 (11; 7; 23) | 5/14 (11; 7; 3) | 4/11 (9; 5; 0) |
| BKNG | room nights | 8/14 (11; 7; 51) | 7/14 (11; 7; 31) | 5/11 (9; 6; 17) |
| EXPE | revenue | 10/14 (11; 7; 90) | 7/14 (11; 7; 29) | 7/11 (9; 6; 60) |
| EXPE | booked room nights | 9/14 (11; 4; 62) | 8/14 (11; 4; 52) | 7/11 (9; 4; 61) |
| ABNB | revenue | 7/14 (11; 5; 16) | 6/14 (11; 5; 16) | 5/11 (9; 2; 17) |
| ABNB | nights & seats booked | 9/14 (11; 7; 62) | 10/14 (11; 7; 88) | 8/11 (9; 6; 81) |
| UBER | revenue | 8/14 (11; 8; 21) | 9/14 (11; 8; 78) | 8/11 (9; 6; 68) |
| UBER | trips | 9/14 (11; 7; 60) | 10/14 (11; 7; 87) | 7/11 (9; 7; 55) |
| LYFT | revenue | 11/14 (11; 6; 93) | 8/14 (11; 6; 52) | 7/11 (9; 5; 53) |
| LYFT | rides | 7/12 (10; 3; 28) | 7/12 (10; 3; 49) | 6/11 (9; 2; 21) |
| DASH | revenue | 8/14 (11; 8; 22) | 7/14 (11; 8; 26) | 5/11 (9; 5; 13) |
| DASH | total orders | 7/14 (11; 8; 14) | 8/14 (11; 8; 46) | 6/11 (9; 6; 42) |
| TCOM | revenue | **CAAC 9/9 (8; 3; 99) GREEN** | 3/9 (8; 3; 0) | 5/6 (6; 1; 65) |

Multiple testing: 39 direction cells tested; 1.95 expected to pass by chance; GREEN found: 1 (TCOM CAAC
revenue). The six TSA cells per target share one call series (identical for all U.S. names each
quarter), so they are not independent tests. HKIA cells: not run (fallback not triggered); TCOM has no
volume KPI. (outputs/tables/multiple_testing.csv, docs/decisions_log.md)

**Live calls** (outputs/tables/live_calls.csv; as-of 2026-11-16 for 2026Q4, 2026-11-10 for the locked
TCOM 2026Q3 call). Guidance label from the company's own latest release (config/guidance.yaml);
companies tend to guide conservatively, so "above guidance" is the common case.

| Name | Quarter | Volume source | Wikipedia | Combined | Guided direction (metric) | Volume-source read |
|---|---|---|---|---|---|---|
| BKNG | 2026Q4 | TSA accelerate | accelerate | accelerate | decelerate (room nights; Adjusted Revenue) | above guidance |
| EXPE | 2026Q4 | TSA accelerate | decelerate | decelerate | decelerate (revenue) | above guidance |
| ABNB | 2026Q4 | TSA accelerate | accelerate | accelerate | decelerate (revenue) | above guidance |
| UBER | 2026Q4 | TSA accelerate | decelerate | accelerate | no change (Gross Bookings) | no label |
| LYFT | 2026Q4 | TSA accelerate | decelerate | decelerate | decelerate (Gross Bookings) | above guidance |
| DASH | 2026Q4 | TSA accelerate | decelerate | accelerate | decelerate (Marketplace GOV) | above guidance |
| TCOM | 2026Q4 | CAAC insufficient data | accelerate | insufficient data | pending | – |
| TCOM | 2026Q3 (locked) | CAAC accelerate | accelerate | accelerate | no guidance | score pending (no Q3 6-K on EDGAR, 2026-11-17) |

Memos: outputs/memos/<TICKER>.md and outputs/memos/SECTOR.md. Tracker: outputs/tracker/sector_nowcast_tracker.xlsx.

## Method

- **Targets.** y = revenue YoY growth (SEC XBRL; Trip.com from 6-K results releases, RMB); k = headline
  KPI YoY growth from earnings releases (room nights, booked room nights, nights and seats booked, trips,
  rides, total orders). Each YoY is like-for-like from one filing (docs/hypotheses.md §3.11).
- **Feature.** alt_q = YoY growth of the source over the quarter (to date), each day against the same
  weekday 364 days earlier; d_alt = alt_q − alt_q−1 at the same as-of date. CAAC uses only months already
  published. Combined source = sign of the sum of d_alt / std over sources.
- **Call and scoring.** Accelerate if d_alt > 0, decelerate if < 0, scored against the sign of the
  change in first-reported growth. Baselines: momentum (last quarter's direction) and 50%, on the same
  quarters. Magnitude: yhat = y_q−1 + beta × d_alt, beta by expanding OLS through the origin, vs y_q−1.
- **Point in time.** A call at date T uses only alt data published by T (daily: observation + 1 day; CAAC:
  the release date recorded from each bulletin page) and filings filed before T. Backtest as-of = quarter
  end; lead time also at day 28 and day 56.
- **Significance.** 1,000-run shuffle placebo per cell (primary), wrong-company placebo for Wikipedia,
  binomial p for reference, Benjamini-Hochberg over the 39-cell family.
- **Windows.** Headline U.S. 2023Q2–2026Q3, TCOM 2024Q2–2026Q2; pandemic-affected YoY values excluded
  (U.S. 2020Q1–2021Q4, TCOM 2020Q1–2022Q4); robustness: U.S. 2024Q1–2026Q3, structural-break quarters
  removed, Wikipedia without the 7 days after each earnings release (outputs/tables/robustness.csv).

**Pre-registration.** docs/hypotheses.md (series, models, metrics, windows, a prediction per cell, the
power table and the structural-break list) was frozen at git tag `prereg`, commit
3247f30575f3dcf08b329d720f150a72e2937f1d, SHA-256 of docs/hypotheses.md
28056437cdfd7c3baeb512aeb764adbc25457a0d4562ab0647eee400db35fb4d, publicly timestamped at
https://gist.github.com/HuJiawei-David/47f6478387d9dd488394a7ffb18f041e. The same gist holds the
timestamps of the live calls: the TSA/CAAC/Wikipedia 2026Q4 calls (outputs/tables/live_calls.csv, commit
89b8c69de10387c8be51d28d7a531968296562ae) and the earlier TCOM 2026Q3 forward call
(outputs/tables/live_calls_tcom_2026Q3.csv, commit 03746aaff9f4159fff7f0d1f027afc3c0e4a2a82). Nothing above
the "## Deviations" heading has changed (the file's SHA-256 is checked at every stage).

## Limitations

- **Sample size.** 14 quarters per U.S. cell (11 hits needed), 9 for Trip.com (8 needed). Even a true
  70% hit rate is detected only about a third of the time at N = 14 (power 0.355; outputs/tables/power_table.csv).
- **TSA is one U.S.-only series shared by six names.** It cannot see Booking's 90.4% non-U.S. entity
  revenue or Airbnb's 60.7% international listings (outputs/tables/geo_mix_fy2025.csv), and its six cells
  are one test (outputs/tables/tsa_dependence.csv).
- **Wikipedia measures attention, not demand**, is English only, spikes on earnings days, and is blocked
  in mainland China (Trip.com's series sees only non-mainland readers). Wikimedia also revised recent
  pageviews between pulls; the backtest uses the original snapshot (outputs/tables/snapshot_revision_check.csv).
- **Pandemic exclusion.** Quarters whose YoY uses a pandemic quarter are excluded and shown only in
  outputs/charts/pandemic_inflections_excluded.png.
- **Structural breaks.** 22 listed breaks (13 MAJOR) that no demand proxy can see, e.g. Uber's accounting
  changes (removing them leaves N = 1 for Uber revenue), Booking's −$900m FTC item, DoorDash's Deliveroo
  (config/breaks.yaml, outputs/tables/robustness.csv).
- **One TSA call is a knife-edge.** The 2024Q2 TSA d_alt is -0.0004; computed one day earlier it is +0.0001, which
  flips that quarter for all six U.S. names (e.g. LYFT revenue 11 → 12 of 14, placebo percentile 93.8 → 98.2;
  EXPE revenue 10 → 9). No other call changes. The pre-registered quarter-end results stand; the U.S. cells are that
  close to the line (outputs/tables/audit_asof_minus_1_cells.csv, docs/audit.md).
- **Trip.com's 9 hits include small moves.** 3 of the 9 were on |d_y| < 1 pp or |d_alt| < 0.01 (descriptive, not
  pre-registered; outputs/tables/tcom_caac_small_moves.csv).
- **Authors not blind.** David and an AI assistant had seen historical reported revenue before the
  pre-registration; it guards against specification search, not against prior knowledge of outcomes
  (docs/hypotheses.md §0).

## Research tooling

- **Config-driven.** Companies, sources, structural breaks and guidance live in config/*.yaml; adding a
  name or a source is a config change.
- **Point in time by publication date.** Every feature takes an explicit `asof` and asserts that nothing
  it used was published after it; tests delete or poison all later data and check the call is unchanged.
- **Snapshots.** Every external pull (SEC EDGAR, tsa.gov, Wikimedia, caac.gov.cn, Federal Register) is
  saved unmodified under data/raw/<source>/<pull_date>/ with its request parameters; code reads
  snapshots, never the live API. The backtest is pinned to the 2026-11-11 snapshots (config/pipeline.yaml).
- **One implementation.** The backtest and the live calls use the same function (src/nowcast/live.py
  `calls_at`); a test reproduces the locked Trip.com forward call byte for byte.
- **SQL.** Portable schema and queries in sql/*.sql (SQLite file data/nowcast.db; PostgreSQL-compatible);
  the relevancy matrix is produced by sql/results_summary.sql.
- **Independent audit.** docs/audit.md (Session 8, a different model than the builder): every as-of moved one
  day earlier, restated quarters, CAAC publication dates, spec drift, number traceability, fresh-clone rebuild
  (scripts/s8_audit_*.py, outputs/tables/audit_*.csv).
- **Tests.** pytest suite (tests/) covering point-in-time cut-offs, data validations, reconciliation
  against company-stated figures, the scoring rules and the quotes behind every guidance number.

## How to run

Rebuild every table, chart, memo input and the tracker from the committed snapshots (no network), then
run the tests:

```bash
bash scripts/run_all.sh
```

Requires Python 3.12 with `pip install -r requirements.txt` in `.venv/`. Network pulls (SEC needs a
contact User-Agent in `.env`, see `.env.example`) are separate: scripts/s2_pull_sec.py, s3_pull.py,
s6_pull_events.py.
