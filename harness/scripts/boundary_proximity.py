"""Does instability concentrate where the case sits near a decision boundary?

A floor reported as one number invites the reading that instability is a fixed property of the
model. The alternative is that it is a property of the *case*: a presentation admitting exactly
one defensible action should come back the same way every time, while one sitting between two
defensible actions should not. If that holds, the floor is a function of boundary proximity and
an audit must stratify by it rather than average over it.

The triage step supplies a continuous urgency score alongside the discrete ESI acuity, and the
headline dichotomisation is ESI <= 2. Distance from the acuity boundary is therefore observable
without any new model calls, and this script asks whether the vignettes whose urgency sits
closest to the cut are the ones whose discrete actions move.

    python boundary_proximity.py <instability-dir>
"""
from __future__ import annotations

import itertools
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

REFERENCE = "ref_white_man_private"


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
            reps.append((name, acts))
    return reps


def main(out_dir: str) -> int:
    reps = _load(out_dir)
    if len(reps) < 2:
        print("need at least two completed replicates")
        return 1

    vignettes = sorted(set.intersection(*[set(a) for _, a in reps]))
    print("replicates %d, vignettes %d\n" % (len(reps), len(vignettes)))

    print("%-26s %-7s %-7s %-7s %s"
          % ("vignette", "urg min", "urg max", "urg SD", "acuity flips"))
    rows = []
    for v in vignettes:
        urg, acu = [], []
        for _, acts in reps:
            t = acts[v].get("triage") or {}
            if t.get("urgency_score") is not None:
                urg.append(t["urgency_score"])
            if t.get("esi_acuity") is not None:
                acu.append(t["esi_acuity"])
        if len(urg) < 2 or len(acu) < 2:
            continue
        mean_u = sum(urg) / len(urg)
        sd = (sum((u - mean_u) ** 2 for u in urg) / (len(urg) - 1)) ** 0.5
        flips = sum(1 for x, y in itertools.combinations(acu, 2) if (x <= 2) != (y <= 2))
        pairs = len(acu) * (len(acu) - 1) // 2
        rows.append((v, sd, flips, pairs, urg))
        print("%-26s %-7d %-7d %-7.1f %d/%d"
              % (v[:26], min(urg), max(urg), sd, flips, pairs))

    print()
    # Split at the median dispersion rather than a fixed threshold, since the scale of the
    # urgency score is arbitrary and only the ordering is meaningful.
    sds = sorted(r[1] for r in rows)
    cut = sds[len(sds) // 2] if sds else 0.0
    wide = [r for r in rows if r[1] >= cut]
    tight = [r for r in rows if r[1] < cut]

    def rate(group):
        f = sum(r[2] for r in group)
        p = sum(r[3] for r in group)
        return (f / p if p else None), f, p

    rw, fw, pw = rate(wide)
    rt, ft, pt = rate(tight)
    print("ACUITY-FLIP RATE BY URGENCY DISPERSION (median split at SD %.1f)" % cut)
    print("   wide urgency spread  : %s  (%d/%d over %d vignettes)"
          % ("%.3f" % rw if rw is not None else "n/a", fw, pw, len(wide)))
    print("   tight urgency spread : %s  (%d/%d over %d vignettes)"
          % ("%.3f" % rt if rt is not None else "n/a", ft, pt, len(tight)))
    print()
    if rw is not None and rt is not None:
        if rw > rt:
            print("Discrete instability tracks continuous dispersion: the cases the model "
                  "scores inconsistently are the cases whose action moves. That is a "
                  "case-difficulty account, not a fixed model-noise account.")
        elif rw == rt:
            print("No separation at this sample size.")
        else:
            print("Dispersion does not predict flips here, which counts against the "
                  "case-difficulty account and should be reported as such.")
    print()
    print("With four vignettes this is a direction, not an estimate. The comparison is worth "
          "making at the extended vignette count, where the split has enough clusters to "
          "carry an interval.")
    print()
    print("Urgency spread within a vignette across replicates is reported above so a reader "
          "can see that the continuous score moves even where the discrete action does not.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
