# CV bullets

- Built a point-in-time alt-data nowcasting harness for 7 travel and mobility stocks; pre-registered 39 tests with a public hash before downloading any alternative data.
  <!-- 7: config/companies.yaml; 39: outputs/tables/multiple_testing.csv (direction_cells_tested) -->
- China air-traffic data called Trip.com revenue direction 9 of 9 quarters (99th placebo percentile), not significant after multiple-testing correction (BH q = 0.43); 1 of 39 passed, 1.95 expected.
  <!-- 9 of 9, 99.0, BH q 0.43 (bh_q_placebo): outputs/tables/results.csv (TCOM caac y); 1, 39, 1.95: outputs/tables/multiple_testing.csv -->
- Every call uses only data published by its date; tests poison later data, and one command rebuilds all outputs byte for byte from saved snapshots.
  <!-- tests/test_evaluate.py, tests/test_live.py; scripts/run_all.sh -->
