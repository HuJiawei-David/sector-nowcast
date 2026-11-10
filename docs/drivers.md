# Revenue drivers, KPIs, guidance and structural breaks

Written in Session 1 (2026-11-10) from each company's latest annual report (10-K for FY2025; 20-F for
FY2025 for TCOM: business section + MD&A + segment/geographic notes) and latest earnings release
(Q3 2026 for the six US names; Q2 2026 for TCOM, whose Q3 2026 results were not yet filed on
2026-11-10). Older 10-Q / 8-K / 6-K filings were read only where needed to source a structural
break. Every document read is stored unmodified under `data/raw/sec_filings/2026-11-10/`, and
EDGAR full-text-search queries under `data/raw/sec_efts/2026-11-10/`.

Revenue-mix shares quoted below are computed by `scripts/s1_geo_mix.py` and stored in
`outputs/tables/geo_mix_fy2025.csv` (inputs transcribed from the filings, source URL per row).
The structural-break list at the end is rendered from `config/breaks.yaml` by
`scripts/render_breaks.py`; the list is frozen at the `prereg` tag.

Timing vocabulary used throughout: **booking-time** = counted when the customer books;
**travel-time** = counted when the trip/stay/delivery happens. TSA counts travel-time US air
departures; CAAC/HKIA count travel-time passengers flown/handled.

Source documents (latest annual report; latest earnings release):

| Name | Annual report | Latest earnings release |
|---|---|---|
| BKNG | [10-K FY2025, filed 2026-02-18](https://www.sec.gov/Archives/edgar/data/1075531/000107553126000009/bkng-20251231.htm) | [8-K Ex-99.1, Q3 2026, filed 2026-11-03](https://www.sec.gov/Archives/edgar/data/1075531/000107553126000044/q3-26bkngearningsrelease.htm) |
| EXPE | [10-K FY2025, filed 2026-02-13](https://www.sec.gov/Archives/edgar/data/1324424/000132442426000008/expe-20251231.htm) | [8-K Ex-99.1, Q3 2026, filed 2026-11-04](https://www.sec.gov/Archives/edgar/data/1324424/000132442426000059/earningsrelease-q32026.htm) + [earnings presentation exhibit](https://www.sec.gov/Archives/edgar/data/1324424/000132442426000059/earningspresentation-q32.htm) |
| ABNB | [10-K FY2025, filed 2026-02-12](https://www.sec.gov/Archives/edgar/data/1559720/000155972026000004/abnb-20251231.htm) | [8-K Ex-99.1, Q3 2026, filed 2026-11-05](https://www.sec.gov/Archives/edgar/data/1559720/000119312526449727/d437988dex991.htm) |
| UBER | [10-K FY2025, filed 2026-02-13](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000015/uber-20251231.htm) | [8-K Ex-99.1, Q3 2026, filed 2026-11-04](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000039/uberq326earningspressrelea.htm) |
| LYFT | [10-K FY2025, filed 2026-02-11](https://www.sec.gov/Archives/edgar/data/1759509/000162828026006960/lyft-20251231.htm) | [8-K Ex-99.1, Q3 2026, filed 2026-11-05](https://www.sec.gov/Archives/edgar/data/1759509/000162828026071043/lyft-20260930xpressrelease.htm) |
| DASH | [10-K FY2025, filed 2026-02-18](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000013/dash-20251231.htm) | [8-K Ex-99.1, Q3 2026, filed 2026-10-29](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000062/proddashex991-pressrelease.htm) |
| TCOM | [20-F FY2025, filed 2026-04-28](https://www.sec.gov/Archives/edgar/data/1269238/000119312526183379/d27369d20f.htm) | [6-K Ex-99.1, Q2 2026, filed 2026-09-16](https://www.sec.gov/Archives/edgar/data/1269238/000119312526392473/d167816dex991.htm) |

---

## BKNG — Booking Holdings

**a. Driver tree.** Revenue ≈ gross bookings × take rate, with gross bookings = room nights ×
ADR (+ rental car days, airline tickets, other). Revenue streams: merchant, agency, advertising &
other (KAYAK, OpenTable). The 10-K describes an ongoing shift from agency to merchant revenue at
Booking.com. Revenue is recognised mainly at check-in, while gross bookings and room nights are
recorded at booking (10-K "Seasonality"), so the booking window shifts revenue between quarters.

**b. KPI and guidance.** Quarterly KPI: **room nights** (also rental car days, airline tickets,
gross bookings). Guidance (Q3 2026 release, for Q4 2026 and FY2026): room-night growth, gross
bookings growth (reported and constant currency), **Adjusted Revenue** growth (reported and
constant currency), Adjusted EBITDA growth, Adjusted EPS growth. Q4 2026: room nights +1% to +3%,
adjusted revenue +0% to +2% (includes about −2% from FX). Guidance is on *Adjusted* revenue, which
differs from GAAP revenue when discrete items occur (e.g. the FTC matter in Q3 2026).

**c. Geography and FX.** Revenue by entity domicile: U.S. 9.6%, outside the U.S. 90.4% (entity
domiciled in the Netherlands 80.6%). The company stresses that this split is by entity, not by
traveller (a U.S. traveller booking a New York hotel on Booking.com is "outside the U.S.").
Room-night growth in 2025 was "driven primarily by increased travel demand in Europe and Asia".
FX: businesses outside the U.S. are "a substantial majority" of results, principally EUR and GBP;
FX added about 3pp to 2025 revenue growth.

**d. Structural breaks 2022Q1–2026Q3.** Getaroom acquisition (Dec 2021; affects only non-clean
2022 YoY values). FTC matter: $900m reduction in GAAP revenue in Q3 2026 (GAAP revenue −1% Y/Y vs
Adjusted Revenue +9%). The attempted Etraveli acquisition did not complete (not a break). No KPI
definition change found.

**e. Implications.** TSA (U.S. departures) measures a small and unidentified slice of Booking's
volume; its demand is Europe/Asia-weighted, and room nights are booking-time while TSA is
travel-time. Revenue additionally moves with EUR/GBP translation and the merchant shift, and has
the Q3 2026 FTC item. → TSA should **not** track revenue, and only weakly (U.S. slice) the room
nights KPI. Wikipedia (Booking Holdings = investor attention; Booking.com = brand) is English
only and dominated by news/earnings attention rather than booking volume → should not track either.

## EXPE — Expedia Group

**a. Driver tree.** Revenue ≈ lodging (booked room nights × ADR × take rate) + air/other +
B2B + trivago advertising + Vrbo traveller fees. Segments: B2C, B2B, trivago. Lodging revenue is
recognised at check-in (Vrbo traveller service fees "recognized at check-in"), while booked room
nights and gross bookings are booking-time.

**b. KPI and guidance.** Quarterly KPI: **booked room nights** (hotel room nights + alternative
accommodation property nights), plus ADR, booked air tickets, gross bookings. Guidance (Q3 2026
earnings presentation, Q4 2026): gross bookings $27.9–28.4bn, revenue $3.69–3.75bn, Adjusted
EBITDA $830–880m, all reported (include FX); full-year 2026 gross bookings, revenue, Adjusted
EBITDA margin expansion.

**c. Geography and FX.** Revenue by website / point-of-sale location: United States 59.1%, all
other countries 40.9% (trivago allocated to Germany). The company hedges part of forecasted merchant
revenue; non-U.S. points of sale give EUR/GBP and other currency translation exposure. B2B (global
partners) is the fastest-growing segment in the latest release (B2B revenue +23% in Q3 2026 vs B2C +6%).

**d. Structural breaks 2022Q1–2026Q3.** Egencia sold 2021-11-01 (affects only non-clean 2022
YoY values). EDGAR full-text search found no other acquisition/disposal of a consolidated
business in 2022–2026 (the 2025 sale of the Despegar equity stake does not touch revenue). No KPI
definition change found.

**e. Implications.** A U.S.-majority point-of-sale mix and check-in revenue recognition make
Expedia the OTA where U.S. travel-time volume (TSA) is most directly aligned with revenue timing:
→ TSA **should** track revenue, weakly (≈41% non-U.S., B2B global, ADR and FX also move it).
Booked room nights are booking-time and increasingly B2B/global → TSA should track the KPI less
well than revenue. Wikipedia (Expedia Group = corporate/investor; Expedia = brand) measures
attention, not bookings → should not track either.

## ABNB — Airbnb

**a. Driver tree.** Revenue ≈ GBV × take rate, GBV = nights and seats booked × ADR. Revenue is
recognised at check-in; "GBV is a leading indicator of revenue" (10-K). Q4 2026 guidance expects
take rate "up slightly" Y/Y.

**b. KPI and guidance.** Quarterly KPI: **Nights and Seats Booked** (booking-time, net of
cancellations), formerly *Nights and Experiences Booked*; since Q2 2025 it adds seats booked for
experiences and services (company: substantially all bookings are nights). Guidance (Q3 2026
release, Q4 2026): revenue $3.22–3.28bn, +16% to +18% Y/Y including ~2pp FX tailwind; GBV growth
"mid-teens"; Nights and Seats Booked "at least low double-digit" growth (qualitative); Adjusted
EBITDA margin direction. FY2026: revenue growth "high teens", Adjusted EBITDA margin ~36%.

**c. Geography and FX.** Revenue by listing location: United States 39.3%, international 60.7%
(no single foreign country ≥10%). FX matters (guidance quotes a ~2pp FX tailwind after hedging).

**d. Structural breaks 2022Q1–2026Q3.** KPI redefinition from Q2 2025 (nights + seats for
experiences and services; affects k only, small by the company's description). No material
acquisition (EDGAR full-text search for completed acquisitions in 2022–2026 returned none).

**e. Implications.** Revenue is travel-time (check-in), but only ~39% comes from U.S. listings
and FX moves the international part → TSA should track revenue only weakly; I do not expect a
detectable direction signal. Nights and Seats Booked are booking-time and 61% international →
TSA should not track the KPI. Wikipedia (Airbnb) is a heavily-read general-interest article
(regulation, news) → should not track either.

## UBER — Uber Technologies

**a. Driver tree.** Revenue = Mobility + Delivery + Freight; Mobility/Delivery revenue ≈ gross
bookings × revenue margin, gross bookings = trips × basket/fare. Revenue margin is repeatedly
moved by business-model choices (principal vs agent, incentives classified as contra revenue).

**b. KPI and guidance.** Quarterly KPI: **Trips** (completed Mobility rides + Delivery orders;
travel-time). Also MAPCs, gross bookings. Guidance (Q3 2026 release, Q4 2026): gross bookings
$63.25–65.25bn (+18% to +22% Y/Y constant currency, ~1pp FX headwind), Adjusted EBITDA
$3.13–3.23bn, non-GAAP EPS. No revenue or trips guidance.

**c. Geography and FX.** FY2025 revenue by region: US & Canada 50.9%, EMEA 31.5%, APAC 11.3%,
LatAm 6.4%; by country: United States 45.7%, United Kingdom 20.4%. Material FX exposure (GBP,
EUR, LatAm and APAC currencies).

**d. Structural breaks 2022Q1–2026Q3.** Many: UK business-model change from 2022-03-14 (gross
Mobility revenue; affects YoY through 2023Q1); contra-revenue business-model changes in some
countries from Q2 2023 (Delivery) and Q3 2023 (Mobility), quantified by the company through Q3
2024 (−8pp on total revenue growth in Q1 2024, −7pp in Q2 2024); Trendyol GO (2025-06-17); a
second UK business-model change effective 2026-01-02 (−8 to −9pp on total revenue growth in
Q1–Q3 2026; Mobility revenue −2% Y/Y in Q3 2026 while trips +16%); SpotHero (2026-04-16), Getir
food delivery (2026-07-01) and control of Careem Technologies (2026-07-31). Pending: Delivery Hero
takeover offer (expected close 2H 2027, outside the window).

**e. Implications.** U.S. is <50% of revenue, Delivery (≈ not travel) is a large share, and
reported revenue growth is dominated in 2023–2024 and 2026 by accounting-model changes a demand
proxy cannot see → TSA should **not** track revenue. Trips (global, mobility + delivery,
travel-time) are a cleaner volume target, but U.S. air travel is a small driver of global trips →
TSA should not track trips either (airport rides are only a slice of U.S. Mobility). Wikipedia
(Uber) is a very high-traffic general article → no expected link.

## LYFT — Lyft

**a. Driver tree.** Revenue ≈ gross bookings − driver payments/incentives (net revenue model);
gross bookings = rides × fare. Revenue is reduced by "investments in driver supply" and by
"certain legal, tax and regulatory reserve changes and settlements" recorded as a reduction to
revenue, so revenue growth can diverge sharply from rides growth.

**b. KPI and guidance.** Quarterly KPI: **Rides** (completed rides that contribute to revenue;
travel-time). Also Active Riders, gross bookings. Guidance (Q3 2026 release, Q4 2026): gross
bookings $5.74–5.94bn (+13% to +17% Y/Y), Adjusted EBITDA $188–213m and margin on gross bookings.
No revenue or rides guidance.

**c. Geography and FX.** FY2025 revenue: United States 95.9%, international 4.1%; international
grows with Freenow (Europe, since 2025-07-31) and TBR (since 2025-10-14), adding EUR/GBP exposure
from 2025Q3.

**d. Structural breaks 2022Q1–2026Q3.** Freenow (2025-07-31) and TBR (2025-10-14) acquisitions
(both y and k); revenue-reducing reserve items of $168m in Q4 2025 (reported revenue +3% Y/Y; the
company says ≈$1.8bn without it) and $69.1m in Q3 2026. A California driver-classification
settlement was announced 2026-09-30 (8-K Item 7.01); its revenue effect, if any, is within the
Q3 2026 reserve item.

**e. Implications.** Lyft is the most U.S.-concentrated name, and rides are travel-time U.S.
volume that partly includes airport trips → TSA **should** track rides (the mechanistically
matched target), weakly. Revenue growth is moved by incentives, reserve items and acquisitions
TSA cannot see → TSA should not track revenue direction reliably. Wikipedia (Lyft) → attention,
not rides; no expected link.

## DASH — DoorDash

**a. Driver tree.** Revenue = Marketplace GOV × net revenue margin (+ Commerce Platform and
advertising); Marketplace GOV = Total Orders × average order value. Net revenue margin was 13.4% in
2025 (10-K).

**b. KPI and guidance.** Quarterly KPI: **Total Orders** (Marketplaces + Commerce Platform;
travel-time, i.e. completion). Guidance (Q3 2026 release, Q4 2026): Marketplace GOV $35.4–36.4bn,
Adjusted EBITDA $900–1,100m. No revenue or orders guidance.

**c. Geography and FX.** FY2025 revenue: United States 83.5%, international 16.5% (Wolt,
Deliveroo — EUR/GBP and other European currencies); international share rises from Q4 2025 with
Deliveroo.

**d. Structural breaks 2022Q1–2026Q3.** Wolt (2022-05-31; y and k through 2023Q2); Symbiosys
(2025-05-28) and SevenRooms (2025-06-13) (y only, small B2B); Deliveroo (2025-10-02; y and k
2025Q4–2026Q3; Q3 2026 revenue +34% reported vs +23% excluding Deliveroo). Announced but not
closed: Instacart (agreement announced in the Q3 2026 release) — not a break inside the window.

**e. Implications.** Local food/grocery delivery is not travel; air-travel throughput has no
mechanical link to orders (if anything, travel moves orders away from home markets) → TSA should
**not** track revenue or orders. Wikipedia (DoorDash) → attention, not orders; no expected link.

## TCOM — Trip.com Group

**a. Driver tree.** Revenue (RMB) = accommodation reservation (41.8% of FY2025 revenue) +
transportation ticketing (36.0%) + packaged tours (7.5%) + corporate travel (4.5%) + other.
Accommodation ≈ room nights × ADR × commission; ticketing ≈ tickets × commission. Recognition:
ticketing commissions when tickets are issued (booking-time); accommodation when the reservation
becomes non-cancelable; packaged tours on departure date (20-F).

**b. KPI and guidance.** No volume KPI is disclosed each quarter (revenue only). Guidance: the
Q1 2026 release guided Q2 2026 net revenue +3% to +8% Y/Y; the latest release (Q2 2026, 6-K filed
2026-09-16) contains **no quantitative guidance** for Q3 2026.

**c. Geography and FX.** Reports in RMB; "the majority of our revenues and costs are denominated
in Renminbi" (20-F). The SAMR fine of RMB3,521m was stated as 7.5% of 2025 PRC sales revenue,
which implies PRC ≈ 75.1% of FY2025 revenue (`outputs/tables/geo_mix_fy2025.csv`; the SAMR revenue
base may be defined differently from reported net revenue, so treat as approximate). The
international platform (Trip.com) grew revenue "by over 50%" Y/Y in Q2 2026.

**d. Structural breaks 2022Q1–2026Q3.** SAMR anti-monopoly case: investigation notified
2026-01-14; a contra-revenue imposed by SAMR reduced Q2 2026 accommodation revenue; decision
received 2026-07-25 (refund of RMB122m deposits, confiscation of RMB1,658m gains, fine RMB3,521m;
the RMB5.2bn total penalty is an expense). The company also cites "operational adjustments ... to
align with evolving industry standards and compliance frameworks" as slowing growth from Q2 2026.
No acquisition of a consolidated business found in the 20-F (the Dec 2024 conversion of Chengdu
Ctrip from VIE to wholly-owned subsidiary is a structure change, not new revenue).

**e. Implications.** CAAC national passenger traffic is travel-time air volume for (mostly
domestic) China — the market that produces ~3/4 of TCOM revenue — and air ticketing plus hotel
demand move with it. TCOM revenue is close to booking-time (tickets at issuance), and Chinese
booking windows are short, so within-quarter overlap is high → CAAC **should** track revenue,
with three caveats: price (airfares, ADR) and take rate move revenue too; the SAMR rectification
from 2026Q2; and monthly publication lags mean the quarter-end call sees fewer than three months.
HKIA (fallback) counts Hong Kong airport passengers — Hong Kong residents, transit and
international traffic — a much smaller and more international slice of TCOM → should track
revenue only weakly. Wikipedia is blocked in mainland China, so English Wikipedia views of Trip.com
Group / Trip.com measure non-mainland (international) attention — a minority of revenue plus
SAMR news spikes → should not track revenue.

---

## Structural-break list (frozen at `prereg`)

Rules: see `config/breaks.yaml` header. Each break is MAJOR or MINOR by the rule in
docs/hypotheses.md section 3.8. A direction call for target quarter q is dropped in the
break-robustness run if y_q or y_{q-1} (k_q or k_{q-1} for the KPI target) is listed in a MAJOR
break for that name and target; MINOR breaks stay listed but are not dropped.

| Name | Event | Type | Materiality | Effective | Targets | Affected YoY quarters | Source filing |
|---|---|---|---|---|---|---|---|
| BKNG | Acquisition of Getaroom (B2B hotel distributor) completed December 2021 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py) | 2021-12 | y | 2021Q4, 2022Q1, 2022Q2, 2022Q3, 2022Q4 (all outside the clean set; listed for completeness) | [bkng-20211231.htm](https://www.sec.gov/Archives/edgar/data/1075531/000107553122000008/bkng-20211231.htm) |
| BKNG | FTC matter: $900 million reduction in revenue recorded in Q3 2026 (excluded from Adjusted Revenue); GAAP revenue -1% Y/Y vs Adjusted Revenue +9% | one_off_revenue | MAJOR (a) type one_off_revenue | 2026Q3 | y | 2026Q3, 2027Q3 | [q3-26bkngearningsrelease.htm](https://www.sec.gov/Archives/edgar/data/1075531/000107553126000044/q3-26bkngearningsrelease.htm) |
| EXPE | Sale of Egencia (corporate travel) to GBT completed 2021-11-01; deconsolidated | disposal | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py) | 2021-11-01 | y, k | 2021Q4, 2022Q1, 2022Q2, 2022Q3, 2022Q4 (all outside the clean set; listed for completeness) | [expe-20221231.htm](https://www.sec.gov/Archives/edgar/data/1324424/000132442423000007/expe-20221231.htm) |
| ABNB | KPI redefined: 'Nights and Experiences Booked' became 'Nights and Seats Booked' (adds seats for experiences and services; services launched in Q2 2025). First used in the Q2 2025 10-Q; company says substantially all bookings are nights | kpi_definition | MAJOR (a) type kpi_definition | 2025Q2 | k | 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | [abnb-20250630.htm](https://www.sec.gov/Archives/edgar/data/1559720/000155972025000025/abnb-20250630.htm) |
| UBER | Acquisition of Transplace (Freight) in Q4 2021 | acquisition | MAJOR (b) company quantifies the effect: "Excluding Transplace, the organic Freight business revenue grew 27% to $396 million." ([uberq421earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315122000004/uberq421earningspressrelea.htm)) | 2021-11 | y | 2021Q4, 2022Q1, 2022Q2, 2022Q3, 2022Q4 (all outside the clean set; listed for completeness) | [uber-20220630.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315122000024/uber-20220630.htm) |
| UBER | UK business model change effective 2022-03-14 (Mobility revenue reported gross); Q1 2022 benefit $200m vs Q1 2023 $1.1bn, Q2 2022 $1.1bn | accounting_model_change | MAJOR (a) type accounting_model_change | 2022-03-14 | y | 2022Q1, 2022Q2, 2022Q3, 2022Q4, 2023Q1 | [uberq123earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315123000013/uberq123earningspressrelea.htm) |
| UBER | Business model changes in some countries classifying certain sales and marketing costs as contra revenue (Delivery from Q2 2023, Mobility from Q3 2023); company quantifies the negative Y/Y revenue impact through Q3 2024 (e.g. -8pp total revenue growth in Q1 2024, -7pp in Q2 2024) | accounting_model_change | MAJOR (a) type accounting_model_change | 2023Q2 | y | 2023Q2, 2023Q3, 2023Q4, 2024Q1, 2024Q2, 2024Q3 | [uberq224earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315124000024/uberq224earningspressrelea.htm)<br>[uberq223earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315123000021/uberq223earningspressrelea.htm)<br>[uberq323earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315123000036/uberq323earningspressrelea.htm)<br>[uberq124earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315124000017/uberq124earningspressrelea.htm)<br>[uberq324earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315124000033/uberq324earningspressrelea.htm) |
| UBER | Acquisition of 85% of Trendyol GO (Turkey delivery) completed 2025-06-17 | acquisition | MAJOR (b) company quantifies the effect: "As a reminder, our outlook includes the contribution from the close of the Trendyol Go acquisition; excluding this, our growth outlook would be 16% to 20% YoY on a constant-currency basis (consistent with the prior quarter)." ([uberq225earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315125000020/uberq225earningspressrelea.htm)) | 2025-06-17 | y, k | 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | [uber-20251231.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000015/uber-20251231.htm) |
| UBER | UK business model change effective 2026-01-02 (Uber no longer responsible for Mobility services in certain UK markets; driver payments become a reduction of revenue); company: -$1.0bn revenue in Q1 2026, -8 to -9pp on total revenue Y/Y growth in Q1-Q3 2026 | accounting_model_change | MAJOR (a) type accounting_model_change | 2026-01-02 | y | 2026Q1, 2026Q2, 2026Q3, 2026Q4 | [uber-20260331.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000022/uber-20260331.htm)<br>[uberq326earningspressrelea.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000039/uberq326earningspressrelea.htm) |
| UBER | Acquisition of SpotHero (parking reservations) completed 2026-04-16 | acquisition | MINOR: the company says SpotHero contributed an immaterial amount of revenue (not quantified); no 'excluding' figure found (EDGAR full-text search, scripts/s1b_materiality_search.py) | 2026-04-16 | y, k | 2026Q2, 2026Q3, 2026Q4, 2027Q1, 2027Q2 | [uber-20260930.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000041/uber-20260930.htm) |
| UBER | Acquisition of Getir's food delivery business (Turkey) completed 2026-07-01 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py) | 2026-07-01 | y, k | 2026Q3, 2026Q4, 2027Q1, 2027Q2 | [uber-20260930.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000041/uber-20260930.htm) |
| UBER | Control of Careem Technologies obtained 2026-07-31 (~60% stake); consolidated from that date | acquisition | MINOR: the company says Careem Technologies contributed an immaterial amount of revenue (not quantified); no 'excluding' figure found (EDGAR full-text search, scripts/s1b_materiality_search.py) | 2026-07-31 | y, k | 2026Q3, 2026Q4, 2027Q1, 2027Q2, 2027Q3 | [uber-20260930.htm](https://www.sec.gov/Archives/edgar/data/1543151/000154315126000041/uber-20260930.htm) |
| LYFT | Acquisition of Freenow (European taxi/multimodal app) completed 2025-07-31 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py); the 10-K says Freenow 'did not contribute a significant amount of revenue' | 2025-07-31 | y, k | 2025Q3, 2025Q4, 2026Q1, 2026Q2, 2026Q3 | [lyft-20251231.htm](https://www.sec.gov/Archives/edgar/data/1759509/000162828026006960/lyft-20251231.htm) |
| LYFT | Acquisition of TBR Global Chauffeuring completed 2025-10-14 | acquisition | MINOR: the company says TBR contributed an immaterial amount of revenue (not quantified); no 'excluding' figure found (EDGAR full-text search, scripts/s1b_materiality_search.py) | 2025-10-14 | y, k | 2025Q4, 2026Q1, 2026Q2, 2026Q3, 2026Q4 | [lyft-20251231.htm](https://www.sec.gov/Archives/edgar/data/1759509/000162828026006960/lyft-20251231.htm) |
| LYFT | Legal, tax and regulatory reserve changes and settlements recorded as a reduction to revenue: $168m in Q4 2025 (revenue +3% Y/Y as reported) | one_off_revenue | MAJOR (a) type one_off_revenue | 2025Q4 | y | 2025Q4, 2026Q4 | [lyft-2025x12x31pressreleas.htm](https://www.sec.gov/Archives/edgar/data/1759509/000162828026006817/lyft-2025x12x31pressreleas.htm) |
| LYFT | Legal, tax and regulatory reserve changes and settlements: $69.1m recorded as a reduction to revenue in Q3 2026 | one_off_revenue | MAJOR (a) type one_off_revenue | 2026Q3 | y | 2026Q3, 2027Q3 | [lyft-20260930xpressrelease.htm](https://www.sec.gov/Archives/edgar/data/1759509/000162828026071043/lyft-20260930xpressrelease.htm) |
| DASH | Acquisition of Wolt completed 2022-05-31 | acquisition | MAJOR (b) company quantifies the effect: "Revenue increased 33% Y/Y to $1.7 billion in Q3 2022 from $1.3 billion, driven by 25% Y/Y growth in DoorDash revenue and the addition of Wolt." ([dashq32022ex991-shareholde.htm](https://www.sec.gov/Archives/edgar/data/1792789/000162828022028194/dashq32022ex991-shareholde.htm)) | 2022-05-31 | y, k | 2022Q2, 2022Q3, 2022Q4, 2023Q1, 2023Q2 | [dash-20220531.htm](https://www.sec.gov/Archives/edgar/data/1792789/000162828022015815/dash-20220531.htm) |
| DASH | Acquisition of Symbiosys (retail media) completed 2025-05-28 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py) | 2025-05-28 | y | 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | [dash-20251231.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000013/dash-20251231.htm) |
| DASH | Acquisition of SevenRooms (restaurant reservation software) completed 2025-06-13 | acquisition | MINOR: no company-quantified effect on revenue, KPI or growth and no 'excluding' figure found (EDGAR full-text search for the acquiree's name, 8-K/10-Q/10-K, scripts/s1b_materiality_search.py); the FY2025 10-K gives one figure for SevenRooms and Deliveroo together (3% of 2025 revenue), which does not isolate SevenRooms | 2025-06-13 | y | 2025Q2, 2025Q3, 2025Q4, 2026Q1, 2026Q2 | [dash-20251231.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000013/dash-20251231.htm) |
| DASH | Acquisition of Deliveroo completed 2025-10-02 ($3,724m); Q3 2026 revenue +34% Y/Y reported vs +23% excluding Deliveroo | acquisition | MAJOR (b) company quantifies the effect: "Excluding Deliveroo, revenue increased 23% Y/Y in Q3 2026." ([proddashex991-pressrelease.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000062/proddashex991-pressrelease.htm)) | 2025-10-02 | y, k | 2025Q4, 2026Q1, 2026Q2, 2026Q3 | [dash-20251231.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000013/dash-20251231.htm)<br>[proddashex991-pressrelease.htm](https://www.sec.gov/Archives/edgar/data/1792789/000179278926000062/proddashex991-pressrelease.htm) |
| TCOM | SAMR anti-monopoly case (investigation notified 2026-01-14; decision 2026-07-25): contra-revenue imposed by SAMR reduced Q2 2026 accommodation revenue; RMB5.2bn penalty (expense, not revenue) | one_off_revenue | MAJOR (a) type one_off_revenue | 2026Q2 | y | 2026Q2, 2027Q2 | [d167816dex991.htm](https://www.sec.gov/Archives/edgar/data/1269238/000119312526392473/d167816dex991.htm)<br>[d256213d6k.htm](https://www.sec.gov/Archives/edgar/data/1269238/000119312526316761/d256213d6k.htm) |
| TCOM | 'Operational adjustments ... to align with evolving industry standards and compliance frameworks' cited by the company as lowering growth from Q2 2026 (Q1 2026 release outlook; Q2 2026 release) | business_practice_change | MAJOR (a) type business_practice_change | 2026Q2 | y | 2026Q2, 2026Q3, 2026Q4, 2027Q1, 2027Q2 | [d163607dex991.htm](https://www.sec.gov/Archives/edgar/data/1269238/000119312526281805/d163607dex991.htm)<br>[d167816dex991.htm](https://www.sec.gov/Archives/edgar/data/1269238/000119312526392473/d167816dex991.htm) |

Searches that found nothing (so nothing is listed): Booking/Etraveli (blocked, never closed);
Expedia 2022–2026 consolidated acquisitions/disposals; Airbnb 2022–2026 completed acquisitions;
TCOM consolidated acquisitions 2022–2025 (20-F). KPI-definition changes other than Airbnb's were
not found in the documents read; definitions were checked in each FY2025 10-K/20-F.
