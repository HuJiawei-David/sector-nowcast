# Case framework: "which alternative data would you use for this question?"

A four-step answer, then a checklist, using three names from this repo as worked examples. Every fact
cites its file; "my view" marks judgement.

## 1. Driver tree first
Write revenue as volume × price × take rate (+ FX, + M&A, + accounting), and mark each branch as
booking-time or travel-time and by geography (docs/drivers.md, section a-c per name).
- **EXPE**: revenue ≈ booked room nights × ADR × take rate, lodging recognised at check-in; 59.1% of
  revenue from U.S. points of sale (outputs/tables/geo_mix_fy2025.csv).
- **TCOM**: ticketing (36.0%) and accommodation (41.8%) of FY2025 revenue; ~75.1% PRC (drivers.md,
  geo_mix_fy2025.csv); revenue close to booking-time.
- **DASH**: revenue = Marketplace GOV × net revenue margin; GOV = Total Orders × AOV; 83.5% U.S. —
  local delivery, not travel (drivers.md).

## 2. Candidate proxies: map each to one branch
A proxy is only a candidate if it measures a branch that moves revenue, in the right geography and
at the right time. TSA = U.S. air departures (travel-time volume); CAAC = China national air
passengers (travel-time volume); Wikipedia = English-language attention.
- EXPE: TSA maps to the U.S. lodging-volume branch → pre-registered "signal expected (weak)".
- TCOM: CAAC maps to the PRC ticketing/hotel volume branch → "signal expected".
- DASH: no branch for air travel → "signal NOT expected" (docs/hypotheses.md section 5).

## 3. Test relevance before trusting it
Freeze series, model and windows (tag `prereg`), then walk forward at each quarter end using only data
published by then; score direction against first-reported growth; compare with momentum and 50%;
require a 1,000-run shuffle-placebo percentile ≥ 95 and count tests (39 cells, 1.95 expected by chance).
- TCOM CAAC y: 9/9 vs momentum 3/9, placebo percentile 99.0 → the only GREEN cell (outputs/tables/results.csv).
- EXPE TSA y: 10/14 vs momentum 7/14, placebo percentile 90.7 → not GREEN (same file).
- DASH TSA y: 8/14 vs momentum 8/14, placebo percentile 22.0 → no detectable signal (same file).

## 4. Why a proxy fails
Wrong branch (DASH), wrong geography (BKNG: 9.6% U.S. entity revenue, drivers.md), wrong timing
(booking-time KPIs vs travel-time TSA), price/FX/accounting moves (UBER: −8 to −9pp from the 2026 UK
model change, config/breaks.yaml), or a series that measures something else (Wikipedia: earnings-day
attention). Wrong-company test: UBER's own Wikipedia series scores 9/14 for y, no other name's series
scores more than 8/14 on UBER's quarters; for ABNB y, other names' series reach 10/14 vs its own 6/14
(outputs/tables/placebo_wrong_company.csv).

## Proxy quality checklist

| | TSA | CAAC (HKIA fallback) | Wikipedia |
|---|---|---|---|
| **Coverage** (branch / geography) | U.S. air departures only; BKNG revenue is 90.4% non-U.S. entities, ABNB 60.7% international listings (drivers.md) | National China air passengers; matches the ~75% PRC revenue of TCOM and its ticketing + hotel branches (drivers.md). HKIA not triggered (docs/decisions_log.md) | English-language attention to the company article, not bookings; blocked in mainland China, so TCOM's series sees only non-mainland readers (hypotheses.md section 5) |
| **Representativeness** (whose behaviour) | Everyone screened at U.S. airports — one series identical for all six US names, so its six cells are not independent (outputs/tables/tsa_dependence.csv) | All passengers on Chinese carriers, not Trip.com customers | Readers of English Wikipedia, incl. investors around earnings: the 7 days after each release are removed in robustness (iii) (outputs/tables/robustness.csv) |
| **Timeliness** (publication lag) | Next day (observation + 1 day; config/sources.yaml) | Bulletin 47-55 days after month start in 2024-2026 (data/processed/caac_monthly.csv): no month of the quarter at day 28, one at day 56, two at quarter end (outputs/tables/lead_time.csv) | Next day (config/sources.yaml) |
| **History length** (usable clean quarters) | From 2019-01-01; first clean d_alt 2023Q2 → N = 14 headline quarters per US cell (outputs/tables/power_table.csv) | From 2019-01; China reopened a year later → N = 9 (TCOM 2024Q2-2026Q2) | From 2019-01-01; N = 14 (US), 9 (TCOM) |
| **Definition stability** | Same national series 2019-2026; 0 gaps, 0 duplicate dates (outputs/tables/alt_validation.csv); 0 changed values on 2,870 overlapping days between the 2026-11-11 and 2026-11-17 pulls (outputs/tables/snapshot_revision_check.csv) | Flash figures: level-based YoY vs the bulletin's stated YoY differ by up to 0.69 pp (outputs/tables/caac_yoy_check.csv) | Article moves must be summed: Ctrip → Trip.com Group on 2019-11-07 (hypotheses.md section 4); targets break too (ABNB KPI redefined 2025Q2, config/breaks.yaml) |

## What I would buy next (my view; no vendor numbers)
1. **Card-spend panel (U.S. + Europe)** — proxies the price × volume branch per name (DASH GOV,
   LYFT gross bookings, EXPE/BKNG gross bookings) instead of one shared air series. Test: add it to
   config/sources.yaml with its delivery lag as the publication rule, pre-register cells in a new
   hypotheses file before the first delivery, run the same walk-forward and placebos.
2. **App downloads / usage panel** — proxies active users (LYFT Active Riders, UBER MAPCs) and
   engagement, per name and per country. Same harness; the wrong-company placebo becomes defined
   because each name has its own series.
3. **Licensed hotel-rate and ride-fare scrapes** — proxies the price branch (ADR, fares) that
   volume sources miss. Tested on the magnitude model (MAE vs y_q-1) as well as direction.
