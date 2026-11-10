"""Render config/breaks.yaml as a markdown table (used in docs/drivers.md and docs/hypotheses.md).
Writes outputs/tables/structural_breaks.md. Materiality: MAJOR (a) by type, MAJOR (b) with the
justifying quote, or MINOR with the reason."""
import sys
sys.path.insert(0, "src")
from nowcast import config

lines = ["| Name | Event | Type | Materiality | Effective | Targets | Affected YoY quarters | Source filing |",
         "|---|---|---|---|---|---|---|---|"]
for b in config.breaks():
    aff = ", ".join(str(q) for q in b["affected_yoy_quarters"])
    if b.get("clean_only_note"):
        aff += " (all outside the clean set; listed for completeness)"
    srcs = [b["source"]] + b.get("other_sources", [])
    src = "<br>".join(f"[{s.rsplit('/', 1)[-1]}]({s})" for s in srcs)
    mat = b["materiality"].upper() + " " + b["materiality_basis"].split(":")[0]
    if b.get("materiality_quote"):
        qs = b["materiality_source"]
        mat += f": \"{b['materiality_quote']}\" ([{qs.rsplit('/', 1)[-1]}]({qs}))"
    elif b["materiality"] == "minor":
        mat = "MINOR: " + b["materiality_basis"].split(": ", 1)[1]
    lines.append(f"| {b['name']} | {b['event']} | {b['type']} | {mat} | {b['effective']} | {', '.join(b['targets'])} | {aff} | {src} |")
md = "\n".join(lines)
open("outputs/tables/structural_breaks.md", "w").write(md + "\n")
print(md)
