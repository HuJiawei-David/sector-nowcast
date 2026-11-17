# UBER — Uber Technologies: alt-data nowcast memo (2026-11-17)

**No detectable signal at n=14, which needed ≥ 11 hits.** At quarter end, TSA called the direction of Uber's revenue right in 8 of 14 quarters (the same as momentum) and of trips in 9 of 14; Wikipedia 9 of 14 and 10 of 14 (placebo percentiles 78.0 and 87.2) [R]. Quarter-end calls are available ~5.1 weeks before the print [LT].

**Current read vs company guidance.** For 2026Q4 TSA and combined say *accelerate*, Wikipedia says *decelerate* [LV]. Uber guides Gross Bookings +18% to +22% in constant currency; the 20% midpoint equals Q3's 20% [G], so guidance implies no change and there is no above/below label. Companies tend to guide conservatively.

**What would prove me wrong.** Trip growth in the Q4 release (estimate 2027-02-03 [LV]) below Q3's 15.6%, against the TSA and combined "accelerate".

---

**Debate and the KPI that settles it.** The Q3 release's CFO quote: "Uber continues to translate strong growth into expanding profitability" (https://www.sec.gov/Archives/edgar/data/1543151/000154315126000039/uberq326earningspressrelea.htm). My view: the debate is whether growth holds while autonomy spending rises; trips and Gross Bookings settle it, not GAAP revenue.

**Driver tree.** Revenue = Mobility + Delivery + Freight ≈ Gross Bookings × revenue margin; Gross Bookings = trips × basket/fare. The margin is moved by business-model choices. U.S. 45.7%, U.K. 20.4% of FY2025 revenue [D].

**Pre-registered hypothesis (quoted).** TSA y: "signal NOT expected" because "Accounting-model changes move reported revenue growth by up to 8–9pp"; TSA k: "Trips are global and include delivery orders" [H §5].

**What the data said.** Consistent with "not expected": no cell reaches its minimum hit count or the 95th placebo percentile [R]. Wikipedia y beats every other name's Wikipedia series on Uber's quarters (wrong-company percentile 100) [R], but its own placebo percentile is 78.0. The TSA magnitude model for trips beats "same as last quarter" (MAE 1.37 vs 1.73 pp; magnitude placebo percentile 97.6) [R]; magnitude is secondary and outside the multiple-testing family.

**Useless source here.** TSA for revenue: 8 of 14 = momentum, placebo percentile 21.5 [R]. Reported revenue growth is dominated by accounting changes.

**Structural breaks.** U.K. business-model change from 2026-01-02 (−8 to −9 pp on revenue growth in Q1–Q3 2026), earlier contra-revenue changes (2023Q2–2024Q3), Trendyol GO (MAJOR) [B]. Removing them leaves N = 1 for revenue ("robustness not informative"); trips keep N = 8 (TSA 5 of 8, Wikipedia 6 of 8) [RB].

**Live call and base period.** TSA 2026Q4 quarter-to-date d_alt +0.0150; Wikipedia −0.092; combined +0.258 [LV]. The U.K. model change runs through 2026Q4 [B]; the 2025 U.S. base has the federal lapse in appropriations and FAA cuts; without those days the TSA direction holds [S]. **Confidence: low.**

**What would change my mind.** A country-level trips or Gross Bookings proxy (app usage, card spend) that clears the placebo test on trips.

Sources: [R] outputs/tables/results.csv · [RB] robustness.csv · [LT] lead_time.csv · [LV] live_calls.csv · [S] live_tsa_sensitivity.csv · [G] config/guidance.yaml · [B] config/breaks.yaml · [D] docs/drivers.md · [H] docs/hypotheses.md
