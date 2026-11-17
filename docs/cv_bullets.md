# CV bullets

- Built a point-in-time alt-data nowcasting harness for 7 travel and mobility stocks; pre-registered 39 tests with a public hash before downloading any alternative data.
  <!-- 7: config/companies.yaml; 39: outputs/tables/multiple_testing.csv (direction_cells_tested) -->
- China air-traffic data called Trip.com revenue direction in 9 of 9 quarters (99th placebo percentile); reported that 1 of 39 cells passed versus 1.95 expected by chance.
  <!-- 9 of 9, 99.0: outputs/tables/results.csv (TCOM caac y); 1, 39, 1.95: outputs/tables/multiple_testing.csv -->
- Every call uses only data published by its date; tests poison later data, and one command rebuilds all outputs byte for byte from saved snapshots.
  <!-- tests/test_evaluate.py, tests/test_live.py; scripts/run_all.sh -->
