# EXPE — Expedia Group: alt-data nowcast memo (2026-11-17)

**No detectable signal at n=14, which needed ≥ 11 hits.** TSA, the pre-registered source, called the direction of Expedia's revenue right in 10 of 14 quarters at quarter end (momentum 7 of 14; shuffle-placebo percentile 90.7, below the 95 required) and booked room nights in 9 of 14 [R]. Quarter-end calls are available ~5.3 weeks before the print [LT].

**Current read vs company guidance.** For 2026Q4 TSA says *accelerate*, Wikipedia and combined say *decelerate* [LV]. Expedia guides revenue +4.0% to +5.7% vs Q3's 11.9% [G], a deceleration: the TSA read is *above guidance*, Wikipedia and combined are *in line*. The TSA magnitude model gives 13.60% vs the 4.85% midpoint [LV]. Companies tend to guide conservatively, so "above guidance" is the common case.

**What would prove me wrong.** Q4 revenue growth (estimate 2027-02-11 [LV]) below Q3's 11.9%, which is what guidance implies, against the TSA call.

---

**Debate and the KPI that settles it.** The Q3 release shows B2B revenue +23% vs B2C +6% [D]. My view: the debate is B2B growth vs the U.S. consumer brands; revenue growth by segment settles it, with booked room nights as the volume check.

**Driver tree.** Lodging revenue ≈ booked room nights × ADR × take rate, recognised at check-in; plus air, B2B, trivago and Vrbo fees. 59.1% of revenue comes from U.S. points of sale [D].

**Pre-registered hypothesis (quoted).** TSA y: "**signal expected** (weak)", because of "59% of revenue from U.S. points of sale and lodging revenue recognised at check-in"; TSA k: "signal NOT expected" [H §5].

**What the data said.** In the predicted direction but not significant. TSA y beats both baselines (10 vs 7 of 14) and its magnitude model beats "same as last quarter" (MAE 2.75 vs 3.03 pp; magnitude placebo percentile 96.2), but the direction placebo percentile is 90.7 [R]. At day 28 TSA was right in 12 of 14 [LT]. It caught 5 of 7 revenue inflections [INF]. In the US 2024Q1–2026Q3 window it is 8 of 11 [RB].

**Useless source here.** Wikipedia: 7 of 14 for revenue, equal to momentum, placebo percentile 29.7 [R]. It measures attention, not bookings.

**Structural breaks.** None inside the clean window (Egencia sale 2021 only touches excluded quarters) [B]; the break-removed run is unchanged at 10 of 14 [RB].

**Live call and base period.** TSA 2026Q4 quarter-to-date d_alt +0.0150 [LV]. The 2025 base contains the federal lapse in appropriations and FAA flight cuts; without those base days the direction holds (d_alt +0.0398 and +0.0086) [S]. Wikipedia d_alt −0.689 drives the combined decelerate [LV]. **Confidence: low to moderate.** The source fits the mechanism but did not clear the pre-registered bar, and the two sources disagree.

**What would change my mind.** The placebo test is rerun as each quarter is reported; a TSA miss on Q4 would weaken the case, a hit alone would not make it significant.

Sources: [R] outputs/tables/results.csv · [RB] robustness.csv · [LT] lead_time.csv · [INF] inflections_summary.csv · [LV] live_calls.csv · [S] live_tsa_sensitivity.csv (sensitivity, not pre-registered) · [G] config/guidance.yaml · [B] config/breaks.yaml · [D] docs/drivers.md · [H] docs/hypotheses.md
