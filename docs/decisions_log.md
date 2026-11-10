# Decisions log — outcomes of pre-registered branches

This file records the outcome of decision rules that docs/hypotheses.md fixes in advance (for
example the HKIA fallback trigger, section 3.6). Recording an outcome here is **not** a deviation
from the pre-registration: the rule and both branches were frozen at the `prereg` tag. Changes of
plan go under "## Deviations" in docs/hypotheses.md instead.

Append-only. Each entry: date, rule (hypotheses.md section), evidence (files under data/raw/ or
outputs/), outcome. An entry must be written before any statistic that depends on its outcome is
computed.

| Date | Rule | Evidence | Outcome |
|---|---|---|---|
| 2026-11-11 | hypotheses.md 3.6, HKIA fallback trigger (first CAAC pull) | `data/raw/caac/2026-11-11/`: 25 listing pages of caac.gov.cn 信息公开 > 统计数据 > 月度运输生产统计 (`listing_p01..p25.html`), 93 bulletin pages `bulletin_2019-01.html` … `bulletin_2026-09.html` and their 93 PDF attachments. Parsed by `src/nowcast/caac.parse()` / `coverage()`: national 旅客运输量 (万人) present for every month 2019-01 … 2026-09 (latest published month; 93 of 93, 0 missing, 0 unparsed); release date (发文日期) recorded from the bulletin page for all 93 months (listing-page date identical for all 93; 0 months on the month-end + 45 days fallback). Coverage checked before any TCOM data was read in this session; no statistic relating CAAC or HKIA to TCOM had been computed. | **Not triggered.** CAAC is TCOM's volume source (single and inside the combined source). HKIA cells are reported as "not run (fallback not triggered)"; HKIA data are not pulled. |
