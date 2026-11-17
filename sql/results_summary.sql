-- Name x source relevancy matrix: headline direction cells (quarter-end call), one row per
-- (name, target), one column per source. Cell text = hits/N (minimum hits for one-sided binomial
-- p < 0.05 at that N; momentum-baseline hits on the same quarters; shuffle-placebo percentile), then
-- GREEN if the cell beats both baselines (50% and momentum) AND its placebo percentile is >= 95,
-- else "beats both baselines" when only the first part holds. Not-run cells show their reason.
-- Portable SQL (SQLite and PostgreSQL): || concatenation, CASE pivot, no SQLite-only functions.
SELECT name, target,
       MAX(CASE WHEN source = 'tsa'       THEN cell END) AS tsa,
       MAX(CASE WHEN source = 'caac'      THEN cell END) AS caac,
       MAX(CASE WHEN source = 'hkia'      THEN cell END) AS hkia,
       MAX(CASE WHEN source = 'wikipedia' THEN cell END) AS wikipedia,
       MAX(CASE WHEN source = 'combined'  THEN cell END) AS combined,
       SUM(CASE WHEN green = 1 THEN 1 ELSE 0 END) AS green_cells
FROM (
    SELECT name_order, name, target, source, green,
           CASE WHEN n_realised = 0 THEN status
                ELSE CAST(hits AS VARCHAR(4)) || '/' || CAST(n_realised AS VARCHAR(4))
                     || ' (need ' || COALESCE(CAST(min_hits_p05 AS VARCHAR(4)), 'n/a')
                     || '; momentum ' || CAST(momentum_hits AS VARCHAR(4))
                     || COALESCE('; placebo pct ' || CAST(CAST(placebo_percentile AS INTEGER) AS VARCHAR(4)), '')
                     || ')'
                     || CASE WHEN green = 1 THEN ' GREEN'
                             WHEN beats_both = 1 THEN ' beats both baselines' ELSE '' END
           END AS cell
    FROM results_cells
    WHERE analysis = 'headline' AND model = 'direction'
) t
GROUP BY name_order, name, target
ORDER BY name_order, target DESC;
