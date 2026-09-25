"""Bootstrap intervals for the per-action instability floor.

The floor is a proportion over pairwise comparisons, and those pairs are not independent: R
replicates give R(R-1)/2 pairs built from the same R draws, and every vignette contributes a
pair to each. Resampling pairs would therefore understate the uncertainty badly. The vignette
is the independent unit here, so the resampling is over vignettes, with all of a vignette's
pairs carried along whenever it is drawn.

    python floor_intervals.py <experiment-dir> [label] [B]

Reports the point estimate and a percentile interval per action and pooled. Intervals are wide
at sixteen vignettes, which is the honest reading and the reason they belong in the paper.
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
    """Replicates as the verifier reads them, so both agree on what a cell is."""
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


def _counts(reps: list[dict], vignettes: list[str]) -> dict[str, list[int]]:
    per = {k: [0, 0] for k in OUTCOMES}
    for a, b in itertools.combinations(range(len(reps)), 2):
        for v in vignettes:
            for k, proj in OUTCOMES.items():
                if v not in reps[a] or v not in reps[b]:
                    continue
                x, y = proj(reps[a][v]), proj(reps[b][v])
                if x is None or y is None:
                    continue
                per[k][1] += 1
                if x != y:
                    per[k][0] += 1
    return per


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(__doc__)
        return 2
    root = argv[1]
    label = argv[2] if len(argv) > 2 else os.path.basename(root)
    B = int(argv[3]) if len(argv) > 3 else 2000

    reps = _reps(root)
    if not reps:
        print("no replicates under %s" % root)
        return 1
    vignettes = sorted(set.intersection(*[set(r) for r in reps]))
    point = _counts(reps, vignettes)

    rng = random.Random(42)
    draws = {k: [] for k in OUTCOMES}
    draws["pooled"] = []
    for _ in range(B):
        sample = [rng.choice(vignettes) for _ in vignettes]
        c = _counts(reps, sample)
        f = sum(c[k][0] for k in OUTCOMES)
        n = sum(c[k][1] for k in OUTCOMES)
        if n:
            draws["pooled"].append(f / n)
        for k in OUTCOMES:
            if c[k][1]:
                draws[k].append(c[k][0] / c[k][1])

    def pct(vals, q):
        vals = sorted(vals)
        return vals[max(0, min(len(vals) - 1, int(q * len(vals))))]

    print("%s: %d replicates, %d vignettes, %d bootstrap resamples over vignettes"
          % (label, len(reps), len(vignettes), B))
    print("%-14s %7s  %s" % ("action", "rate", "95% percentile interval"))
    for k in sorted(OUTCOMES, key=lambda k: point[k][0] / point[k][1] if point[k][1] else 0):
        r = point[k][0] / point[k][1] if point[k][1] else float("nan")
        lo, hi = pct(draws[k], 0.025), pct(draws[k], 0.975)
        print("%-14s %7.3f  [%.3f, %.3f]" % (k, r, lo, hi))
    fp = sum(point[k][0] for k in OUTCOMES)
    np_ = sum(point[k][1] for k in OUTCOMES)
    lo, hi = pct(draws["pooled"], 0.025), pct(draws["pooled"], 0.975)
    print("%-14s %7.3f  [%.3f, %.3f]" % ("POOLED", fp / np_, lo, hi))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
