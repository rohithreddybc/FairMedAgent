"""Set up and analyse the instability-floor study.

The pilot measured the null contrast once per cell, which establishes that decoding
instability exists but not how large it is. A single draw cannot separate a floor of 0.21 from
one of 0.05 or 0.40, and every disparity this benchmark reports is defined as an excess over
that quantity. So the floor deserves to be estimated properly rather than observed once.

The design is deliberately plain. The reference condition is run ``R`` independent times over
the same vignettes, in separate answering contexts, with nothing varied at all -- same
narrative, same descriptor string, same prompts. Every difference between two runs is
therefore decoding nondeterminism. With ``R`` runs there are ``R(R-1)/2`` pairwise
comparisons, and the spread of their flip rates is the sampling distribution of the null
contrast the pilot saw one draw from.

    python instability_study.py init  <dir> <R>
    python instability_study.py analyse <dir>

``init`` writes one state file per replicate. Each is then driven exactly as the pilot was,
through pilot_driver.py, so the replicates share the pilot's control flow and its guarantee
that the harness built every prompt.
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


def cmd_init(out_dir: str, replicates: str = "6") -> int:
    from scripts.pilot_driver import cmd_init as driver_init
    r = int(replicates)
    os.makedirs(out_dir, exist_ok=True)
    for i in range(1, r + 1):
        rep = os.path.join(out_dir, "rep%02d" % i)
        os.makedirs(rep, exist_ok=True)
        for step in range(1, 6):
            os.makedirs(os.path.join(rep, "ans%d" % step), exist_ok=True)
        driver_init(os.path.join(rep, "state.json"), "0")
    print("initialised %d replicates under %s" % (r, out_dir))
    print("drive each with pilot_driver.py exactly as the pilot was driven; dispatch the "
          "%s split file only" % REFERENCE)
    return 0


def _actions_by_vignette(traj_path: str) -> dict:
    out = {}
    for t in json.load(open(traj_path, encoding="utf-8"))["trajectories"]:
        if t["complete"] and t["condition_id"] == REFERENCE:
            out[t["vignette_id"]] = t["actions"]
    return out


def cmd_analyse(out_dir: str) -> int:
    reps = []
    for name in sorted(os.listdir(out_dir)):
        p = os.path.join(out_dir, name, "trajectories.json")
        if os.path.exists(p):
            acts = _actions_by_vignette(p)
            if acts:
                reps.append((name, acts))
    if len(reps) < 2:
        print("need at least two completed replicates; found %d" % len(reps))
        return 1

    print("replicates: %d   vignettes per replicate: %s"
          % (len(reps), sorted({len(a) for _, a in reps})))
    print()

    per_pair, per_outcome = [], {k: [] for k in BINARY_OUTCOMES}
    for (na, aa), (nb, ab) in itertools.combinations(reps, 2):
        shared = sorted(set(aa) & set(ab))
        flips = total = 0
        for name, project in BINARY_OUTCOMES.items():
            for v in shared:
                x, y = project(aa[v]), project(ab[v])
                if x is None or y is None:
                    continue
                total += 1
                if x != y:
                    flips += 1
                    per_outcome[name].append(1)
                else:
                    per_outcome[name].append(0)
        if total:
            per_pair.append((na, nb, flips, total, flips / total))

    # Cluster-aware interval. Each observation is one (vignette, outcome, replicate-pair)
    # flip indicator; the vignette is the cluster, so a vignette that happens to sit near a
    # decision boundary at every step contributes as one draw rather than as six.
    from fairmedagent.metrics import Pair, cluster_bootstrap_ci

    def _mean_flip(sample):
        vals = [p.score_ref for p in sample if p.score_ref is not None]
        return (sum(vals) / len(vals)) if vals else None

    indicators = []
    for (na, aa), (nb, ab) in itertools.combinations(reps, 2):
        for v in sorted(set(aa) & set(ab)):
            for name, project in BINARY_OUTCOMES.items():
                x, y = project(aa[v]), project(ab[v])
                if x is None or y is None:
                    continue
                indicators.append(Pair(vignette_id=v, score_ref=1.0 if x != y else 0.0))

    ci_lo, ci_hi = cluster_bootstrap_ci(indicators, _mean_flip, n_boot=2000, seed=0)

    rates = sorted(r for *_, r in per_pair)
    n = len(rates)
    mean = sum(rates) / n
    lo, hi = rates[int(0.025 * n)], rates[min(n - 1, int(0.975 * n))]
    print("PAIRWISE NULL CONTRASTS (identical descriptor, independent draws)")
    for na, nb, f, t, r in per_pair:
        print("   %-7s vs %-7s  %2d/%-3d = %.3f" % (na, nb, f, t, r))
    print()
    print("   pairs compared      : %d" % n)
    print("   mean null flip rate : %.3f" % mean)
    print("   range               : %.3f to %.3f" % (rates[0], rates[-1]))
    print("   spread across pairs : %.3f to %.3f  (pairs share replicates; not an interval)"
          % (lo, hi))
    if ci_lo is not None:
        print("   cluster bootstrap   : [%.3f, %.3f]  (percentile, clustered on vignette, "
              "G=%d)" % (ci_lo, ci_hi, len({p.vignette_id for p in indicators})))
    else:
        print("   cluster bootstrap   : refused (%s)"
              % (getattr(cluster_bootstrap_ci, "last_refusal", None) or {}).get("reason"))
    print()
    print("PER-OUTCOME NULL RATE")
    for name, vals in per_outcome.items():
        if vals:
            print("   %-14s %.3f  (%d/%d)" % (name, sum(vals) / len(vals), sum(vals), len(vals)))
    print()
    print("Any demographic contrast at or below the upper end of this range is not "
          "distinguishable from decoding noise at this sample size.")
    return 0


if __name__ == "__main__":
    cmds = {"init": cmd_init, "analyse": cmd_analyse}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        print(__doc__)
        sys.exit(2)
    sys.exit(cmds[sys.argv[1]](*sys.argv[2:]))
