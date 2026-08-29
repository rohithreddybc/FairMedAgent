"""How much of the instability floor survives majority-vote aggregation?

A reviewer's natural objection to a measured floor is that the fix is one decoding parameter:
pin the temperature to zero and the noise disappears, so a warning aimed at audits that leave
sampling at its default is a warning about bad practice rather than about the instrument. The
objection deserves an answer rather than a citation.

We cannot pin decoding in this environment, so we answer the question the objection is really
asking -- is the instability removable? -- by measuring the other route to removing it. The
protocol already pre-registers R replicates collapsed by majority vote. If the floor collapses
under aggregation, an audit can remove it without any decoding control, and the recommendation
becomes concrete: replicate to this depth. If the floor persists under aggregation, it is not
mere sampling jitter and pinning the temperature is unlikely to be sufficient either.

What this does NOT claim: it is not a simulation of temperature 0. Greedy decoding selects the
argmax token at each position; majority vote selects the modal answer over independent draws.
They are different operations that happen to attack the same variance. The curve below bounds
what replication buys, which is the actionable quantity, and it is reported as that.

The subsets must be DISJOINT. Comparing a majority over replicates {1,2,3} against a majority
over {1,2,4} shares two of three draws and would report agreement driven by the overlap rather
than by aggregation, inflating the apparent benefit. Only splits that share no replicate are
used, which is why the attainable depth is bounded by half the replicate count.

    python aggregation_curve.py <instability-dir>
"""
from __future__ import annotations

import itertools
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REFERENCE = "ref_white_man_private"

BINARY_OUTCOMES = {
    "high_acuity":  lambda a: (lambda e: None if e is None else e <= 2)(
        (a.get("triage") or {}).get("esi_acuity")),
    "admit":        lambda a: (a.get("reassess") or {}).get("admit"),
    "escalate_icu": lambda a: (a.get("reassess") or {}).get("escalate_icu"),
    "any_opioid":   lambda a: (lambda t: None if t is None else t >= 2)(
        (a.get("prescribe") or {}).get("analgesia_tier")),
    "cs_caution":   lambda a: (a.get("prescribe") or {}).get("controlled_substance_caution"),
    "referral":     lambda a: (a.get("document") or {}).get("referral"),
}


def _load(out_dir: str) -> list:
    reps = []
    for name in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, name, "trajectories.json")
        if not os.path.exists(p):
            continue
        acts = {}
        for t in json.load(open(p, encoding="utf-8"))["trajectories"]:
            if t["complete"] and t["condition_id"] == REFERENCE:
                acts[t["vignette_id"]] = t["actions"]
        if acts:
            reps.append(acts)
    return reps


def _vote(values):
    """Majority over an odd-sized group. A tie returns None, never an arbitrary pick."""
    vals = [v for v in values if v is not None]
    if not vals:
        return None
    t = sum(1 for v in vals if v)
    f = len(vals) - t
    if t == f:
        return None
    return t > f


def _disjoint_splits(n: int, k: int):
    """Every unordered pair of disjoint k-subsets of range(n)."""
    seen = set()
    for a in itertools.combinations(range(n), k):
        rest = [i for i in range(n) if i not in a]
        for b in itertools.combinations(rest, k):
            key = tuple(sorted([a, b]))
            if key not in seen:
                seen.add(key)
                yield a, b


def main(out_dir: str) -> int:
    reps = _load(out_dir)
    n = len(reps)
    if n < 2:
        print("need at least two replicates; found %d" % n)
        return 1
    vignettes = sorted(set.intersection(*[set(r) for r in reps]))
    print("replicates %d, vignettes %d\n" % (n, len(vignettes)))

    print("%-6s %-9s %-12s %-9s %s" % ("R", "splits", "flip rate", "flips", "undetermined"))
    curve = []
    for k in range(1, n // 2 + 1):
        if k > 1 and k % 2 == 0:
            continue  # even groups tie; the protocol reports a tie as undetermined
        flips = total = undet = 0
        splits = 0
        for a, b in _disjoint_splits(n, k):
            splits += 1
            for v in vignettes:
                for name, project in BINARY_OUTCOMES.items():
                    xa = _vote([project(reps[i][v]) for i in a])
                    xb = _vote([project(reps[i][v]) for i in b])
                    if xa is None or xb is None:
                        undet += 1
                        continue
                    total += 1
                    if xa != xb:
                        flips += 1
        rate = flips / total if total else None
        curve.append((k, rate))
        print("%-6d %-9d %-12s %-9s %d"
              % (k, splits, "%.3f" % rate if rate is not None else "n/a",
                 "%d/%d" % (flips, total), undet))

    print()
    if len(curve) >= 2 and curve[0][1] and curve[-1][1] is not None:
        first, last = curve[0], curve[-1]
        drop = (first[1] - last[1]) / first[1] * 100 if first[1] else 0
        print("Aggregating from R=%d to R=%d removes %.0f%% of the floor (%.3f -> %.3f)."
              % (first[0], last[0], drop, first[1], last[1]))
        if last[1] > 0:
            print("A residue survives aggregation. That alone does NOT establish bimodality: "
                  "majority vote converges at a rate set by how far a cell sits from p=0.5, "
                  "so heterogeneous rates produce this shape with no cell holding two stable "
                  "answers. Run plateau_null.py to compare against an independent-noise null.")
        else:
            print("The floor is fully removed by aggregation at this depth, so an audit can "
                  "eliminate it by replication without any decoding control.")
    print()
    print("Disjoint splits only. Overlapping subsets would share draws and inflate agreement.")
    print("Depth is bounded by half the replicate count; deeper R needs more replicates.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
