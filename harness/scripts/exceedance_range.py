"""Probability of at least 3 flips in 4 vignettes under the floor, as a range over its interval.

For a cell with four vignettes, P(>=3 of 4 flips | floor) is evaluated at the low end, the point
estimate and the high end of the floor's 95% interval, for the five-action pooled floor, the
six-action pooled floor and the controlled-substance caution flag alone (model A). A point
estimate alone would overstate precision.

    python exceedance_range.py
"""
from __future__ import annotations

from math import comb

import os

# Five defined actions, model A (experiments/robustness_v3.json item 9, vignette bootstrap): 0.068 [0.036, 0.101].
POOLED_LO, POOLED_PT, POOLED_HI = 0.036, 0.068, 0.101
# Six-action pooled floor for model A, shown for comparison: 0.087 [0.056, 0.116].
SIX_LO, SIX_PT, SIX_HI = 0.056, 0.087, 0.116
# Controlled-substance caution flag alone (exploratory output), model A.
CS_LO, CS_PT, CS_HI = 0.06, 0.179, 0.29


def p3(p: float) -> float:
    return comb(4, 3) * p ** 3 * (1 - p) + p ** 4


def main() -> int:
    print("P(>=3 of 4), five-action pooled floor, 95%% interval [%.3f, %.3f], point %.3f:"
          % (POOLED_LO, POOLED_HI, POOLED_PT))
    print("  lo  %.4f" % p3(POOLED_LO))
    print("  pt  %.4f" % p3(POOLED_PT))
    print("  hi  %.4f" % p3(POOLED_HI))
    print()
    print("P(>=3 of 4), six-action pooled floor, 95%% interval [%.3f, %.3f], point %.3f:"
          % (SIX_LO, SIX_HI, SIX_PT))
    print("  lo  %.4f" % p3(SIX_LO))
    print("  pt  %.4f" % p3(SIX_PT))
    print("  hi  %.4f" % p3(SIX_HI))
    print()
    print("P(>=3 of 4), cs_caution flag alone, 95%% interval [%.2f, %.2f], point %.3f:"
          % (CS_LO, CS_HI, CS_PT))
    print("  lo  %.4f" % p3(CS_LO))
    print("  pt  %.4f" % p3(CS_PT))
    print("  hi  %.4f" % p3(CS_HI))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
