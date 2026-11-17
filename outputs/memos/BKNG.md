# BKNG — Booking Holdings: alt-data nowcast memo (2026-11-17)

**No detectable signal at n=14, which needed ≥ 11 hits.** At quarter end, TSA called the direction of Booking's revenue right in 8 of 14 quarters and of room nights in 8 of 14; Wikipedia 5 of 14 and 7 of 14; combined 4 of 11 and 5 of 11 [R]. Quarter-end calls are available ~4.6 weeks before the print [LT].

**Current read vs company guidance.** For 2026Q4 TSA, Wikipedia and combined all say *accelerate* [LV]. Booking guides room nights +1% to +3% and Adjusted Revenue 0% to +2%, both below Q3's +7% and +9% [G], so the read is *above guidance*. Companies tend to guide conservatively, so "above guidance" is the common case, and here it rests on sources with no detectable signal.

**What would prove me wrong.** Room-night growth in the Q4 release (estimate 2027-02-17 [LV]) at or below Q3's 7%, i.e. a deceleration.

---

**Debate and the KPI that settles it.** The Q3 release says "global travel demand moderated somewhat toward the end of the third quarter" and its guidance assumes Middle East disruption persists (Q3 2026 release, https://www.sec.gov/Archives/edgar/data/1075531/000107553126000044/q3-26bkngearningsrelease.htm). My view: the debate is whether that softness is temporary; room-night growth settles it.

**Driver tree.** Revenue ≈ room nights × ADR × take rate (+ cars, flights, advertising). Revenue is recognised at check-in, room nights at booking. 90.4% of revenue comes from entities outside the U.S.; FX (EUR, GBP) added about 3 pp to 2025 revenue growth [D].

**Pre-registered hypothesis (quoted).** TSA y: "signal NOT expected" because of "~90% of revenue booked through non-U.S. entities"; TSA k: "Room nights are booking-time and global" [H §5].

**What the data said.** Consistent with the hypothesis. TSA beats momentum by one quarter (8 vs 7 of 14) but its shuffle-placebo percentile is 23.8 (y) and 51.2 (k), far below 95 [R]. TSA caught 3 of 7 revenue inflections [INF]. The magnitude model is worse than "same as last quarter" (MAE 5.34 vs 5.07 pp for y) [R].

**Useless source here.** Wikipedia for revenue: 5 of 14, below momentum's 7 of 14, placebo percentile 3.0 [R]. It measures attention to Booking Holdings and Booking.com, not bookings.

**Structural breaks.** FTC matter: −$900m revenue in 2026Q3 (MAJOR) [B]. With break quarters removed, TSA y is 7 of 13 [RB]. Room nights are published in whole millions; sign(d_k) from levels matched sign from the stated Y/Y in 14 of 14 headline quarters [BK].

**Live call and base period.** TSA 2026Q4 quarter-to-date d_alt +0.0150 (accelerate) [LV]. The 2025 base contains the U.S. federal lapse in appropriations (1 Oct–12 Nov 2025) and FAA flight reductions (7–16 Nov 2025) [G]. Removing those base days leaves the direction unchanged (d_alt +0.0398 and +0.0086) [S]. Hypotheses §3.12: GAAP y for 2026Q3 is −1.28% vs Adjusted Revenue +9%, so the GAAP Q4 direction is mechanically driven by the FTC item; the call has the same sign against Adjusted Revenue [LV]. **Confidence: low** (no source has a detectable signal for BKNG).

**What would change my mind.** A Europe/Asia volume source (e.g. card spend outside the U.S.) that clears the placebo test on room nights.

Sources: [R] outputs/tables/results.csv · [RB] robustness.csv · [LT] lead_time.csv · [INF] inflections_summary.csv · [LV] live_calls.csv · [S] live_tsa_sensitivity.csv (sensitivity, not pre-registered) · [BK] bkng_k_rounding_check.csv · [G] config/guidance.yaml (quotes from the Q3 2026 release snapshot) · [B] config/breaks.yaml · [D] docs/drivers.md · [H] docs/hypotheses.md
