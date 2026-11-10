# Pre-registered hypotheses — Sector Nowcast

Status: frozen at the commit tagged `prereg` (2026-11-10).

Nothing above the "## Deviations" heading may be edited after that tag; any change of plan is
appended under "## Deviations" with date and reason and is labelled exploratory in all outputs.
Outcomes of branches pre-registered here (e.g. the HKIA trigger, section 3.6) are not deviations;
they are recorded in docs/decisions_log.md.

## 0. Disclosure (hard rule 1)

The authors of this pre-registration — David and an AI assistant (Claude) — had seen historical
reported revenue for these companies before writing it. While writing docs/drivers.md the AI
assistant also read each company's latest earnings release, which contains multi-quarter tables of
revenue and KPI growth (for example Booking's room-night growth 3Q24–3Q26, DoorDash's five-quarter
Total Orders table, Expedia's seven-quarter operating metrics), and the size of several one-off items
quoted in the structural-break list. To classify break materiality (section 3.8) it also read
sentences from older 8-K / 10-Q / 10-K filings that state historical revenue, order and Gross
Bookings growth (e.g. DoorDash Q3 2022, Uber 2021–2022). This pre-registration therefore fixes series, models, metrics
and windows — it guards against specification search, **not** against prior knowledge of outcomes.
No alternative-data series (TSA throughput, Wikipedia pageviews, CAAC or HKIA statistics) was
downloaded or viewed for this project before the `prereg` tag; only Wikipedia page-move metadata
was queried (to fix article titles). The authors cannot rule out general familiarity with public
travel statistics.

The SHA-256 of this file is printed when the `prereg` tag is created, so that David can post it
publicly; git commit dates alone are self-asserted.

## 1. Model specification (copied verbatim from CLAUDE.md)

```text
## Model spec (summary; docs/hypotheses.md is authoritative once it exists)
- Targets (all names use calendar quarters):
  PRIMARY  y_q = revenue YoY growth (US names: XBRL; TCOM: 6-K press releases, RMB,
           point-in-time date = 6-K filing date).
  SECONDARY k_q = headline operating KPI YoY growth, from earnings press releases:
           BKNG room nights, EXPE booked room nights, ABNB nights & experiences booked,
           UBER trips, LYFT rides, DASH total orders. TCOM discloses no volume KPI: revenue only.
           Every KPI number is stored with its source filing URL and filing date.
           TSA and CAAC/HKIA measure VOLUME; revenue also moves with price, take rate, FX and
           M&A. So k is the mechanistically matched target for the volume sources, and the
           hypotheses must say so where it matters.
- STRUCTURAL BREAKS. docs/drivers.md lists, per name, known breaks that a demand proxy cannot
  see (acquisitions, accounting/reporting changes, KPI definition changes, large FX
  exposure), each with the affected quarters and its source document. The list is frozen at
  prereg. Results are reported on the full headline window AND with the listed quarters
  removed (robustness).
- Alt-data feature: alt_q = YoY growth of the source summed over the quarter (or
  quarter-to-date up to `asof`), versus the same days one year earlier (364-day shift,
  weekday-aligned). Monthly sources (CAAC/HKIA) use only months published by `asof`, versus
  the same months one year earlier. d_alt_q = alt_q - alt_{q-1}, both computed at the same
  `asof`. The same models are run for both targets (y and k).
- Source map: TSA for US names; CAAC (fallback HKIA) for TCOM; Wikipedia for all names.
  Wikipedia: English Wikipedia only. If an article was renamed/moved at any time since
  2019-01-01, its views are the sum over all its titles in that period (titles fixed in
  config at prereg). Known confounds the hypotheses must address: Wikipedia is blocked in
  mainland China (so for TCOM it measures non-mainland attention only); company articles
  spike on earnings days, so alt_q contains the reaction to the PREVIOUS quarter's release.
  Pre-registered robustness: Wikipedia alt with the 7 days starting on each earnings release
  date removed (from both years).
- PRIMARY CALL (direction): will y accelerate or decelerate vs last quarter?
  Prediction = sign(d_alt_q); d_alt_q == 0 counts as a miss. Baselines: momentum (same
  direction as last quarter; may use the previous quarter's value even if not clean) and 50%.
- COMBINED source: sign of the sum of each source's d_alt divided by that source's
  expanding-window std of clean d_alt values up to and including q. Needs >= 4 clean values,
  else the combined cell is "not run" for that quarter.
- SECONDARY (magnitude): yhat_q = y_{q-1} + beta * d_alt_q, beta from expanding-window OLS
  through the origin on clean (d_y, d_alt) pairs available before asof. If the name has
  fewer than 4 such pairs, use the beta pooled across all names for the SAME source; if that
  also has fewer than 4 pairs, the cell is "not run" for that quarter. Baseline: yhat_q = y_{q-1}.
- PLACEBOS: (a) shuffle d_alt across quarters, 1000 runs, fixed seed. This preserves the
  share of accelerate/decelerate calls, so it is the PRIMARY significance test.
  (b) wrong-company: score each name with every other name's series. Wikipedia only: TSA is
  the same series for all six US names and CAAC/HKIA maps to one name, so (b) is undefined
  for them.
- DEPENDENCE. TSA gives an identical call to all six US names each quarter. Never pool TSA
  calls across names as if independent; any cross-name summary counts each quarter once.
- LEAD TIME. The quarter-to-date direction call is computed at three fixed checkpoints per
  quarter: day 28, day 56 and quarter end (asof = quarter start + 27 days, + 55 days, quarter
  end). Report the hit rate at each checkpoint and the median number of weeks from each
  checkpoint to the earnings release date (8-K Item 2.02 / 6-K filing date). "Available ~W
  weeks before the print" = that median for the quarter-end checkpoint. Never use "the date
  the call stopped changing" (only knowable in hindsight).
- INFLECTIONS. An inflection is a clean quarter where sign(d_y_q) != sign(d_y_{q-1}).
  Report inflections caught vs missed by the quarter-end call.
- GUIDANCE BENCHMARK (live calls only): each company's own guidance for the quarter being
  called, from its latest earnings release: metric, low, high, midpoint, reported or
  constant currency, source URL. Guided direction = sign(guidance-midpoint-implied YoY of
  the guided metric minus the previous quarter's actual YoY of the same metric). Label:
  "above guidance" if the alt call is accelerate and guidance implies decelerate; "below
  guidance" in the reverse case; "in line" if both agree. If the guided metric is the model
  target, also compare yhat with the guidance-implied YoY ("in line" = within +/-1.0 pp).
  If a company gives no quantitative guidance, label "no guidance". Memos must note that
  companies tend to guide conservatively, so "above guidance" is the common case.
- LIVE CALLS: (a) 2026Q4 quarter-to-date, asof = run date, all names; (b) for any name that
  has not reported 2026Q3 by the run date, a 2026Q3 call with asof = run date. Live-call
  memos must list known one-off events in the base-year period that shift the YoY read.
- METRICS: direction hit rate with N and the minimum hit count needed for one-sided binomial
  p < 0.05 at that N (computed before results are viewed; e.g. N=14 needs 11); binomial p vs
  50% (reference only); shuffle-placebo percentile (primary); MAE in percentage points; MAE
  vs baseline. A cell is GREEN only if it beats both baselines AND its placebo percentile is
  >= 95. Multiple testing: report the number of direction cells tested, the number expected
  to pass by chance (0.05 x cells), and Benjamini-Hochberg q-values. Memos say "no detectable
  signal at this sample size", never "no signal".
```

## 2. Hard rules 2 and 4 (copied verbatim from CLAUDE.md)

```text
2. POINT-IN-TIME. A call for quarter q may use only (a) revenue/KPI facts whose `filed`
   date is before the as-of date and (b) alt-data observations whose PUBLICATION date is on
   or before the as-of date. Publication date: daily sources (TSA, Wikipedia) = observation
   date + 1 day; monthly sources (CAAC/HKIA) = the release date recorded from the source
   page, or, if it cannot be recorded, month end + 45 days. Backtest as-of = fiscal quarter
   end. Every feature-building function takes an explicit `asof` argument. Keep a test that
   fails if any feature uses data published after `asof`.
```

```text
4. EVALUATION WINDOW (name-specific, because China reopened a year after the US).
   Pandemic exclusion window: US names 2020Q1-2021Q4; TCOM 2020Q1-2022Q4.
   A YoY value for quarter q is CLEAN if neither q nor q-4 is in the exclusion window;
   a quarter-on-quarter change d_q is clean if both YoY values it uses are clean.
   Headline evaluation = calls whose target d_y (or d_k) is clean:
   US names 2023Q2-2026Q3; TCOM 2024Q2 through its last reported quarter.
   Pre-registered robustness window: US names 2024Q1-2026Q3.
   Model fitting and standardisation use clean values only. Excluded quarters appear only in
   a separate, clearly labelled chart.
```

## 3. Operational definitions fixed here (they complete, not change, the spec above)

1. **Alt-data history.** All alt series start on 2019-01-01 (2019-01 for monthly series). The first
   YoY value is therefore 2020, so no pre-pandemic clean alt values exist; the first clean d_alt is
   2023Q2 for US names and 2024Q2 for TCOM.
2. **Clean alt values.** An alt YoY value / d_alt value is clean under exactly the same
   name-specific rule as the target (hard rule 4). TSA uses the US window.
3. **Wikipedia series per name** = daily sum of English-Wikipedia pageviews (agent = `user`,
   access = `all-access`) over every listed article and every title it held since 2019-01-01
   (table in section 4). Exactly one Wikipedia series per name.
4. **Earnings release date** (for lead times and the Wikipedia 7-day robustness) = filing date of
   the 8-K carrying Item 2.02 (US) or of the 6-K carrying the results release (TCOM).
5. **Headline windows are fixed at prereg**: US names 2023Q2–2026Q3; TCOM 2024Q2–2026Q2 (2026Q2 is
   TCOM's last quarter whose results 6-K was filed before the prereg date, 2026-11-10; this is how
   hard rule 4's "through its last reported quarter" is fixed). The windows do not move when later
   quarters are reported. TCOM 2026Q3 is scored only as live call (b) (asof = run date), an
   out-of-sample test reported separately from the headline results and outside the
   multiple-testing family.
6. **HKIA fallback trigger.** HKIA replaces CAAC for TCOM (both as single source and inside the
   combined source) if and only if, when the CAAC data are first pulled, caac.gov.cn does not
   provide the national monthly civil-aviation passenger traffic figure for every month from
   2019-01 to the latest published month, each with either a release date recorded from the source
   page or the month-end + 45 days rule. The trigger outcome is a pre-registered branch, not a
   deviation: it is recorded in docs/decisions_log.md (date, evidence, outcome) before any
   statistic relating CAAC or HKIA to TCOM is computed, and not under "## Deviations". If the
   trigger does not fire, the HKIA cells are reported as "not run (fallback not triggered)".
7. **Multiple-testing family.** The family is the 39 headline direction cells in the power table
   (quarter-end checkpoint, full headline window): 6 US names × {TSA, Wikipedia, combined} ×
   {y, k} = 36, plus TCOM × {CAAC (or HKIA if triggered), Wikipedia, combined} × {y} = 3.
   Benjamini-Hochberg q-values are computed over these 39. The pre-registered variants —
   robustness window (US 2024Q1–2026Q3), structural-break removal, Wikipedia earnings-window
   removal, day-28 and day-56 checkpoints, and HKIA cells if not triggered — are reported for every
   cell but are not separate members of the family. Magnitude cells (MAE vs the y_{q-1} baseline)
   are secondary and are not members of the multiple-testing family. TCOM has no robustness
   window: its headline window (2024Q2–2026Q2) already starts after a full reopening year (2023,
   the first year after TCOM's exclusion window), which is what the US robustness window
   (2024Q1–2026Q3) achieves for the US names.
8. **Structural-break robustness.** Every break in section 7 carries `materiality: major | minor`,
   assigned by this rule only: MAJOR if (a) its type is accounting_model_change, one_off_revenue,
   kpi_definition or business_practice_change; or (b) the company quantifies the event's effect on
   revenue, the KPI or growth in a filing or earnings release, or reports a figure "excluding" it;
   otherwise MINOR. Each MAJOR (b) entry quotes the justifying sentence verbatim from the cited
   filing (config/breaks.yaml `materiality_quote`; the quote is checked against the saved filing by
   tests/test_config.py). In the structural-break robustness run a direction call for target
   quarter q is dropped if y_q or y_{q-1} (k_q or k_{q-1} for the KPI target) is listed in a MAJOR
   break for that name and target; MINOR breaks stay listed but are not dropped. The robustness N
   per cell is in the power table (section 6); where it is below 6 the cell's break-robustness
   result is reported as "robustness not informative".
9. **Meaning of the predictions below.** "Signal expected" = we expect the quarter-end direction
   hit rate to exceed both the 50% and the momentum baselines. Because N is small (section 6), a
   true but moderate signal will usually *not* reach the pre-computed minimum hit count, so
   "expected" is not a forecast that the cell turns GREEN. "Signal NOT expected" = we expect a hit
   rate indistinguishable from the baselines. For the magnitude model, MAE is expected to beat the
   y_{q-1} baseline only in "signal expected" cells.
10. **Missing data at a checkpoint.** If a source has no published observation inside quarter q at
   a given asof (for example CAAC at day 28, when no month of q has been published yet), that
   cell-quarter is "not run (no data)", not a miss: it is excluded from the cell's N at that
   checkpoint. The count of such cell-quarters is reported per cell and checkpoint. For the
   combined source, a component with no data at asof makes the combined cell-quarter
   "not run (no data)" as well.
11. **Like-for-like YoY.** y_q and k_q are computed as the current-period value divided by the
   prior-year comparative value taken from the SAME filing or release (the latest one filed before
   asof that reports q), minus one, so definition changes and recasts are compared on one basis.
   If that release gives no comparable prior-year value, the YoY % the company states in that
   release is used; if neither exists, the quarter is "not run (no like-for-like base)". When y_q
   or k_q is the realised outcome being scored (it is reported after asof by construction), the
   filing used is the first earnings release (or, for XBRL revenue, the first filing) that
   reports q.
12. **Live calls and one-offs.** If quarter q-1 or q-4 of a live call contains a MAJOR
   one_off_revenue break (for the 2026Q4 live call: BKNG 2026Q3 FTC item; LYFT 2025Q4 and 2026Q3
   reserve items), the live call is ALSO stated against the company's adjusted metric where the
   company reports one (e.g. BKNG Adjusted Revenue), and the memo says that the GAAP direction is
   mechanically driven by that item.

## 4. Data series per name

| Name | Revenue target y | KPI target k | Volume source | Wikipedia articles (all titles since 2019-01-01) |
|---|---|---|---|---|
| BKNG | XBRL `Revenues` (USD) | Room nights | TSA national daily throughput | Booking Holdings; Booking.com |
| EXPE | XBRL `RevenueFromContractWithCustomerExcludingAssessedTax` (USD) | Booked Room Nights | TSA national daily throughput | Expedia Group; Expedia |
| ABNB | XBRL `RevenueFromContractWithCustomerExcludingAssessedTax` (USD) | Nights and Seats Booked (formerly Nights and Experiences Booked) | TSA national daily throughput | Airbnb |
| UBER | XBRL `Revenues` (USD) | Trips | TSA national daily throughput | Uber |
| LYFT | XBRL `Revenues`, else `RevenueFromContractWithCustomerExcludingAssessedTax` (USD) | Rides | TSA national daily throughput | Lyft |
| DASH | XBRL `RevenueFromContractWithCustomerExcludingAssessedTax` (USD) | Total Orders | TSA national daily throughput | DoorDash |
| TCOM | Total net revenues from 6-K Ex-99.1 results releases (RMB; point-in-time = 6-K filing date) | none disclosed (revenue only) | CAAC monthly national civil-aviation passenger traffic; pre-registered fallback HKIA monthly passenger statistics | Trip.com Group (former title: Ctrip, moved 2019-11-07); Trip.com |

Wikipedia move check (2026-11-10, raw responses in `data/raw/wikipedia_meta/2026-11-10/`): each
article's revision history since 2019-01-01 was scanned for page-move edits and every title found
was cross-checked against the move log. The only move found: "Ctrip" → "Trip.com Group" on
2019-11-07. All other listed articles held a single title throughout. Config:
`config/companies.yaml`. Sources and publication rules: `config/sources.yaml`.

## 5. Hypotheses per (name, source, target)

Confounds that apply throughout (see docs/drivers.md for the per-name evidence):

- **Volume vs revenue.** TSA, CAAC and HKIA measure travel volume. Revenue also moves with price
  (ADR, fares, basket size), take rate, FX, accounting-model choices and M&A. The KPI k is the
  mechanistically matched target for the volume sources; but four of the six US KPIs are
  booking-time or global, so "matched" does not imply "expected".
- **TSA is identical across the six US names.** Each quarter it gives the same accelerate /
  decelerate call to all six. The six TSA cells are not six independent tests; cross-name summaries
  count each quarter once. We predict TSA works only where the name's mechanism points to it
  (EXPE revenue, LYFT rides); a TSA "hit" across all six names in the same quarters would point to a
  common macro co-movement, not to name-specific information.
- **Wikipedia is blocked in mainland China**, so for TCOM the English-Wikipedia series measures
  non-mainland attention only, while ≈75% of revenue is PRC (drivers.md).
- **Earnings-day spikes.** Company articles spike on earnings days, and the release for quarter q-1
  falls inside quarter q, so alt_q contains the reaction to the previous quarter's results. The
  pre-registered robustness run removes the 7 days starting on each earnings release date (both
  years).

| Name | Source | Target | Prediction | Reason (drivers.md) |
|---|---|---|---|---|
| BKNG | TSA | y | signal NOT expected | ~90% of revenue booked through non-U.S. entities, demand Europe/Asia-weighted; EUR/GBP translation and the Q3 2026 FTC −$900m revenue item move y; TSA sees none of this. |
| BKNG | TSA | k | signal NOT expected | Room nights are booking-time and global; TSA is travel-time U.S. air volume, a small unidentified share. |
| BKNG | Wikipedia | y | signal NOT expected | English views of Booking Holdings / Booking.com reflect news, investor and earnings-day attention, not bookings. |
| BKNG | Wikipedia | k | signal NOT expected | Same as above. |
| BKNG | Combined | y | signal NOT expected | Neither component is expected to carry signal. |
| BKNG | Combined | k | signal NOT expected | Neither component is expected to carry signal. |
| EXPE | TSA | y | **signal expected** (weak) | 59% of revenue from U.S. points of sale and lodging revenue recognised at check-in, so same-quarter U.S. travel-volume shocks reach revenue; diluted by B2B/global growth, ADR and FX. |
| EXPE | TSA | k | signal NOT expected | Booked room nights are booking-time and increasingly B2B/global; the booking window decouples them from same-quarter U.S. departures. |
| EXPE | Wikipedia | y | signal NOT expected | Expedia Group / Expedia views measure attention (news, earnings), not bookings. |
| EXPE | Wikipedia | k | signal NOT expected | Same as above. |
| EXPE | Combined | y | **signal expected** (weaker than TSA alone) | Carries the TSA mechanism; equal weighting with a non-informative Wikipedia series dilutes it. |
| EXPE | Combined | k | signal NOT expected | Neither component expected for k. |
| ABNB | TSA | y | signal NOT expected | Revenue is check-in-time, but 61% comes from non-U.S. listings and FX, ADR and take rate move it. |
| ABNB | TSA | k | signal NOT expected | Nights and Seats Booked are booking-time and 61% international; KPI redefined from 2025Q2. |
| ABNB | Wikipedia | y | signal NOT expected | High-traffic general-interest article (regulation, news); attention, not bookings. |
| ABNB | Wikipedia | k | signal NOT expected | Same as above. |
| ABNB | Combined | y | signal NOT expected | Neither component expected. |
| ABNB | Combined | k | signal NOT expected | Neither component expected. |
| UBER | TSA | y | signal NOT expected | Accounting-model changes move reported revenue growth by up to 8–9pp (2023Q2–2024Q3, 2026Q1–Q4); U.S. <50% of revenue; Delivery and Freight unrelated to air travel. |
| UBER | TSA | k | signal NOT expected | Trips are global and include delivery orders; U.S. airport rides are a small share. |
| UBER | Wikipedia | y | signal NOT expected | Very high-traffic general article; attention, not trips. |
| UBER | Wikipedia | k | signal NOT expected | Same as above. |
| UBER | Combined | y | signal NOT expected | Neither component expected. |
| UBER | Combined | k | signal NOT expected | Neither component expected. |
| LYFT | TSA | y | signal NOT expected | Revenue growth is moved by driver incentives (contra revenue), reserve items (−$168m Q4 2025, −$69.1m Q3 2026) and the Freenow/TBR acquisitions. |
| LYFT | TSA | k | **signal expected** (weak) | 96% U.S.; rides are travel-time U.S. ground mobility including airport trips, so same-quarter U.S. travel/mobility shocks reach rides; airport trips are a minority and Freenow adds Europe from 2025Q3. |
| LYFT | Wikipedia | y | signal NOT expected | Attention, not rides. |
| LYFT | Wikipedia | k | signal NOT expected | Attention, not rides. |
| LYFT | Combined | y | signal NOT expected | Neither component expected for y. |
| LYFT | Combined | k | **signal expected** (weaker than TSA alone) | Carries the TSA mechanism for rides; diluted by Wikipedia. |
| DASH | TSA | y | signal NOT expected | Local food/grocery delivery is not travel; no mechanical link from air throughput to orders or revenue; Wolt and Deliveroo also move y. |
| DASH | TSA | k | signal NOT expected | Same; Total Orders also jump with Deliveroo (2025Q4–2026Q3). |
| DASH | Wikipedia | y | signal NOT expected | Attention, not orders. |
| DASH | Wikipedia | k | signal NOT expected | Attention, not orders. |
| DASH | Combined | y | signal NOT expected | Neither component expected. |
| DASH | Combined | k | signal NOT expected | Neither component expected. |
| TCOM | CAAC | y | **signal expected** | ≈75% of revenue is PRC; ticketing + accommodation (≈78% of revenue) move with Chinese air-travel volume, and short booking windows keep booking-time revenue close to travel-time traffic. Caveats: the quarter-end call sees only months published by `asof` (with the +45-day rule, only the first month of the quarter), price and take rate move revenue, SAMR rectification from 2026Q2; N = 9 needs 8 hits. |
| TCOM | HKIA (fallback) | y | signal NOT expected | Hong Kong airport passengers (HK residents, transit, international) are a small, international slice of a PRC-weighted revenue base. |
| TCOM | Wikipedia | y | signal NOT expected | Blocked in mainland China: measures non-mainland attention (a minority of revenue) plus SAMR news spikes (2026Q1 investigation, 2026Q3 decision). |
| TCOM | Combined | y | **signal expected** if CAAC is used (weaker than CAAC alone); signal NOT expected if the HKIA fallback is triggered | Follows its volume component. |

Summary: 6 of the 39 family cells are predicted "signal expected" (EXPE TSA y, EXPE combined y,
LYFT TSA k, LYFT combined k, TCOM CAAC y, TCOM combined y); 33 are predicted "signal NOT expected".
The HKIA cell is predicted "signal NOT expected".

## 6. Power table

Computed by `src/nowcast/power.py` from `config/companies.yaml` (output:
`outputs/tables/power_table.csv`, `outputs/tables/power_table.md`), before any alt data was
downloaded. N = headline quarters that can be scored (headline windows fixed at prereg,
section 3.5); `min_hits_p05` = smallest hit count with one-sided binomial P(X ≥ h | N, 0.5) < 0.05;
`power_if_true_p` = probability of reaching that count if the true hit rate were p. Combined cells
start later because they need ≥ 4 clean d_alt values up to and including q. HKIA cells, if
triggered, have the same N as the CAAC rows. `N_excl_major_breaks` / `min_hits_excl_major` = N and
minimum hit count in the structural-break robustness run (MAJOR breaks dropped, section 3.8);
`break_robustness` says "robustness not informative" where that N is below 6. N in this table
assumes no "not run" quarters (sections 3.10, 3.11); actual N can only be lower.

| name | source | target | first_q | last_q | N | min_hits_p05 | p_at_min_hits | power_if_true_0.6 | power_if_true_0.7 | power_if_true_0.8 | N_excl_major_breaks | min_hits_excl_major | break_robustness |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| BKNG | tsa | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 13 | 10 |  |
| BKNG | wikipedia | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 13 | 10 |  |
| BKNG | combined | y | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 10 | 9 |  |
| BKNG | tsa | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| BKNG | wikipedia | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| BKNG | combined | k | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 11 | 9 |  |
| EXPE | tsa | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| EXPE | wikipedia | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| EXPE | combined | y | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 11 | 9 |  |
| EXPE | tsa | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| EXPE | wikipedia | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| EXPE | combined | k | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 11 | 9 |  |
| ABNB | tsa | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| ABNB | wikipedia | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| ABNB | combined | y | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 11 | 9 |  |
| ABNB | tsa | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 8 | 7 |  |
| ABNB | wikipedia | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 8 | 7 |  |
| ABNB | combined | k | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 5 | 5 | robustness not informative |
| UBER | tsa | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 1 |  | robustness not informative |
| UBER | wikipedia | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 1 |  | robustness not informative |
| UBER | combined | y | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 1 |  | robustness not informative |
| UBER | tsa | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 8 | 7 |  |
| UBER | wikipedia | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 8 | 7 |  |
| UBER | combined | k | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 5 | 5 | robustness not informative |
| LYFT | tsa | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 11 | 9 |  |
| LYFT | wikipedia | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 11 | 9 |  |
| LYFT | combined | y | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 8 | 7 |  |
| LYFT | tsa | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| LYFT | wikipedia | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 14 | 11 |  |
| LYFT | combined | k | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 11 | 9 |  |
| DASH | tsa | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 8 | 7 |  |
| DASH | wikipedia | y | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 8 | 7 |  |
| DASH | combined | y | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 7 | 7 |  |
| DASH | tsa | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 8 | 7 |  |
| DASH | wikipedia | k | 2023Q2 | 2026Q3 | 14 | 11 | 0.0287 | 0.124 | 0.355 | 0.698 | 8 | 7 |  |
| DASH | combined | k | 2024Q1 | 2026Q3 | 11 | 9 | 0.0327 | 0.119 | 0.313 | 0.617 | 7 | 7 |  |
| TCOM | caac | y | 2024Q2 | 2026Q2 | 9 | 8 | 0.0195 | 0.071 | 0.196 | 0.436 | 8 | 7 |  |
| TCOM | wikipedia | y | 2024Q2 | 2026Q2 | 9 | 8 | 0.0195 | 0.071 | 0.196 | 0.436 | 8 | 7 |  |
| TCOM | combined | y | 2025Q1 | 2026Q2 | 6 | 6 | 0.0156 | 0.047 | 0.118 | 0.262 | 5 | 5 | robustness not informative |

Headline direction cells: 39; expected to pass p<0.05 by chance alone: 1.95 (= 0.05 x cells).

## 7. Structural-break list (copied from docs/drivers.md; source: config/breaks.yaml)

Materiality per section 3.8. Evidence search for the (b) rule: EDGAR full-text search for each
acquiree's name in the company's 8-K / 10-Q / 10-K filings (`scripts/s1b_materiality_search.py`;
raw responses in `data/raw/sec_efts/2026-11-10/`, documents in `data/raw/sec_filings/2026-11-10/`).

| Name | Event | Type | Materiality | Effective | Targets | Affected YoY quarters | Source filing |
|---|---|---|---|---|---|---|---|
| BKNG | Acquisition of Getaroom (B2B hotel distributor) completed December 2021 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py) | 2021-12 | y | 2021Q4, 2022Q1, 2022Q2, 2022Q3, 2022Q4 (all outside the clean set; listed for completeness) | [bkng-20211231.htm](https://www.sec.gov/Archives/edgar/data/1075531/000107553122000008/bkng-20211231.htm) |
| BKNG | FTC matter: $900 million reduction in revenue recorded in Q3 2026 (excluded from Adjusted Revenue); GAAP revenue -1% Y/Y vs Adjusted Revenue +9% | one_off_revenue | MAJOR (a) type one_off_revenue | 2026Q3 | y | 2026Q3, 2027Q3 | [q3-26bkngearningsrelease.htm](https://www.sec.gov/Archives/edgar/data/1075531/000107553126000044/q3-26bkngearningsrelease.htm) |
| EXPE | Sale of Egencia (corporate travel) to GBT completed 2021-11-01; deconsolidated | disposal | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py) | 2021-11-01 | y, k | 2021Q4, 2022Q1, 2022Q2, 2022Q3, 2022Q4 (all outside the clean set; listed for completeness) | [expe-20221231.htm](https://www.sec.gov/Archives/edgar/data/1324424/000132442423000007/expe-20221231.htm) |
| ABNB | KPI redefined: 'Nights and Experiences Booked' became 'Nights and Seats Booked' (adds seats for experiences and services; services launched in Q2 2025). First used in the Q2 2025 10-Q; company says substantially all bookings are nights | kpi_definition | MAJOR (a) type kpi_definition | 2025Q2 | k | 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | [abnb-20250630.htm](https://www.sec.gov/Archives/edgar/data/1559720/000155972025000025/abnb-20250630.htm) |
| UBER | Acquisition of Transplace (Freight) in Q4 2021 | acquisition | MAJOR (b) company quantifies the effect: "Excluding Transplace, the organic Freight business revenue grew 27% to $396 million." ([uberq421earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315122000004/uberq421earningspressrelea.htm)) | 2021-11 | y | 2021Q4, 2022Q1, 2022Q2, 2022Q3, 2022Q4 (all outside the clean set; listed for completeness) | [uber-20220630.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315122000024/uber-20220630.htm) |
| UBER | UK business model change effective 2022-03-14 (Mobility revenue reported gross); Q1 2022 benefit $200m vs Q1 2023 $1.1bn, Q2 2022 $1.1bn | accounting_model_change | MAJOR (a) type accounting_model_change | 2022-03-14 | y | 2022Q1, 2022Q2, 2022Q3, 2022Q4, 2023Q1 | [uberq123earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315123000013/uberq123earningspressrelea.htm) |
| UBER | Business model changes in some countries classifying certain sales and marketing costs as contra revenue (Delivery from Q2 2023, Mobility from Q3 2023); company quantifies the negative Y/Y revenue impact through Q3 2024 (e.g. -8pp total revenue growth in Q1 2024, -7pp in Q2 2024) | accounting_model_change | MAJOR (a) type accounting_model_change | 2023Q2 | y | 2023Q2, 2023Q3, 2023Q4, 2024Q1, 2024Q2, 2024Q3 | [uberq224earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315124000024/uberq224earningspressrelea.htm)<br>[uberq223earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315123000021/uberq223earningspressrelea.htm)<br>[uberq323earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315123000036/uberq323earningspressrelea.htm)<br>[uberq124earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315124000017/uberq124earningspressrelea.htm)<br>[uberq324earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315124000033/uberq324earningspressrelea.htm) |
| UBER | Acquisition of 85% of Trendyol GO (Turkey delivery) completed 2025-06-17 | acquisition | MAJOR (b) company quantifies the effect: "As a reminder, our outlook includes the contribution from the close of the Trendyol Go acquisition; excluding this, our growth outlook would be 16% to 20% YoY on a constant-currency basis (consistent with the prior quarter)." ([uberq225earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315125000020/uberq225earningspressrelea.htm)) | 2025-06-17 | y, k | 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | [uber-20251231.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000015/uber-20251231.htm) |
| UBER | UK business model change effective 2026-01-02 (Uber no longer responsible for Mobility services in certain UK markets; driver payments become a reduction of revenue); company: -$1.0bn revenue in Q1 2026, -8 to -9pp on total revenue Y/Y growth in Q1-Q3 2026 | accounting_model_change | MAJOR (a) type accounting_model_change | 2026-01-02 | y | 2026Q1, 2026Q2, 2026Q3, 2026Q4 | [uber-20260331.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000022/uber-20260331.htm)<br>[uberq326earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000039/uberq326earningspressrelea.htm) |
| UBER | Acquisition of SpotHero (parking reservations) completed 2026-04-16 | acquisition | MINOR: the company says SpotHero contributed an immaterial amount of revenue (not quantified); no 'excluding' figure found (EDGAR full-text search, scripts/s1b_materiality_search.py) | 2026-04-16 | y, k | 2026Q2, 2026Q3, 2026Q4, 2027Q1, 2027Q2 | [uber-20260930.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000041/uber-20260930.htm) |
| UBER | Acquisition of Getir's food delivery business (Turkey) completed 2026-07-01 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py) | 2026-07-01 | y, k | 2026Q3, 2026Q4, 2027Q1, 2027Q2 | [uber-20260930.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000041/uber-20260930.htm) |
| UBER | Control of Careem Technologies obtained 2026-07-31 (~60% stake); consolidated from that date | acquisition | MINOR: the company says Careem Technologies contributed an immaterial amount of revenue (not quantified); no 'excluding' figure found (EDGAR full-text search, scripts/s1b_materiality_search.py) | 2026-07-31 | y, k | 2026Q3, 2026Q4, 2027Q1, 2027Q2, 2027Q3 | [uber-20260930.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000041/uber-20260930.htm) |
| LYFT | Acquisition of Freenow (European taxi/multimodal app) completed 2025-07-31 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py); the 10-K says Freenow 'did not contribute a significant amount of revenue' | 2025-07-31 | y, k | 2025Q3, 2025Q4, 2026Q1, 2026Q2, 2026Q3 | [lyft-20251231.htm](https://www.sec.gov/Archives/edgar/data/1759509/000162828026006960/lyft-20251231.htm) |
| LYFT | Acquisition of TBR Global Chauffeuring completed 2025-10-14 | acquisition | MINOR: the company says TBR contributed an immaterial amount of revenue (not quantified); no 'excluding' figure found (EDGAR full-text search, scripts/s1b_materiality_search.py) | 2025-10-14 | y, k | 2025Q4, 2026Q1, 2026Q2, 2026Q3, 2026Q4 | [lyft-20251231.htm](https://www.sec.gov/Archives/edgar/data/1759509/000162828026006960/lyft-20251231.htm) |
| LYFT | Legal, tax and regulatory reserve changes and settlements recorded as a reduction to revenue: $168m in Q4 2025 (revenue +3% Y/Y as reported) | one_off_revenue | MAJOR (a) type one_off_revenue | 2025Q4 | y | 2025Q4, 2026Q4 | [lyft-2025x12x31pressreleas.htm](https://www.sec.gov/Archives/edgar/data/1759509/000162828026006817/lyft-2025x12x31pressreleas.htm) |
| LYFT | Legal, tax and regulatory reserve changes and settlements: $69.1m recorded as a reduction to revenue in Q3 2026 | one_off_revenue | MAJOR (a) type one_off_revenue | 2026Q3 | y | 2026Q3, 2027Q3 | [lyft-20260930xpressrelease.htm](https://www.sec.gov/Archives/edgar/data/1759509/000162828026071043/lyft-20260930xpressrelease.htm) |
| DASH | Acquisition of Wolt completed 2022-05-31 | acquisition | MAJOR (b) company quantifies the effect: "Revenue increased 33% Y/Y to $1.7 billion in Q3 2022 from $1.3 billion, driven by 25% Y/Y growth in DoorDash revenue and the addition of Wolt." ([dashq32022ex991-shareholde.htm](https://www.sec.gov/Archives/edgar/data/1792789/000162828022028194/dashq32022ex991-shareholde.htm)) | 2022-05-31 | y, k | 2022Q2, 2022Q3, 2022Q4, 2023Q1, 2023Q2 | [dash-20220531.htm](https://www.sec.gov/Archives/edgar/data/1792789/000162828022015815/dash-20220531.htm) |
| DASH | Acquisition of Symbiosys (retail media) completed 2025-05-28 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py) | 2025-05-28 | y | 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | [dash-20251231.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000013/dash-20251231.htm) |
| DASH | Acquisition of SevenRooms (restaurant reservation software) completed 2025-06-13 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py); the FY2025 10-K gives one figure for SevenRooms and Deliveroo together (3% of 2025 revenue), which does not isolate SevenRooms | 2025-06-13 | y | 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | [dash-20251231.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000013/dash-20251231.htm) |
| DASH | Acquisition of Deliveroo completed 2025-10-02 ($3,724m); Q3 2026 revenue +34% Y/Y reported vs +23% excluding Deliveroo | acquisition | MAJOR (b) company quantifies the effect: "Excluding Deliveroo, revenue increased 23% Y/Y in Q3 2026." ([proddashex991-pressrelease.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000062/proddashex991-pressrelease.htm)) | 2025-10-02 | y, k | 2025Q4, 2026Q1, 2026Q2, 2026Q3 | [dash-20251231.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000013/dash-20251231.htm)<br>[proddashex991-pressrelease.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000062/proddashex991-pressrelease.htm) |
| TCOM | SAMR anti-monopoly case (investigation notified 2026-01-14; decision 2026-07-25): contra-revenue imposed by SAMR reduced Q2 2026 accommodation revenue; RMB5.2bn penalty (expense, not revenue) | one_off_revenue | MAJOR (a) type one_off_revenue | 2026Q2 | y | 2026Q2, 2027Q2 | [d167816dex991.htm](https://www.sec.gov/Archives/edgar/data/1269238/000119312526392473/d167816dex991.htm)<br>[d256213d6k.htm](https://www.sec.gov/Archives/edgar/data/1269238/000119312526316761/d256213d6k.htm) |
| TCOM | 'Operational adjustments ... to align with evolving industry standards and compliance frameworks' cited by the company as lowering growth from Q2 2026 (Q1 2026 release outlook; Q2 2026 release) | business_practice_change | MAJOR (a) type business_practice_change | 2026Q2 | y | 2026Q2, 2026Q3, 2026Q4, 2027Q1, 2027Q2 | [d163607dex991.htm](https://www.sec.gov/Archives/edgar/data/1269238/000119312526281805/d163607dex991.htm)<br>[d167816dex991.htm](https://www.sec.gov/Archives/edgar/data/1269238/000119312526392473/d167816dex991.htm) |

## Deviations
