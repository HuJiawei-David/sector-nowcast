# DASH — DoorDash: alt-data nowcast memo (2026-11-17)

**No detectable signal at n=14, which needed ≥ 11 hits.** At quarter end, TSA called the direction of DoorDash's revenue right in 8 of 14 quarters and of Total Orders in 7 of 14; Wikipedia 7 of 14 and 8 of 14; momentum alone got 8 of 14 for both [R]. Quarter-end calls are available ~5.1 weeks before the print [LT].

**Current read vs company guidance.** For 2026Q4 TSA and combined say *accelerate*, Wikipedia *decelerate* [LV]. DoorDash guides Marketplace GOV $35.4–36.4bn, implying +20.9% at the midpoint vs Q3's 35.7% [G, LV], a deceleration: TSA and combined are *above guidance*, Wikipedia *in line*. Companies tend to guide conservatively, so "above guidance" is the common case; here it is also implausible on mechanics (below).

**What would prove me wrong.** Total Orders growth in the Q4 release (estimate 2027-02-17 [LV]) at or above Q3's 28.0%. Deliveroo is in both Q4 2025 and Q4 2026, so it stops adding to growth and a deceleration is the mechanical default.

---

**Debate and the KPI that settles it.** DoorDash warns that "consumer spending in any of our geographies could deteriorate relative to our outlook" (https://www.sec.gov/Archives/edgar/data/1792789/000179278926000062/proddashex991-pressrelease.htm). My view: the debate is organic order growth once Deliveroo is lapped; Total Orders excluding Deliveroo settles it.

**Driver tree.** Revenue = Marketplace GOV × net revenue margin (+ Commerce Platform, ads); GOV = Total Orders × average order value. 83.5% of FY2025 revenue was U.S. [D].

**Pre-registered hypothesis (quoted).** Every DASH cell: "signal NOT expected"; TSA because "Local food/grocery delivery is not travel; no mechanical link from air throughput to orders or revenue" [H §5].

**What the data said.** Consistent with the hypothesis: no cell beats momentum on revenue; the best placebo percentile is 46.6 (Wikipedia, orders) [R]. The magnitude models match "same as last quarter" (TSA y MAE 3.18 vs 3.17 pp) [R].

**Useless source here.** TSA for both targets: no mechanism, 8 of 14 and 7 of 14, placebo percentiles 22.0 and 14.4 [R].

**Structural breaks.** Wolt (2022) and Deliveroo (closed 2025-10-02; Q3 2026 revenue +34% reported vs +23% excluding Deliveroo) are MAJOR; Symbiosys and SevenRooms MINOR [B]. Removing break quarters leaves N = 8 (TSA y 6 of 8) [RB].

**Live call and base period.** TSA d_alt +0.0150, Wikipedia −0.069, combined +0.138 [LV]. The 2025Q4 base contains the first Deliveroo quarter (MAJOR) and the U.S. lapse in appropriations; the TSA direction holds without those base days [S], but TSA has no link to DoorDash. **Confidence: very low.**

**What would change my mind.** A card-spend or app-usage panel on food delivery, by country, that clears the placebo test on Total Orders.

Sources: [R] outputs/tables/results.csv · [RB] robustness.csv · [LT] lead_time.csv · [LV] live_calls.csv · [S] live_tsa_sensitivity.csv · [G] config/guidance.yaml · [B] config/breaks.yaml · [D] docs/drivers.md · [H] docs/hypotheses.md
