-- Name x source relevancy matrix: headline direction cells (quarter-end call), one row per
-- (name, target), one column per source. Cell text = hits/N (minimum hits for one-sided binomial
-- p < 0.05 at that N; momentum-baseline hits on the same quarters), flagged when the cell beats both
-- baselines (50% and momentum). Not-run cells show their reason (hard rule 5).
-- Portable SQL (SQLite and PostgreSQL): || concatenation, CASE pivot, no SQLite-only functions.
SELECT name, target,
       MAX(CASE WHEN source = 'tsa'       THEN cell END) AS tsa,
       MAX(CASE WHEN source = 'caac'      THEN cell END) AS caac,
       MAX(CASE WHEN source = 'hkia'      THEN cell END) AS hkia,
       MAX(CASE WHEN source = 'wikipedia' THEN cell END) AS wikipedia,
       MAX(CASE WHEN source = 'combined'  THEN cell END) AS combined
FROM (
    SELECT name_order, name, target, source,
           CASE WHEN n_realised = 0 THEN status
                ELSE CAST(hits AS VARCHAR(4)) || '/' || CAST(n_realised AS VARCHAR(4))
                     || ' (need ' || COALESCE(CAST(min_hits_p05 AS VARCHAR(4)), 'n/a')
                     || '; momentum ' || CAST(momentum_hits AS VARCHAR(4)) || ')'
                     || CASE WHEN beats_both = 1 THEN ' beats both baselines' ELSE '' END
           END AS cell
    FROM results_cells
    WHERE analysis = 'headline' AND model = 'direction'
) t
GROUP BY name_order, name, target
ORDER BY name_order, target DESC;
