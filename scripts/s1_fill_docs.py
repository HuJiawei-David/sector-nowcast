"""Session 1: fill placeholders in docs/drivers.md and docs/hypotheses.md.
<<MODEL_SPEC>>, <<RULE_2>>, <<RULE_4>> are copied verbatim from CLAUDE.md (fenced, so whitespace is
preserved); <<POWER_TABLE>> from outputs/tables/power_table.md; <<BREAKS_TABLE>> from
outputs/tables/structural_breaks.md. One-shot: does nothing once the placeholders are gone."""
import re
from pathlib import Path

claude = Path("CLAUDE.md").read_text()

def between(text, start_pat, end_pat):
    m1 = re.search(start_pat, text, re.M)
    m2 = re.search(end_pat, text[m1.start():], re.M)
    return text[m1.start(): m1.start() + m2.start()].rstrip("\n")

spec = between(claude, r"^## Model spec", r"^## Session protocol")
rule2 = between(claude, r"^2\. POINT-IN-TIME\.", r"^3\. FIXED SPECIFICATION\.")
rule4 = between(claude, r"^4\. EVALUATION WINDOW", r"^5\. REPORT EVERYTHING\.")
fence = lambda s: "```text\n" + s + "\n```"
repl = {
    "<<MODEL_SPEC>>": fence(spec),
    "<<RULE_2>>": fence(rule2),
    "<<RULE_4>>": fence(rule4),
    "<<POWER_TABLE>>": Path("outputs/tables/power_table.md").read_text().rstrip("\n"),
    "<<BREAKS_TABLE>>": Path("outputs/tables/structural_breaks.md").read_text().rstrip("\n"),
}
for doc in ["docs/drivers.md", "docs/hypotheses.md"]:
    t = Path(doc).read_text()
    for k, v in repl.items():
        t = t.replace(k, v)
    Path(doc).write_text(t)
    left = re.findall(r"<<[A-Z_0-9]+>>", t)
    print(doc, "remaining placeholders:", left)
