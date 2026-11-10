-- Point-in-time KPI levels: for each (name, quarter) the value from the latest earnings release
-- filed strictly before :asof (a later release may restate a prior-year comparative).
SELECT name, quarter, value, unit, release_quarter, filed, accession, source_url
FROM (
    SELECT v.*,
           ROW_NUMBER() OVER (PARTITION BY name, quarter ORDER BY filed DESC, accession DESC) AS rn
    FROM release_values v
    WHERE metric = 'kpi' AND kind = 'value' AND filed < :asof
) t
WHERE rn = 1
ORDER BY name, quarter;
