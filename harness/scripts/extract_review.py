"""Print a compact, severity-sorted view of the Pass-1 review findings."""
import json
import sys

data = json.load(open(sys.argv[1], encoding="utf-8"))
reviews = data.get("result", data).get("reviews", [])
order = {"critical": 0, "major": 1, "minor": 2}
for r in reviews:
    persona = (r.get("persona") or "?").split(",")[0].split("—")[0].strip()[:60]
    print(f"\n### {persona}  [{r.get('verdict')}]")
    if r.get("summary"):
        print("  summary:", r["summary"][:280])
    for f in sorted(r.get("findings", []), key=lambda x: order.get(x.get("severity"), 3)):
        print(f"  - [{f.get('severity','?').upper()}] ({f.get('section','?')}) {f.get('issue','')[:300]}")
        print(f"      FIX: {f.get('fix','')[:300]}")
    for mc in r.get("missing_citations", []) or []:
        print(f"  * MISSING CITE: {mc.get('title','?')} [{mc.get('doi_or_arxiv','?')}]: {mc.get('why','')[:200]}")
