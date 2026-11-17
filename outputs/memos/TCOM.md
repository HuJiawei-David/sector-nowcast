# TCOM — Trip.com Group: alt-data nowcast memo (2026-11-17)

**CAAC called the direction of Trip.com's revenue right in 9 of 9 quarters at quarter end (needed ≥ 8; momentum 3 of 9; shuffle-placebo percentile 99.0), available ~8.1 weeks before the print** [R, LT]. This is the only GREEN cell of the 39 pre-registered cells; 1.95 would pass by chance, and its Benjamini-Hochberg q-value (placebo) is 0.43 [MT, R]. N = 9 is small.

**Current read vs company guidance.** Locked 2026Q3 forward call (asof 2026-11-10, commit 03746aa): CAAC, Wikipedia and combined all say *accelerate*; the CAAC magnitude model gives 11.50% vs Q2's 5.52% [LV]. The Q2 release gives no quantitative guidance, so the label is "no guidance". 2026Q4: CAAC "insufficient data" (October not yet published), Wikipedia *accelerate*, guidance "pending" [LV].

**What would prove me wrong.** Q3 2026 revenue growth at or below Q2's 5.52% in the Q3 results 6-K (estimate 2026-11-17 [LV]).

---

**Debate and the KPI that settles it.** Trip.com cites "operational adjustments" to "align with evolving industry standards and compliance frameworks" as lowering growth from Q2 2026 [B]. My view: the debate is how much the SAMR case slows domestic growth; revenue growth settles it, since Trip.com discloses no volume KPI.

**Driver tree.** Accommodation 41.8% and transportation ticketing 36.0% of FY2025 revenue; ticketing recognised at issuance (close to booking-time); PRC ≈ 75.1% of revenue [D].

**Pre-registered hypothesis (quoted).** CAAC y: "**signal expected**" because "≈75% of revenue is PRC; ticketing + accommodation (≈78% of revenue) move with Chinese air-travel volume"; caveat "N = 9 needs 8 hits" [H §5].

**What the data said.** As predicted, and the strongest cell in the study: 9 of 9, all 6 revenue inflections caught, 8 of 9 at day 56 (~13.3 weeks before the print), 8 of 8 with break quarters removed [R, INF, LT, RB]. The magnitude model beats "same as last quarter" (MAE 2.97 vs 4.27 pp, N = 5) [R]. CAAC sees two months of the quarter at quarter end; no month is published by day 28 [LT].

**Useless source here.** Wikipedia: 3 of 9, placebo percentile 0.0 [R]. English Wikipedia is blocked in mainland China, so it sees only non-mainland attention.

**Structural breaks.** SAMR contra-revenue in 2026Q2 and the "operational adjustments" from 2026Q2 (both MAJOR) [B].

**Live call and base period.** The 2026Q2 base (q-1) is depressed by an unquantified SAMR contra-revenue, so part of any Q3 acceleration is mechanical; Trip.com reports no adjusted revenue [LV notes]. CAAC flash figures can differ from the bulletin's revised YoY by up to 0.69 pp (outputs/tables/caac_yoy_check.csv). **Confidence: moderate on direction, low on magnitude.**

**What would change my mind.** A Q3 miss; a run of misses would take the cell back towards chance.

Sources: [R] outputs/tables/results.csv · [RB] robustness.csv · [LT] lead_time.csv · [INF] inflections_summary.csv · [LV] live_calls.csv (incl. the locked rows from live_calls_tcom_2026Q3.csv) · [MT] multiple_testing.csv · [B] config/breaks.yaml · [D] docs/drivers.md · [H] docs/hypotheses.md
