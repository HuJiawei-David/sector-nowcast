# Five-minute walkthrough (for a PM and an analyst)

Numbers are from outputs/tables/ (results.csv, multiple_testing.csv, lead_time.csv, live_calls.csv,
power_table.csv) unless named otherwise.

## Script (about 5 minutes)

**1. The question (30 s).** I cover seven online travel and mobility names: Booking, Expedia, Airbnb,
Uber, Lyft, DoorDash and Trip.com. The question is simple. Before the company reports, can free public
data tell me whether revenue growth will speed up or slow down?

**2. The data (40 s).** I used three public sources. U.S. airport security throughput from the TSA,
published daily. China's monthly air-passenger numbers from the CAAC. And English Wikipedia page views
for each company. For the targets I used revenue from SEC filings and each company's headline volume KPI,
like Booking's room nights or Lyft's rides.

**3. The discipline (60 s).** Before downloading any of that data, I wrote down every test: which series,
which model, which quarters, and a prediction for each of 39 cells. I hashed that file and posted the hash
publicly. Then I replayed every quarter from 2023 as if I stood at quarter end, using only data that was
public that day. Each call is scored against the growth the company first reported, and compared with a
naive call: "same direction as last quarter". To count as a signal, a cell must beat that naive call,
beat a coin flip, and beat 95% of 1,000 random shuffles of its own calls.

**4. The result (60 s).** One cell passes: China air traffic for Trip.com. It called the direction of
revenue right in 9 of 9 quarters, about eight weeks before the print. Chance alone would give about two
passing cells out of 39, so I report it as one promising result, not a discovery. For the six U.S. names
there is no detectable signal at this sample size. That fits the plan: I predicted most cells would fail,
because airport traffic is one U.S. series and most of these companies are global, priced, or moved by
accounting changes.

**5. The live calls (50 s).** The same code makes today's calls. Airport traffic says U.S. travel volume is
accelerating in the fourth quarter, even after removing last year's shutdown days. Five of the six U.S.
companies guide a slowdown, so the read is "above guidance". But companies usually guide low, and this
source has no proven record here, so I give it little weight. For Trip.com's third quarter, locked on
November 10, both sources say accelerate; that call is scored the day the company reports.

**6. What I would do next (40 s).** The lesson is that a proxy must match a branch of the driver tree, in
the right country, at the right time. The next step is a name-level source, such as a card-spend or app
panel, tested in the same harness with a new pre-registration.

## The 8 hardest questions

1. **"TSA is public, everyone has it — why does this matter?"** It matters less as an edge than as a
   control: it shows how far a free, crowded series gets you (not far for these names). The value here is
   the harness that tells you, before you pay, whether any proxy beats momentum and chance.
2. **"How is this pre-registered if you already knew the revenue?"** We had seen historical revenue, and the
   pre-registration says so. It fixes the series, models, windows and metrics before seeing any alt data,
   so it guards against trying many specifications until one works, not against knowing the past.
3. **"Nine out of nine sounds too good. Is it luck?"** Possibly: with 39 cells about two pass by chance, and
   its multiple-testing q-value is 0.43. The mechanism is the strongest in the study and the live Q3 call
   is the next real test.
4. **"Lyft revenue got 11 of 14. Why isn't that a finding?"** It fails the shuffle test (93.8th
   percentile), and it was predicted not to work. The six U.S. airport cells are also one series, so a hit
   there is shared by all six names.
5. **"Why direction only, not the number?"** With 9 to 14 quarters, direction is what the sample can test.
   I also ran the magnitude model; it beats "same as last quarter" in only 4 of 26 cells.
6. **"How do you know nothing leaked from the future?"** Each data point carries the date it was published,
   and every feature checks it. Tests multiply all later data by ten, or add fake filings dated on the
   call date, and confirm the call does not move.
7. **"What about one-offs like Booking's FTC charge or Uber's accounting changes?"** They are listed before
   the test with their source documents, and results are rerun without those quarters. For Uber revenue
   that leaves one quarter, so I say the check is not informative.
8. **"Would you trade on the Trip.com call?"** Not on this alone: N is nine, the base quarter was hit by a
   regulatory charge, and there is no company guidance to compare. I would size it as one input and
   watch whether it keeps working.
