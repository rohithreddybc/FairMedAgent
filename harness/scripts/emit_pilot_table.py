"""Emit the pilot table: demographic contrasts set against the null-contrast floor.

The table this replaces reported a flip rate per contrast with a bootstrap interval, which
invited the reading that a larger rate means a larger demographic effect. Nothing in that table
told a reader how often the same agent moves when the patient does not change, so nothing in it
could rule that reading out. The floor belongs in the same table as the contrasts it bounds.

    python emit_pilot_table.py <main-trajectories.json> <control-trajectories.json> <out.tex>
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from scripts.compare_null_floor import (  # noqa: E402
    BINARY_OUTCOMES, NULL_CONTRASTS, flips, load,
)

LABELS = {
    "rerender_control": r"identical re-render",
    "sham_attribute_control": r"sham attribute (eye colour)",
    "rare_token_control": r"rare token (invented demonym)",
    "race_black_man_private": r"Black man",
    "white_woman_private": r"White woman",
    "white_man_medicaid": r"White man, Medicaid",
    "white_man_private_lep": r"White man, LEP",
    "black_woman_medicaid": r"Black woman, Medicaid",
}
COLS = ["high_acuity", "admit", "escalate_icu", "any_opioid", "cs_caution", "referral"]
HEADS = {
    "high_acuity": r"ESI$\le$2", "admit": "admit", "escalate_icu": "ICU",
    "any_opioid": r"opioid", "cs_caution": "caution", "referral": "referral",
}


def _row(label: str, d: dict, emph: bool = False) -> str:
    cells = " & ".join("%d/%d" % d[c] for c in COLS)
    total = sum(n for n, _ in d.values())
    denom = sum(m for _, m in d.values())
    name = r"\emph{%s}" % label if emph else label
    return "%s & %s & \\textbf{%d/%d} \\\\" % (name, cells, total, denom)


def main(main_path: str, ctl_path: str, out_path: str) -> int:
    main_arm, ctl_arm = load(main_path), load(ctl_path)
    ref = "ref_white_man_private"

    lines = [
        r"\begin{table}[t]",
        r"\centering",
        r"\caption{\textbf{Preliminary pilot.} Discrete-action flips against the reference "
        r"condition, per outcome, over $N{=}4$ \emph{draft, unadjudicated} vignettes. The "
        r"upper block varies nothing demographic and bounds how much of the lower block is "
        r"resampling noise: the identical re-render flips more often than three of the five "
        r"demographic contrasts. \emph{No disparity is claimed from this table.} The two "
        r"analgesia columns are additionally not interpretable, because the reference arm's "
        r"prescribe-step prompt differed from the comparison arms' (caveat C1 in the released "
        r"artifact). Reproduce with \texttt{harness/scripts/compare\_null\_floor.py}.}",
        r"\label{tab:pilot}",
        r"\footnotesize",
        r"\setlength{\tabcolsep}{3.5pt}",
        r"\begin{tabular}{l" + "c" * len(COLS) + r"c}",
        r"\toprule",
        r"contrast & " + " & ".join(HEADS[c] for c in COLS) + r" & total \\",
        r"\midrule",
        r"\multicolumn{%d}{l}{\emph{null contrasts: no demographic change}} \\"
        % (len(COLS) + 2),
    ]
    for c in NULL_CONTRASTS:
        if c in ctl_arm:
            lines.append(_row(LABELS[c], flips(ctl_arm[ref], ctl_arm[c]), emph=True))
    lines += [
        r"\midrule",
        r"\multicolumn{%d}{l}{\emph{demographic contrasts}} \\" % (len(COLS) + 2),
    ]
    for c in sorted(main_arm):
        if c != ref:
            lines.append(_row(LABELS.get(c, c.replace("_", r"\_")), flips(main_arm[ref],
                                                                          main_arm[c])))
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    print("wrote %s (%d rows)" % (out_path, len(main_arm) - 1 + len(NULL_CONTRASTS)))
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1], sys.argv[2], sys.argv[3]))
