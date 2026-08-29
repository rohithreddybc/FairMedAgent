"""Does the aggregation plateau require bimodality, or does ordinary noise produce it too?

The aggregation curve falls fast and then flattens, and it is tempting to read the residue as
evidence that some cells hold two stable answers rather than one answer with noise around it.
That inference does not follow on its own. Majority vote converges at a rate governed by how
far a cell's flip probability sits from one half: cells with extreme probabilities collapse
almost immediately, cells near the boundary barely move at all. A population mixing the two
produces exactly the fast-then-slow shape without any cell being bimodal in the strong sense.

So the observed curve has to be compared against what independent Bernoulli noise alone would
give at the same per-cell rates. This script estimates each cell's success probability from the
observed replicates, simulates fresh replicates under an independent-noise null, applies the
identical disjoint-split majority-vote procedure, and reports the null distribution of the
aggregated floor.

If the observed residue sits inside that distribution, the plateau is explained by ordinary
heterogeneous noise and no bimodality claim is warranted. If it sits above, something beyond
independent sampling is present.

    python plateau_null.py <instability-dir> [--sims 400]
"""
from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

REFERENCE = "ref_white_man_private"
OUTCOMES = {
    "high_acuity":  lambda a: (lambda e: None if e is None else e <= 2)(
        (a.get("triage") or {}).get("esi_acuity")),
    "admit":        lambda a: (a.get("reassess") or {}).get("admit"),
    "escalate_icu": lambda a: (a.get("reassess") or {}).get("escalate_icu"),
    "any_opioid":   lambda a: (lambda t: None if t is None else t >= 2)(
        (a.get("prescribe") or {}).get("analgesia_tier")),
    "cs_caution":   lambda a: (a.get("prescribe") or {}).get("controlled_substance_caution"),
    "referral":     lambda a: (a.get("document") or {}).get("referral"),
}


def _load(out_dir):
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


def _vote(vals):
    vals = [v for v in vals if v is not None]
    if not vals:
        return None
    t = sum(1 for v in vals if v)
    return None if t * 2 == len(vals) else t * 2 > len(vals)


def _splits(n, k):
    seen = set()
    for a in itertools.combinations(range(n), k):
        rest = [i for i in range(n) if i not in a]
        for b in itertools.combinations(rest, k):
            key = tuple(sorted([a, b]))
            if key not in seen:
                seen.add(key)
                yield a, b


def _curve(cells, n, depths):
    """cells maps (vignette, action) -> list of n booleans."""
    out = {}
    for k in depths:
        fl = to = 0
        for a, b in _splits(n, k):
            for series in cells.values():
                x = _vote([series[i] for i in a])
                y = _vote([series[i] for i in b])
                if x is None or y is None:
                    continue
                to += 1
                if x != y:
                    fl += 1
        out[k] = fl / to if to else None
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--sims", type=int, default=400)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    reps = _load(args.out_dir)
    n = len(reps)
    vignettes = sorted(set.intersection(*[set(r) for r in reps]))

    observed_cells = {}
    for v in vignettes:
        for name, proj in OUTCOMES.items():
            series = [proj(r[v]) for r in reps]
            if all(x is not None for x in series):
                observed_cells[(v, name)] = series

    depths = [k for k in (1, 3, 5) if k <= n // 2]
    obs = _curve(observed_cells, n, depths)
    print("observed curve: " + "  ".join("R=%d %.3f" % (k, obs[k]) for k in depths))

    # Per-cell success probability, the only thing the null borrows from the data.
    probs = {key: sum(1 for x in s if x) / len(s) for key, s in observed_cells.items()}
    extreme = sum(1 for p in probs.values() if p in (0.0, 1.0))
    print("cells: %d, of which %d are unanimous across all %d replicates"
          % (len(probs), extreme, n))
    print("simulating %d independent-noise replicate sets...\n" % args.sims)

    rng = random.Random(args.seed)
    null = {k: [] for k in depths}
    for _ in range(args.sims):
        sim_cells = {key: [rng.random() < p for _ in range(n)] for key, p in probs.items()}
        c = _curve(sim_cells, n, depths)
        for k in depths:
            if c[k] is not None:
                null[k].append(c[k])

    print("%-5s %-10s %-22s %s" % ("R", "observed", "independent-noise null", "verdict"))
    for k in depths:
        vals = sorted(null[k])
        lo, hi = vals[int(0.025 * len(vals))], vals[min(len(vals) - 1, int(0.975 * len(vals)))]
        mean = sum(vals) / len(vals)
        inside = lo <= obs[k] <= hi
        print("%-5d %-10.3f mean %.3f  [%.3f, %.3f]  %s"
              % (k, obs[k], mean, lo, hi, "inside" if inside else "OUTSIDE"))

    print()
    deepest = depths[-1]
    vals = sorted(null[deepest])
    lo = vals[int(0.025 * len(vals))]
    hi = vals[min(len(vals) - 1, int(0.975 * len(vals)))]
    if lo <= obs[deepest] <= hi:
        print("At R=%d the observed residue lies inside what independent per-cell noise alone\n"
              "produces. The plateau does NOT require bimodality, and a claim that it does is\n"
              "not supported. The honest statement is that the residue is what heterogeneous\n"
              "flip probabilities predict: cells near the decision boundary converge slowly\n"
              "under majority vote, and averaging cannot remove what is not independent of\n"
              "the case itself." % deepest)
    else:
        print("At R=%d the observed residue lies OUTSIDE the independent-noise null, so\n"
              "something beyond per-cell Bernoulli variation is present." % deepest)
    return 0


if __name__ == "__main__":
    sys.exit(main())
