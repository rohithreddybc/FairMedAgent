"""Catch mangled LaTeX control sequences before they reach a compiled PDF.

This exists because the same defect occurred three times in one editing session. A Python
string written as "Sec.~\\ref{...}" inside a shell heredoc loses a backslash somewhere in the
quoting chain, and `\\r` becomes a carriage return. The result is `Sec.~<CR>ef{...}`, which
LaTeX renders as the literal text "ef{subsec:limitations}" in the output. It compiles cleanly,
produces no warning, and no undefined-reference error, because from LaTeX's point of view
there is no reference there at all -- just a word.

That combination, invisible to the build and visible to a reader, is exactly what a lint is
for. Run it before circulating a PDF.

Usage:  python harness/scripts/latex_lint.py [paper/main.tex]
Exit code is the number of defects found, so it can gate a build.
"""
from __future__ import annotations

import os
import re
import sys

BS = chr(92)
CR = chr(13)
LF_ = chr(10)

# Control sequences whose names begin with a character Python treats as a string escape.
# These are the ones a quoting accident silently decapitates.
AT_RISK = {
    "r": ["ref", "right", "rule", "raggedright", "renewcommand"],
    "n": ["newcommand", "newline", "noindent", "not", "nu"],
    "t": ["textbf", "textit", "texttt", "table", "textcolor", "tabular", "textsuperscript"],
    "b": ["begin", "bibliography", "bibliographystyle", "bf", "bottomrule"],
    "f": ["frac", "final", "footnote", "figure"],
    "a": ["author", "and", "alpha", "abstract"],
    "v": ["vspace", "vfill"],
}


def lint(path: str) -> list:
    with open(path, encoding="utf-8", newline="") as fh:
        src = fh.read()

    findings = []

    # 1. A stray carriage return that is not part of a CRLF line ending. Almost always the
    #    corpse of a "\r..." control sequence.
    for m in re.finditer(CR + r"(?!\n)", src):
        line = src.count("\n", 0, m.start()) + 1
        ctx = src[max(0, m.start() - 40):m.start() + 40].replace(CR, "<CR>").replace("\n", " ")
        findings.append((line, "stray carriage return (probable mangled control sequence)", ctx))

    # 2. A CR or LF sitting immediately before the tail of an at-risk control sequence, where
    #    the preceding text ends in a way that wanted a macro (a tie, a brace, a space).
    for first, names in AT_RISK.items():
        for name in names:
            tail = name[1:]
            # The break may be CR, LF, or CRLF. Matching a single character is how an
            # earlier version of this lint reported "clean" on the very defect it was
            # written to catch.
            brk = "(?:" + CR + LF_ + "|" + CR + "|" + LF_ + ")"
            for m in re.finditer(r"[~{} ]" + brk + re.escape(tail) + r"\{", src):
                line = src.count("\n", 0, m.start()) + 1
                ctx = src[max(0, m.start() - 40):m.start() + 40].replace(CR, "<CR>").replace("\n", " ")
                findings.append((line, "decapitated " + BS + name + " (leading character eaten)", ctx))

    # 3. A bare macro tail immediately after a tie, which is how a broken cross-reference reads.
    for m in re.finditer(r"~(ref|cite|eqref)\{", src):
        line = src.count("\n", 0, m.start()) + 1
        ctx = src[max(0, m.start() - 40):m.start() + 40].replace("\n", " ")
        findings.append((line, "missing backslash before " + m.group(1), ctx))

    return findings


def main(argv) -> int:
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    path = argv[1] if len(argv) > 1 else os.path.join(root, "paper", "main.tex")
    findings = lint(path)
    if not findings:
        print("latex_lint: clean (%s)" % os.path.relpath(path, root))
        return 0
    print("latex_lint: %d defect(s) in %s" % (len(findings), os.path.relpath(path, root)))
    for line, what, ctx in findings:
        print("  line %-5d %s" % (line, what))
        print("            ...%s..." % ctx.strip())
    return len(findings)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
