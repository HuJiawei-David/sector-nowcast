import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
HYP = ROOT / "docs" / "hypotheses.md"


def test_hypotheses_ends_with_empty_deviations_heading():
    text = HYP.read_text()
    assert text.rstrip().endswith("## Deviations") or "## Deviations\n" in text
    assert text.count("\n## Deviations") == 1
    assert not re.search(r"<<[A-Z_0-9]+>>", text)


def test_spec_copied_verbatim():
    claude = ROOT / "CLAUDE.md"
    if not claude.exists():
        pytest.skip("CLAUDE.md is local-only (gitignored)")
    c, h = claude.read_text(), HYP.read_text()
    spec = c[c.index("## Model spec"): c.index("## Session protocol")].rstrip("\n")
    r2 = c[c.index("2. POINT-IN-TIME."): c.index("3. FIXED SPECIFICATION.")].rstrip("\n")
    r4 = c[c.index("4. EVALUATION WINDOW"): c.index("5. REPORT EVERYTHING.")].rstrip("\n")
    for block in (spec, r2, r4):
        assert block in h


def test_every_family_cell_has_a_prediction():
    rows = [l for l in HYP.read_text().splitlines() if l.startswith("| ") and "signal" in l]
    assert len(rows) == 40  # 39 family cells + the HKIA fallback cell
