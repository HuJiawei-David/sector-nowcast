"""Raw snapshot store (hard rule 8).

Every external pull is saved unmodified under data/raw/<source>/<pull_date>/ together
with a JSON sidecar holding its request parameters. Large payloads may be gzip-compressed
(lossless). Downstream code reads snapshots, never the live API.
"""
from __future__ import annotations

import datetime as dt
import gzip
import hashlib
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
GZIP_THRESHOLD_BYTES = 1_000_000


def snapshot_dir(source: str, pull_date: dt.date | None = None) -> Path:
    pull_date = pull_date or dt.date.today()
    d = RAW_DIR / source / pull_date.isoformat()
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_snapshot(source: str, name: str, content: bytes, params: dict,
                  pull_date: dt.date | None = None) -> Path:
    """Save `content` byte-for-byte (gzip if large) plus `<name>.request.json`."""
    d = snapshot_dir(source, pull_date)
    path = d / name
    if len(content) > GZIP_THRESHOLD_BYTES:
        path = d / (name + ".gz")
        with gzip.open(path, "wb", compresslevel=9) as f:
            f.write(content)
    else:
        path.write_bytes(content)
    meta = dict(params)
    meta.update({
        "pulled_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "sha256_uncompressed": hashlib.sha256(content).hexdigest(),
        "bytes_uncompressed": len(content),
        "stored_as": path.name,
    })
    (d / (name + ".request.json")).write_text(json.dumps(meta, indent=2, sort_keys=True))
    return path


def read_snapshot(path: Path) -> bytes:
    path = Path(path)
    if path.suffix == ".gz":
        with gzip.open(path, "rb") as f:
            return f.read()
    return path.read_bytes()
