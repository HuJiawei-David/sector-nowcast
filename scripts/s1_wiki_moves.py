"""Session 1: for candidate English Wikipedia articles, list every title held since
2019-01-01 (page moves). Read-only metadata; no pageviews are downloaded.

Method: (1) resolve the candidate title (following redirects) to its page id;
(2) read the page's full revision history since 2019-01-01 and keep revisions whose
edit summary records a page move ("moved page [[A]] to [[B]]"); (3) cross-check every
title found against the move log (list=logevents, letype=move, letitle=<title>).
Raw API responses are saved under data/raw/wikipedia_meta/<date>/.
"""
import json, re, sys
sys.path.insert(0, "src")
from nowcast.wikimedia import mw_query

SRC = "wikipedia_meta"
CANDIDATES = sys.argv[1:]
MOVE_RE = re.compile(r"moved page \[\[(.+?)\]\] to \[\[(.+?)\]\]")

def safe(t): return re.sub(r"[^A-Za-z0-9]+", "_", t)

for cand in CANDIDATES:
    j = json.loads(mw_query({"action": "query", "titles": cand, "redirects": 1, "prop": "info"},
                            SRC, f"info_{safe(cand)}.json"))
    q = j["query"]
    page = q["pages"][0]
    redirect = q.get("redirects")
    print(f"\n=== {cand}: pageid={page.get('pageid')} title={page.get('title')} missing={page.get('missing', False)} redirect={redirect}")
    if page.get("missing"):
        continue
    pid = page["pageid"]
    moves, cont, n = [], {}, 0
    while True:
        params = {"action": "query", "pageids": pid, "prop": "revisions", "rvprop": "timestamp|comment",
                  "rvlimit": "max", "rvdir": "newer", "rvstart": "2019-01-01T00:00:00Z", **cont}
        j = json.loads(mw_query(params, SRC, f"revs_{pid}_{n}.json"))
        for rv in j["query"]["pages"][0].get("revisions", []):
            m = MOVE_RE.search(rv.get("comment", ""))
            if m:
                moves.append((rv["timestamp"], m.group(1), m.group(2)))
        if "continue" not in j:
            break
        cont = {k: v for k, v in j["continue"].items()}
        n += 1
    print(f"  revision pages read: {n+1}; move edits since 2019-01-01: {len(moves)}")
    for mv in moves:
        print("   ", mv)
    titles = {page["title"]} | {a for _, a, _ in moves} | {b for _, _, b in moves}
    for t in sorted(titles):
        j = json.loads(mw_query({"action": "query", "list": "logevents", "letype": "move", "letitle": t,
                                 "lestart": "2019-01-01T00:00:00Z", "ledir": "newer", "lelimit": "max"},
                                SRC, f"movelog_{safe(t)}.json"))
        ev = [(e["timestamp"], e["title"], e.get("params", {}).get("target_title")) for e in j["query"]["logevents"]]
        print(f"  move log for '{t}': {ev}")
