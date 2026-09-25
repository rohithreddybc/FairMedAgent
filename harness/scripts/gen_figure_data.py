"""Print the exact data tables the two panel figures need, computed from panel_summary.py.

fig_floor_by_model.tex and fig_per_action.tex are standalone pgfplots documents with a literal
data table pasted into them (they are not \\input from a generated file, to keep the submission
self-contained per build_submission.py's check). This script is the source of truth for that
pasted data, so a reviewer or a future author can regenerate it from experiments/ instead of
hand-editing the numbers in the .tex files.

    python gen_figure_data.py
"""
from __future__ import annotations

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import panel_summary as ps

# Order the floor-by-model figure needs: ascending by pooled floor.
ORDER_BY_LEVEL = None


def main() -> int:
    panel = ps.build_panel(B=600, seed=42)
    by_lab = {row[0]: row for row in panel}

    print("=== fig_floor_by_model.tex data table (ascending by pooled floor) ===")
    print("model        floor  errplus errminus")
    for lab, name, vendor, host, size, R, pooled, lo, hi, rates, worst in sorted(
            panel, key=lambda r: r[6]):
        print("%-12s %.3f  %.3f   %.3f" % (name, pooled, hi - pooled, pooled - lo))

    print()
    print("=== fig_per_action.tex data table ===")
    print("KEYS (alphabetical):", ps.KEYS)
    col_order = ["A", "B", "C", "D", "E", "F"]  # haiku, sonnet, llama, mistral, qwen3, phi3
    row_order = ["escalate_icu", "any_opioid", "referral", "high_acuity", "admit", "cs_caution"]
    print("x y value")
    for yi, k in enumerate(row_order, start=1):
        for xi, lab in enumerate(col_order, start=1):
            rates = by_lab[lab][9]
            r = rates[ps.KEYS.index(k)]
            print("%d %d %.3f" % (xi, yi, r))

    vmax = max(max(row[9]) for row in panel)
    print()
    print("point meta max (overall max rate) = %.3f" % vmax)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
