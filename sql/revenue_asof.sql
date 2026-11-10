-- Point-in-time revenue (hard rule 2): for each (name, quarter) the latest version whose filing
-- date is strictly before :asof. Ties on the filing date prefer a reported 3-month fact over a
-- YTD-derived value, then the later accession. Portable (window functions: SQLite >= 3.25, PostgreSQL).
-- Python: src/nowcast/revenue.py asof_view() implements the same rule; tests/test_revenue.py checks
-- that the two agree.
SELECT name, quarter, value, unit, filed, accession, form, method
FROM (
    SELECT rv.*,
           ROW_NUMBER() OVER (
               PARTITION BY name, quarter
               ORDER BY filed DESC,
                        CASE method WHEN 'derived_ytd' THEN 1 ELSE 0 END ASC,
                        accession DESC
           ) AS rn
    FROM revenue_versions rv
    WHERE filed < :asof
) t
WHERE rn = 1
ORDER BY name, quarter;
