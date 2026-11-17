"""Session 7: deliverable structure (memos, README order, CV bullets) and number provenance spot checks."""
import re

import pandas as pd

from nowcast import config
from nowcast.rawstore import REPO_ROOT

MEMOS = REPO_ROOT / "outputs/memos"


def test_one_memo_per_name_plus_sector_with_the_three_lead_lines():
    names = list(config.companies())
    for n in names + ["SECTOR"]:
        text = (MEMOS / f"{n}.md").read_text()
        paras = [p for p in text.split("\n\n") if p.strip() and not p.startswith("#")]
        assert re.search(r"(called the direction of|No detectable signal at n=\d+|GREEN)", paras[0]), n
        assert paras[1].startswith("**Current read vs company guidance.**"), n
        assert paras[2].startswith("**What would prove me wrong.**"), n
        assert len(text.split()) < 900, f"{n} memo longer than about one page"
        assert "no signal" not in text.lower().replace("no detectable signal", ""), n


def test_readme_section_order():
    t = (REPO_ROOT / "README.md").read_text()
    heads = [h for h in re.findall(r"^## (.+)$", t, re.M)]
    assert heads == ["Findings", "Method", "Limitations", "Research tooling", "How to run"]
    assert "3247f30575f3dcf08b329d720f150a72e2937f1d" in t
    assert "28056437cdfd7c3baeb512aeb764adbc25457a0d4562ab0647eee400db35fb4d" in t
    assert "https://gist.github.com/HuJiawei-David/47f6478387d9dd488394a7ffb18f041e" in t


def test_cv_bullets_short_and_numbers_traceable():
    t = (REPO_ROOT / "docs/cv_bullets.md").read_text()
    bullets = [l[2:] for l in t.splitlines() if l.startswith("- ")]
    assert 1 <= len(bullets) <= 3 and all(len(b.split()) < 30 for b in bullets)
    mt = pd.read_csv(REPO_ROOT / "outputs/tables/multiple_testing.csv").iloc[0]
    r = pd.read_csv(REPO_ROOT / "outputs/tables/results.csv")
    tc = r[(r.name == "TCOM") & (r.source == "caac") & (r.target == "y") & (r.model == "direction")].iloc[0]
    assert mt.direction_cells_tested == 39 and mt.green_found == 1 and mt.expected_to_pass_by_chance == 1.95
    assert (tc.hits, tc.N_realised, int(tc.placebo_percentile)) == (9, 9, 99)
    assert len(config.companies()) == 7


def test_readme_matrix_matches_results():
    t = (REPO_ROOT / "README.md").read_text()
    r = pd.read_csv(REPO_ROOT / "outputs/tables/results.csv")
    d = r[(r.model == "direction") & (r.N_realised > 0)]
    for _, x in d.iterrows():
        cell = f"{int(x.hits)}/{int(x.N_realised)} ({int(x.min_hits_p05_realised)}; {int(x.momentum_hits)}; {int(x.placebo_percentile)})"
        assert cell in t, (x["name"], x.source, x.target, cell)
