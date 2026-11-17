# Online travel & mobility: sector memo (2026-11-17)

**One of 39 pre-registered direction cells is GREEN: CAAC called the direction of Trip.com's revenue right in 9 of 9 quarters at quarter end (placebo percentile 99.0), available ~8.1 weeks before the print. 1.95 cells would pass by chance, and no cell has a Benjamini-Hochberg q-value below 0.05** [MT, R, LT]. For the six U.S. names: no detectable signal at n=14, which needed ≥ 11 hits, in any cell that also clears the placebo test [R].

**Current read vs company guidance.** TSA's single 2026Q4 quarter-to-date call is *accelerate* for all six U.S. names (d_alt +0.0150) [LV]. Five of them guide a deceleration (BKNG, EXPE, ABNB, LYFT, DASH), so TSA reads *above guidance* for all five; Uber's guidance midpoint equals its Q3 growth (no label) [LV, G]. Companies tend to guide conservatively, so "above guidance" is the common case. Trip.com's locked Q3 call is *accelerate*; its Q4 guidance is pending [LV].

**What would prove me wrong.** Trip.com's Q3 revenue growth at or below Q2's 5.52% (estimate 2026-11-17); for the U.S. names, Q4 prints that decelerate as guided would make the TSA call wrong for all six at once [LV].

---

**Relevancy matrix (headline, quarter-end; hits/N, need, momentum, placebo percentile)** [R, RM]

| Name | Volume source y / k | Wikipedia y / k | Combined y / k |
|---|---|---|---|
| BKNG | TSA 8/14 · 8/14 | 5/14 · 7/14 | 4/11 · 5/11 |
| EXPE | TSA 10/14 (pct 90.7) · 9/14 | 7/14 · 8/14 | 7/11 · 7/11 |
| ABNB | TSA 7/14 · 9/14 | 6/14 · 10/14 (pct 88.5) | 5/11 · 8/11 |
| UBER | TSA 8/14 · 9/14 | 9/14 · 10/14 (pct 87.2) | 8/11 · 7/11 |
| LYFT | TSA 11/14 (pct 93.8) · 7/12 | 8/14 · 7/12 | 7/11 · 6/11 |
| DASH | TSA 8/14 · 7/14 | 7/14 · 8/14 | 5/11 · 6/11 |
| TCOM | **CAAC 9/9 GREEN** · no KPI | 3/9 · – | 5/6 · – |

US single-source cells need 11 of 14, combined 9 of 11, TCOM 8 of 9 (combined 6 of 6) [P].

**What the sector data says.**
- The only mechanism that survived is the cleanest one: a national air-traffic series for a company whose revenue is ~75% PRC ticketing and hotels [D, R].
- TSA is one U.S. series shared by six names; each quarter it gives all six the same call, so its six cells are one test viewed six ways, not six tests [TD]. Its best cells (LYFT revenue 11/14, EXPE revenue 10/14) fall short of the placebo bar [R]; LYFT revenue was predicted *not* to work [H §5].
- Wikipedia measures attention. Its best cells are KPI cells (ABNB, UBER), neither predicted nor significant [R]; for TCOM it is the worst cell (3/9, placebo percentile 0.0) [R].
- Structural breaks dominate some names: removing Uber's accounting-change quarters leaves N = 1 for revenue [RB].
- Lead time: at quarter end a call is ~4.6–5.4 weeks before a U.S. print and ~8.1 weeks before Trip.com's; at day 56, ~9.7–10.4 and ~13.3 weeks [LT].
- Pandemic quarters are excluded; they are shown in a separate chart (outputs/charts/pandemic_inflections_excluded.png).

**Base period of the live calls.** The 2025Q4 U.S. base contains the federal lapse in appropriations (1 Oct–12 Nov 2025) and FAA flight reductions (7–16 Nov 2025); TSA's direction holds when those base days are removed, where it can be computed [S, G]. Name-level one-offs: BKNG FTC item, LYFT reserves, DASH Deliveroo, UBER U.K. model change [B].

**What would change my mind.** A name-level, non-U.S. source (card spend, app usage) that clears the same pre-registered test; or a run of TCOM misses.

Sources: [R] outputs/tables/results.csv · [RM] relevancy_matrix.csv · [RB] robustness.csv · [MT] multiple_testing.csv · [LT] lead_time.csv · [LV] live_calls.csv · [S] live_tsa_sensitivity.csv · [TD] tsa_dependence.csv · [P] power_table.csv · [G] config/guidance.yaml · [B] config/breaks.yaml · [D] docs/drivers.md · [H] docs/hypotheses.md
