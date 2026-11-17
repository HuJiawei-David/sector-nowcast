#!/usr/bin/env bash
# Rebuild every output from the committed raw snapshots (no network), then run the tests.
#   bash scripts/run_all.sh
# Network pulls are separate (scripts/s2_pull_sec.py, s3_pull.py, s6_pull_events.py). The locked TCOM 2026Q3
# forward call (scripts/sL_live_tcom.py) is NOT re-run: its output is a timestamped file that must not change.
set -euo pipefail
cd "$(dirname "$0")/.."
PY=.venv/bin/python
PYTHONPATH=src $PY -m nowcast.power >/dev/null
$PY scripts/s2_build.py
$PY scripts/s3_build.py
$PY scripts/s3_charts.py
$PY scripts/s4_evaluate.py
$PY scripts/s5_placebo.py
$PY scripts/s6_live.py
$PY scripts/s8_audit_lookahead.py
$PY scripts/s8_audit_checks.py
$PY scripts/s8_audit_trace.py >/dev/null
.venv/bin/pytest -q
