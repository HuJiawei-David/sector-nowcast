"""Session 3: pull alt-data snapshots (network). Raw responses -> data/raw/<source>/<pull_date>/.

    .venv/bin/python scripts/s3_pull.py [wikipedia] [tsa] [caac]

HKIA is NOT pulled: the pre-registered trigger (hypotheses.md 3.6) did not fire
(docs/decisions_log.md, 2026-11-11).
"""
import datetime as dt
import sys
import time

sys.path.insert(0, "src")
from nowcast import caac, tsa, wiki  # noqa: E402

which = set(sys.argv[1:]) or {"wikipedia", "tsa", "caac"}
if "wikipedia" in which:
    print(len(wiki.pull()), "Wikipedia title snapshots")
if "tsa" in which:
    keys = ["current"] + [str(y) for y in range(2019, dt.date.today().year)]
    status = {}
    for k in keys:
        status.update(tsa.fetch([k]))
        time.sleep(1)
    print("TSA HTTP status:", status)
    if any(v != 200 for v in status.values()):
        raise SystemExit("TSA: some pages were not retrieved (see *.http<status>.html); stop, do not substitute a source")
if "caac" in which:
    print(len(caac.pull()), "CAAC bulletins")
