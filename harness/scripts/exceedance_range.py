"""Exceedance probability for the pilot's 3-of-4 cell, as a range over the floor's own CI.

Sec. subsec:primary plugs a point estimate of the floor into P(>=3 of 4 flips | floor) and
reports a single number. That overstates precision: the floor itself carries a 95% interval
(Table floor), and the exceedance probability should be reported across it, not at its point
estimate alone. This recomputes P(>=3 of 4) at the low and high end of the pooled and the
cs_caution intervals reported in Table~tab:floor.

    python exceedance_range.py
"""
from __future__ import annotations

from math import comb

POOLED_LO, POOLED_PT, POOLED_HI = 0.056, 0.087, 0.116
CS_LO, CS_PT, CS_HI = 0.06, 0.179, 0.29


def p3(p: float) -> float:
    return comb(4, 3) * p ** 3 * (1 - p) + p ** 4


def main() -> int:
    print("P(>=3 of 4) across the pooled floor's 95%% interval [%.3f, %.3f], point %.3f:"
          % (POOLED_LO, POOLED_HI, POOLED_PT))
    print("  lo  %.4f" % p3(POOLED_LO))
    print("  pt  %.4f" % p3(POOLED_PT))
    print("  hi  %.4f" % p3(POOLED_HI))
    print()
    print("P(>=3 of 4) across the cs_caution floor's 95%% interval [%.2f, %.2f], point %.3f:"
          % (CS_LO, CS_HI, CS_PT))
    print("  lo  %.4f" % p3(CS_LO))
    print("  pt  %.4f" % p3(CS_PT))
    print("  hi  %.4f" % p3(CS_HI))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
