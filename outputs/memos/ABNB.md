# ABNB — Airbnb: alt-data nowcast memo (2026-11-17)

**No detectable signal at n=14, which needed ≥ 11 hits.** At quarter end, TSA called the direction of Airbnb's revenue right in 7 of 14 quarters and of Nights and Seats Booked in 9 of 14; Wikipedia 6 of 14 and 10 of 14 (placebo percentile 88.5, below 95) [R]. Quarter-end calls are available ~5.3 weeks before the print [LT].

**Current read vs company guidance.** For 2026Q4 TSA, Wikipedia and combined all say *accelerate* [LV]. Airbnb guides revenue +16% to +18% vs Q3's 18.9% [G], a deceleration, so the read is *above guidance*; the TSA magnitude model gives 19.08% vs the 17.00% midpoint [LV]. Companies tend to guide conservatively, so "above guidance" is the common case.

**What would prove me wrong.** Q4 revenue growth (estimate 2027-02-11 [LV]) below Q3's 18.9%, which is what guidance implies.

---

**Debate and the KPI that settles it.** The Q3 release says Airbnb is "encouraged by the meaningful acceleration we've delivered in 2026" (https://www.sec.gov/Archives/edgar/data/1559720/000119312526449727/d437988dex991.htm). My view: the debate is whether that acceleration lasts; Nights and Seats Booked growth settles it.

**Driver tree.** Revenue ≈ GBV × take rate; GBV = Nights and Seats Booked × ADR. Revenue is recognised at check-in, the KPI at booking. 39.3% of revenue comes from U.S. listings; Q4 guidance includes about a 2 pp FX tailwind [D, G].

**Pre-registered hypothesis (quoted).** Every ABNB cell: "signal NOT expected"; TSA y because "61% comes from non-U.S. listings and FX, ADR and take rate move it"; Wikipedia because it is a "High-traffic general-interest article" [H §5].

**What the data said.** Revenue: no source beats chance (placebo percentiles 16.5 to 17.2) [R]. KPI: all three sources beat both baselines, Wikipedia most (10 of 14, caught 6 of 7 KPI inflections) [R, INF], but none reaches 95. With the KPI-redefinition quarters removed, Wikipedia k falls to 5 of 8 [RB]. This was not predicted, so I treat it as noise until it survives more quarters.

**Useless source here.** TSA for revenue: 7 of 14, placebo percentile 16.5 [R]. Most revenue is non-U.S.

**Structural breaks.** The KPI was redefined from 2025Q2 to add seats for experiences and services (MAJOR for k) [B]; the break-removed k cells have N = 8 (combined 5, "robustness not informative") [RB].

**Live call and base period.** TSA 2026Q4 quarter-to-date d_alt +0.0150; Wikipedia +0.0306 [LV]. The 2025 U.S. base contains the federal lapse in appropriations and FAA flight cuts; without those days the TSA direction holds [S]. The KPI redefinition is in the base too (2025Q4) [LV notes]. **Confidence: low.**

**What would change my mind.** An international (non-U.S.) volume or spend source that clears the placebo test on Nights and Seats Booked.

Sources: [R] outputs/tables/results.csv · [RB] robustness.csv · [LT] lead_time.csv · [INF] inflections_summary.csv · [LV] live_calls.csv · [S] live_tsa_sensitivity.csv (sensitivity, not pre-registered) · [G] config/guidance.yaml · [B] config/breaks.yaml · [D] docs/drivers.md · [H] docs/hypotheses.md
