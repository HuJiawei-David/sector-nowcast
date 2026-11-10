"""Wikimedia API access (read-only). Every response is saved as a raw snapshot first."""
from __future__ import annotations

import time
import urllib.parse

import requests

from .rawstore import save_snapshot

# Descriptive User-Agent per the Wikimedia User-Agent policy.
WIKI_HEADERS = {"User-Agent": "sector-nowcast-research/0.1 (non-commercial research tool; python-requests)"}
MW_API = "https://en.wikipedia.org/w/api.php"


def mw_query(params: dict, source: str, name: str) -> bytes:
    params = {"format": "json", "formatversion": "2", **params}
    url = MW_API + "?" + urllib.parse.urlencode(params)
    for attempt in range(6):
        r = requests.get(url, headers=WIKI_HEADERS, timeout=60)
        if r.status_code != 429:
            break
        time.sleep(float(r.headers.get("Retry-After", 0)) or 10 * (attempt + 1))
    r.raise_for_status()
    save_snapshot(source, name, r.content, {"url": url, "params": params, "headers": WIKI_HEADERS})
    time.sleep(1.5)
    return r.content
