"""Assemble paper/references.bib + docs/CITATION_LEDGER.md from the citation-verification workflow output.

Only entries with a resolved DOI/arXiv id AND confidence in {full-text, abstract} enter references.bib.
'unverified' entries are recorded in the ledger as UNVERIFIED and EXCLUDED from the bib (zero-hallucination rule).

Usage: python scripts/assemble_refs.py <workflow-output.json>
"""
import json
import os
import sys

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def main(path):
    data = json.load(open(path, encoding="utf-8"))
    res = data.get("result", data)
    buckets = res.get("results", [])
    labels = res.get("bucketLabels", [f"bucket{i}" for i in range(len(buckets))])

    verified, unverified, seen = [], [], set()
    for lab, b in zip(labels, buckets):
        if not b:
            continue
        for e in (b.get("entries") or []):
            key = e.get("bibkey")
            if not key or key in seen:
                continue
            seen.add(key)
            conf = (e.get("confidence") or "unverified").lower()
            has_id = bool((e.get("doi_or_arxiv") or "").strip())
            (verified if (conf in ("full-text", "abstract") and has_id) else unverified).append((lab, e))

    # references.bib
    bib = ["% FairMedAgent references — VERIFIED entries only (DOI/arXiv resolved via Consensus/Scholar/web).",
           "% Auto-assembled by harness/scripts/assemble_refs.py. Ledger: docs/CITATION_LEDGER.md.",
           f"% {len(verified)} verified entries; {len(unverified)} unverified (excluded — see ledger).", ""]
    for lab, e in verified:
        bib.append(f"% [{lab}] confidence={e.get('confidence')}")
        bib.append((e.get("bibtex") or "").strip())
        bib.append("")
    open(os.path.join(REPO, "paper", "references.bib"), "w", encoding="utf-8").write("\n".join(bib))

    # CITATION_LEDGER.md
    led = ["# FairMedAgent — Citation Ledger",
           "",
           "*Auto-generated from the citation-verification workflow. Rule: only DOI/arXiv-resolved, "
           "full-text/abstract-confidence entries enter `paper/references.bib`. Number-claims must be full-text. "
           "Final pass: `ars-citation-check`.*",
           "",
           f"**{len(verified)} verified** · **{len(unverified)} unverified/excluded**",
           "",
           "| bibkey | conf | DOI/arXiv | supporting finding (verification) |",
           "|---|---|---|---|"]
    for lab, e in verified:
        find = (e.get("supporting_finding") or "").replace("|", "\\|").replace("\n", " ")
        if len(find) > 240:
            find = find[:237] + "..."
        led.append(f"| `{e.get('bibkey')}` | {e.get('confidence')} | {e.get('doi_or_arxiv')} | {find} |")
    if unverified:
        led += ["", "## UNVERIFIED — excluded from references.bib (do NOT cite until resolved)", ""]
        for lab, e in unverified:
            note = (e.get("supporting_finding") or e.get("title") or "").replace("|", "\\|").replace("\n", " ")[:200]
            led.append(f"- [{lab}] `{e.get('bibkey')}` — {e.get('title','?')} — {note}")
    open(os.path.join(REPO, "docs", "CITATION_LEDGER.md"), "w", encoding="utf-8").write("\n".join(led) + "\n")

    print(f"Verified: {len(verified)}  |  Unverified/excluded: {len(unverified)}")
    print("Verified bibkeys:", ", ".join(e.get("bibkey") for _, e in verified))
    if unverified:
        print("UNVERIFIED:", ", ".join(e.get("bibkey") for _, e in unverified))


if __name__ == "__main__":
    main(sys.argv[1])
