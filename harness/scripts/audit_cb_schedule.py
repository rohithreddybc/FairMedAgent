"""Write the condition-order schedule for the counterbalanced end-to-end check.

Each of the six orders of (reference, null, demographic) is used twice over twelve replicates, so
every condition occupies every within-replicate position four times. Replicates 1-6 and 7-12 each
take the six orders in a seeded random sequence. The schedule is written once, before any call,
to experiments/audit_cb_schedule.json and is shared by both models.

    python audit_cb_schedule.py
"""
from __future__ import annotations

import itertools
import json
import os
import random
import time

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "..", "experiments", "audit_cb_schedule.json")
SEED = 20261013


def main() -> int:
    if os.path.exists(OUT):
        print("schedule exists, not overwriting:", OUT)
        return 0
    perms = [list(p) for p in itertools.permutations(("reference", "null", "demographic"))]
    rng = random.Random(SEED)
    seq = []
    for _ in range(2):
        block = perms[:]
        rng.shuffle(block)
        seq += block
    orders = {str(r + 1): o for r, o in enumerate(seq)}
    counts = {c: [sum(o[p] == c for o in seq) for p in range(3)] for c in perms[0]}
    assert all(v == [4, 4, 4] for v in counts.values()), counts
    json.dump({"seed": SEED, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "orders": orders, "position_counts": counts}, open(OUT, "w", encoding="utf-8"), indent=1)
    print(json.dumps(orders))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
