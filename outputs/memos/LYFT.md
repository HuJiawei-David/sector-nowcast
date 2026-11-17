# LYFT — Lyft: alt-data nowcast memo (2026-11-17)

**TSA called the direction of Lyft's revenue right in 11 of 14 quarters at quarter end, available ~5.4 weeks before the print** [R, LT]. That reaches the pre-computed 11-hit minimum, but its shuffle-placebo percentile is 93.8 (< 95), so the cell is not GREEN, and revenue was the target it was predicted *not* to call. For rides, the pre-registered target, TSA was right in 7 of 12 (needed ≥ 10): no detectable signal [R].

**Current read vs company guidance.** For 2026Q4 TSA says *accelerate*, Wikipedia and combined *decelerate* [LV]. Lyft guides Gross Bookings +13% to +17% vs Q3's 17.5% [G], a deceleration: TSA is *above guidance*, the others *in line*. Companies tend to guide conservatively, so "above guidance" is the common case.

**What would prove me wrong.** Rides growth in the Q4 release (estimate 2027-02-09 [LV]) below Q3's 9.9%, and revenue growth excluding reserve items below Q3's 12.21%.

---

**Debate and the KPI that settles it.** Lyft's outlook: Gross Bookings "up approximately 13% to 17% year over year" (https://www.sec.gov/Archives/edgar/data/1759509/000162828026071043/lyft-20260930xpressrelease.htm). My view: the debate is U.S. share and the Freenow expansion; rides settle it.

**Driver tree.** Revenue ≈ Gross Bookings − driver payments and incentives; Gross Bookings = rides × fare. Reserve changes are booked as reductions to revenue. 95.9% of FY2025 revenue was U.S. [D].

**Pre-registered hypothesis (quoted).** TSA k: "**signal expected** (weak)", "96% U.S.; rides are travel-time U.S. ground mobility including airport trips"; TSA y: "signal NOT expected" because of incentives, reserve items and acquisitions [H §5].

**What the data said.** The opposite of the prediction. Revenue: 11 of 14, 7 of 8 inflections caught, 12 of 14 at day 56, 8 of 11 in the 2024Q1–2026Q3 window and with break quarters removed [R, INF, LT, RB]. Rides: 7 of 12 vs momentum 3 of 12, placebo percentile 28.8 [R]. I do not reinterpret this as a finding: it fails the placebo bar, it is one of 39 tests, and the six U.S. TSA cells share one call series [MT].

**Useless source here.** Wikipedia for rides: 7 of 12, placebo percentile 49.5 [R]; it measures attention.

**Structural breaks.** Reserve items of −$168m (2025Q4) and −$69.1m (2026Q3) are MAJOR; Freenow and TBR are MINOR [B]. Rides history starts in the Q3 2023 release, so momentum is "not run" for 2023Q2–Q3 and N is 12, not 14 [R].

**Live call and base period.** TSA d_alt +0.0150 [LV]; without the 2025 lapse-in-appropriations or FAA-cut base days the direction holds [S]. §3.12: GAAP y for 2026Q3 is 8.11% vs 12.21% excluding the $69.1m item; the −$168m item in the 2025Q4 base mechanically lifts GAAP Q4 growth, so the GAAP direction is partly mechanical [LV]. **Confidence: low.**

**What would change my mind.** Rides calls (not revenue) clearing the placebo test as quarters are added.

Sources: [R] outputs/tables/results.csv · [RB] robustness.csv · [LT] lead_time.csv · [INF] inflections_summary.csv · [LV] live_calls.csv · [S] live_tsa_sensitivity.csv · [MT] multiple_testing.csv · [G] config/guidance.yaml · [B] config/breaks.yaml · [D] docs/drivers.md · [H] docs/hypotheses.md
