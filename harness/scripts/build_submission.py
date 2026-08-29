"""Assemble the submission package.

IEEE portals want the source, the bibliography, and a compiled PDF, and they are happier with a
.bbl than with a .bib because it removes the need to run BibTeX at their end. Everything else in
the paper directory is build residue and does not belong in the upload.

The manuscript is self-contained: no \\input, no external figure files, and the pipeline figure
is inline TikZ. That is checked here rather than assumed, because a missing dependency is
discovered by the portal rather than by the author.

    python build_submission.py <out.zip>
"""
from __future__ import annotations

import io
import os
import re
import sys
import zipfile
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
PAPER = os.path.join(ROOT, "paper")

#: (path relative to paper/, arcname in the zip, description for the manifest)
ITEMS = [
    ("main.tex", "main.tex", "LaTeX source of the manuscript"),
    ("references.bib", "references.bib", "BibTeX database"),
    ("main.bbl", "main.bbl", "compiled bibliography, so BibTeX need not be re-run"),
    ("main.pdf", "main.pdf", "compiled manuscript, the faithful rendering"),
    ("cover_letter_jbhi.md", "cover_letter.md", "cover letter to the editor"),
    ("FairMedAgent.docx", "FairMedAgent_reading_copy.docx",
     "Word reading copy for co-authors; NOT the submission artifact"),
]


def check_self_contained(tex: str) -> list:
    """Return any external dependency the source still carries."""
    problems = []
    for m in re.finditer(r"\\(?:input|include)\{([^}]*)\}", tex):
        problems.append("\\input/\\include of %r" % m.group(1))
    for m in re.finditer(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]*)\}", tex):
        problems.append("\\includegraphics of %r" % m.group(1))
    return problems


def main(out_zip: str) -> int:
    tex = io.open(os.path.join(PAPER, "main.tex"), encoding="utf-8").read()

    problems = check_self_contained(tex)
    if problems:
        print("manuscript is not self-contained; add these to ITEMS before shipping:")
        for p in problems:
            print("   " + p)
        return 1

    # An editor's first impression is the front matter. Rendered placeholders there read as a
    # manuscript uploaded before anyone finished preparing it, and a desk screen can bounce on
    # that alone. The package refuses to build rather than let them ship silently.
    # Vol.~XX / No.~X are conventional in IEEE submission templates and the journal fills
    # them in; they are not author placeholders. These are.
    # A rendered [Affiliation] is a mistake and blocks. A rendered [Author 3] is a decision
    # the author has made while co-authors are being confirmed, so it warns instead.
    PLACEHOLDERS = ["[AFFILIATION NOT YET SUPPLIED]", "[Affiliation]", "[City]", "[Country]",
                    "[address]", "Month DD", "TODO"]
    WARN_ONLY = ["[Author~3]", "[Author~4]", "[Author 3]", "[Author 4]"]
    found = [ph for ph in PLACEHOLDERS if ph in tex]
    if found:
        print("front matter still contains placeholders; refusing to build the package:")
        for ph in found:
            print("   %s" % ph)
        print()
        print("Complete \submissiondate, \correspondingauthor and \authoraffiliations near")
        print("the top of main.tex, and set the running head, then rebuild.")
        return 1

    pending = sorted({w for w in WARN_ONLY if w in tex})
    if pending:
        print("WARNING: the byline still carries placeholder co-authors: %s"
              % ", ".join(pending))
        print("         The package will build, but do not upload until they are named.")
        print()

    missing = [rel for rel, _, _ in ITEMS if not os.path.exists(os.path.join(PAPER, rel))]
    if missing:
        print("missing from paper/: %s" % ", ".join(missing))
        return 1

    # A manifest, so whoever opens the zip knows what each file is and what it is not.
    lines = [
        "FairMedAgent submission package",
        "built %s" % datetime.now().strftime("%Y-%m-%d %H:%M"),
        "",
        "Contents",
        "--------",
    ]
    for _, arc, desc in ITEMS:
        lines.append("  %-34s %s" % (arc, desc))
    lines += [
        "",
        "Notes",
        "-----",
        "  The manuscript is self-contained: no \\input, no external figure files. The",
        "  pipeline figure is inline TikZ, so the source compiles with pdflatex + bibtex",
        "  and needs no separate graphics.",
        "",
        "  main.bbl is included so the portal does not have to run BibTeX.",
        "",
        "  The Word file is a reading copy for co-authors, generated from the source. It is",
        "  not the submission artifact: citations appear as bracketed keys, equations as",
        "  their source, and the figure is described rather than drawn.",
        "",
        "Before uploading",
        "----------------",
        "  The author block carries placeholders. Complete \\submissiondate,",
        "  \\correspondingauthor and \\authoraffiliations near the top of main.tex, and add",
        "  co-authors with ORCIDs to \\author{}.",
        "",
        "Reproducibility",
        "---------------",
        "  Every number in the manuscript is regenerated from released artifacts.",
        "  harness/scripts/verify_paper_numbers.py recomputes 17 reported quantities from the",
        "  raw trajectory files and asserts each appears in the text as computed.",
    ]
    manifest = "\n".join(lines) + "\n"

    os.makedirs(os.path.dirname(os.path.abspath(out_zip)) or ".", exist_ok=True)
    with zipfile.ZipFile(out_zip, "w", zipfile.ZIP_DEFLATED) as z:
        for rel, arc, _ in ITEMS:
            z.write(os.path.join(PAPER, rel), arc)
        z.writestr("MANIFEST.txt", manifest)

    total = os.path.getsize(out_zip)
    print("wrote %s (%.1f KB)" % (os.path.basename(out_zip), total / 1024.0))
    with zipfile.ZipFile(out_zip) as z:
        for info in z.infolist():
            print("   %-34s %7.1f KB" % (info.filename, info.file_size / 1024.0))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
