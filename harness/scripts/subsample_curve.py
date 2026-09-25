"""How much does the pooled floor's interval narrow between four and sixteen vignettes?

The paper says the four-vignette estimate was "simply wrong" and reports the sixteen-vignette
figure as the replacement, but never shows the trajectory between those two points, so a
reviewer has no way to tell whether sixteen is a converged estimate or just a bigger unstable
one. This script answers that directly: fix one random order of the sixteen vignettes actually
run, take the first K of them for K in {4, 8, 12, 16}, and report the pooled point estimate and
a percentile bootstrap interval (resampled over vignettes, same method as floor_intervals.py)
at each K, using the same ten replicates throughout so only the vignette count changes.

    python subsample_curve.py <experiment-dir> [B] [seed]
"""
from __future__ import annotations

import itertools
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))

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

REFERENCE = "ref_white_man_private"


def _reps(root: str) -> list[dict]:
    out = []
    for name in sorted(os.listdir(root)):
        path = os.path.join(root, name, "trajectories.json")
        if not os.path.exists(path):
            continue
        acts = {}
        for t in json.load(open(path, encoding="utf-8"))["trajectories"]:
            if t["complete"] and t["condition_id"] == REFERENCE:
                acts[t["vignette_id"]] = t["actions"]
        if acts:
            out.append(acts)
    return out


def _pooled_point(reps: list[dict], vignettes: list[str]) -> tuple[int, int]:
    flips = total = 0
    for a, b in itertools.combinations(range(len(reps)), 2):
        for v in vignettes:
            for k, proj in OUTCOMES.items():
                if v not in reps[a] or v not in reps[b]:
                    continue
                x, y = proj(reps[a][v]), proj(reps[b][v])
                if x is None or y is None:
                    continue
                total += 1
                if x != y:
                    flips += 1
    return flips, total


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = argv[1]
    B = int(argv[2]) if len(argv) > 2 else 2000
    seed = int(argv[3]) if len(argv) > 3 else 42

    reps = _reps(root)
    if not reps:
        print("no replicates under %s" % root)
        return 1
    all_vignettes = sorted(set.intersection(*[set(r) for r in reps]))

    order_rng = random.Random(seed)
    order = list(all_vignettes)
    order_rng.shuffle(order)

    print("subsample curve over %s: %d replicates, %d vignettes total, order seed=%d"
          % (os.path.basename(root), len(reps), len(all_vignettes), seed))
    print("%-4s %9s %10s %9s" % ("K", "flips/n", "rate", "95% CI"))

    boot_rng = random.Random(seed)
    rows = []
    for K in (4, 8, 12, 16):
        if K > len(order):
            continue
        subset = order[:K]
        flips, total = _pooled_point(reps, subset)
        if total == 0:
            print("%-4d n/a (no comparisons)" % K)
            continue
        rate = flips / total

        draws = []
        for _ in range(B):
            sample = [boot_rng.choice(subset) for _ in subset]
            f, t = _pooled_point(reps, sample)
            if t:
                draws.append(f / t)
        draws.sort()
        lo = draws[max(0, int(0.025 * len(draws)))]
        hi = draws[min(len(draws) - 1, int(0.975 * len(draws)))]
        width = hi - lo
        rows.append((K, flips, total, rate, lo, hi, width))
        print("%-4d %4d/%-4d %9.3f  [%.3f, %.3f]  width=%.3f"
              % (K, flips, total, rate, lo, hi, width))

    if len(rows) >= 2:
        first, last = rows[0], rows[-1]
        print()
        print("interval width at K=%d: %.3f; at K=%d: %.3f (%.0f%% narrower)"
              % (first[0], first[6], last[0], last[6],
                 100 * (1 - last[6] / first[6]) if first[6] else 0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
