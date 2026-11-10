"""SEC EDGAR access (official endpoints only, real User-Agent).

The header pattern and the companyfacts URL pattern are copied from
~/Desktop/Research/Under Review 2/fixed_outputs/scripts/cell4.py (not modified there).
Every response is stored as a raw snapshot (rawstore.save_snapshot) before use.

The User-Agent (real name + contact email, required by the SEC fair-access policy) is read from
the SEC_USER_AGENT environment variable, falling back to a SEC_USER_AGENT=... line in the
repo-root .env file (gitignored; template: .env.example). Request records saved next to each
snapshot redact the contact email; response bodies are untouched.
"""
from __future__ import annotations

import os
import re
import time
from pathlib import Path

import requests

from .rawstore import REPO_ROOT, save_snapshot

ENV_VAR = "SEC_USER_AGENT"
ENV_FILE = REPO_ROOT / ".env"
EMAIL_REDACTION = "<redacted: SEC contact email>"
_EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def _read_env_file(path: Path, key: str) -> str | None:
    """Minimal KEY=VALUE parser (no new dependency): ignores blanks/comments, strips quotes."""
    if not path.exists():
        return None
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip().removeprefix("export ").strip() == key:
            v = v.strip()
            if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
                v = v[1:-1]
            return v or None
    return None


def user_agent(env_file: Path | None = None) -> str:
    ua = os.environ.get(ENV_VAR, "").strip() or _read_env_file(env_file or ENV_FILE, ENV_VAR)
    if not ua:
        raise RuntimeError(
            f"{ENV_VAR} is not set. The SEC requires a User-Agent with a real name and contact "
            f"email. Set the environment variable or add '{ENV_VAR}=Your Name you@example.com' to "
            f"{ENV_FILE} (see .env.example).")
    return ua


def redact_email(s: str) -> str:
    return _EMAIL_RE.sub(EMAIL_REDACTION, s)


def sec_headers() -> dict:
    return {"User-Agent": user_agent()}


_MIN_INTERVAL_S = 0.2  # SEC fair-access limit is 10 requests/second
_last_call = [0.0]


def _get(url: str) -> bytes:
    wait = _MIN_INTERVAL_S - (time.time() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    r = requests.get(url, headers=sec_headers(), timeout=60)
    _last_call[0] = time.time()
    r.raise_for_status()
    return r.content


def fetch(url: str, source: str, name: str, **params) -> tuple[bytes, object]:
    """GET `url`, save the unmodified body under data/raw/<source>/<today>/<name>."""
    content = _get(url)
    recorded = {k: redact_email(v) for k, v in sec_headers().items()}
    path = save_snapshot(source, name, content, {"url": url, "headers": recorded, **params})
    return content, path


def companyfacts_url(cik: int) -> str:
    return f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


def submissions_url(cik: int) -> str:
    return f"https://data.sec.gov/submissions/CIK{cik:010d}.json"


def archive_index_url(cik: int, accession: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/index.json"


def archive_file_url(cik: int, accession: str, filename: str) -> str:
    return f"https://www.sec.gov/Archives/edgar/data/{cik}/{accession.replace('-', '')}/{filename}"
