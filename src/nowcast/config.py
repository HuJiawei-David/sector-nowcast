"""Load config/*.yaml (hard rule 10: companies and sources are configuration, not code)."""
from __future__ import annotations

from pathlib import Path

import yaml

from .quarters import Quarter

REPO_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = REPO_ROOT / "config"


def load_yaml(name: str) -> dict:
    with open(CONFIG_DIR / name, encoding="utf-8") as f:
        return yaml.safe_load(f)


def companies() -> dict:
    return load_yaml("companies.yaml")["companies"]


def sources() -> dict:
    return load_yaml("sources.yaml")["sources"]


def breaks() -> list[dict]:
    return load_yaml("breaks.yaml")["breaks"]


def window(pair, last_reported: Quarter | None = None) -> tuple[Quarter, Quarter] | None:
    """Parse a [start, end] window; end may be 'last_reported'."""
    if pair is None:
        return None
    start, end = pair
    if end == "last_reported":
        if last_reported is None:
            raise ValueError("window ends at 'last_reported' but no last reported quarter was given")
        end_q = last_reported
    else:
        end_q = Quarter.parse(end)
    return Quarter.parse(start), end_q
