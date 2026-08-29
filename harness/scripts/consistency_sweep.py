"""Whole-manuscript consistency sweep, run before a submission is packaged.

This manuscript has been through many rounds in which a figure, a claim or a framing was
superseded. Each round risked leaving something behind in a section nobody re-read, and three
times it did: a retracted floor in the contribution bullet, two different pre-registered
vignette counts, and a table caption asserting behaviour the estimator does not have. Each was
found by a human reading carefully, which does not scale and does not repeat.

These are the checks that would have caught them, plus the build hygiene an editor notices.
verify_paper_numbers.py handles the arithmetic; this handles everything else.

    python consistency_sweep.py
"""
from __future__ import annotations

import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
TEX = os.path.join(ROOT, "paper", "main.tex")
LOG = os.path.join(ROOT, "paper", "main.log")
COVER = os.path.join(ROOT, "paper", "cover_letter_jbhi.md")


def main() -> int:
    tex = io.open(TEX, encoding="utf-8").read()
    problems = []
    notes = []

    # --- claims the code does not support -------------------------------------------------
    # The estimator returns a numeric rate with ground_truth false; it does not return NA
    # because a band lacks an adjudicator. A caption asserted otherwise for several rounds.
    for phrase in ("returned NA on every run", "returns NA on the present pilot",
                   "NA on every run to date"):
        if phrase in tex:
            problems.append("claims the estimator returns NA: %r" % phrase)

    # --- cross-references ------------------------------------------------------------------
    labels = set(re.findall(r"\\label\{([^}]*)\}", tex))
    refs = set(re.findall(r"\\(?:ref|autoref|eqref)\{([^}]*)\}", tex))
    for r in sorted(refs - labels):
        problems.append("reference to a label that does not exist: %s" % r)
    unused = labels - refs
    if unused:
        notes.append("labels defined but never referenced: %s" % ", ".join(sorted(unused)))

    # --- citations -------------------------------------------------------------------------
    bib = io.open(os.path.join(ROOT, "paper", "references.bib"), encoding="utf-8").read()
    keys = set(re.findall(r"@\w+\{([^,]+),", bib))
    cited = set()
    for m in re.finditer(r"\\cite\{([^}]*)\}", tex):
        cited |= {k.strip() for k in m.group(1).split(",")}
    for c in sorted(cited - keys):
        problems.append("citation with no bib entry: %s" % c)
    uncited = keys - cited
    if uncited:
        notes.append("%d bib entries never cited" % len(uncited))

    # --- title, running head and cover letter must agree -----------------------------------
    m = re.search(r"\\title\{([^}]*)\}", tex)
    title = m.group(1) if m else ""
    if title:
        cover = io.open(COVER, encoding="utf-8").read() if os.path.exists(COVER) else ""
        # Compare on content words, since the cover letter wraps the title across lines.
        t_words = [w for w in re.findall(r"[A-Za-z-]+", title.lower()) if len(w) > 4]
        c_flat = " ".join(re.findall(r"[A-Za-z-]+", cover.lower()))
        missing = [w for w in t_words if w not in c_flat]
        if missing:
            problems.append("cover letter title does not match the manuscript; missing %s"
                            % ", ".join(missing))

    # --- front matter ----------------------------------------------------------------------
    for ph in ("[AFFILIATION NOT YET SUPPLIED]", "[Affiliation]", "[address]", "Month DD"):
        if ph in tex:
            problems.append("front-matter placeholder still present: %s" % ph)

    # --- build hygiene ---------------------------------------------------------------------
    if os.path.exists(LOG):
        log = io.open(LOG, encoding="utf-8", errors="ignore").read()
        for pat, label in ((r"^!", "LaTeX error"),
                           (r"Reference .* undefined", "undefined reference"),
                           (r"Citation .* undefined", "undefined citation"),
                           (r"multiply defined", "multiply-defined label")):
            n = len(re.findall(pat, log, re.M))
            if n:
                problems.append("%s in the build log: %d" % (label, n))
        bad = [float(x) for x in re.findall(r"Overfull \\hbox \(([0-9.]+)pt", log)]
        wide = [b for b in bad if b > 20]
        if wide:
            notes.append("%d overfull hboxes over 20pt (worst %.0fpt)" % (len(wide), max(wide)))
    else:
        notes.append("no build log; compile before relying on this sweep")

    # --- report ----------------------------------------------------------------------------
    for n in notes:
        print("note     %s" % n)
    if not problems:
        print("\nno consistency problems found.")
        return 0
    print()
    for p in problems:
        print("PROBLEM  %s" % p)
    print("\n%d problem(s)." % len(problems))
    return 1


if __name__ == "__main__":
    sys.exit(main())
