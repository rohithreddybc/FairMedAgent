"""Coverage simulation for the restricted wild cluster bootstrap.

The manuscript reports that the interval covers the true value in 92.5% of replications at
G=8. A reviewer checking the repository found every other quantitative claim in that paragraph
backed by committed code and this one backed by nothing, which is a fair complaint: a number
that cannot be regenerated is a number a reader has to take on trust. This script is the
missing half.

    python wcb_coverage.py [--trials 200] [--clusters 8] [--seed 0]

Data-generating process, stated because coverage is meaningless without it: each of ``G``
clusters draws a cluster-level effect from N(0, 1) and four observations from N(effect, 0.5).
The true mean is therefore 0, and the question is how often the interval contains it. The
design is deliberately one the estimator finds hard -- strong intra-cluster correlation at a
cluster count where asymptotics do not hold.
"""
from __future__ import annotations

import argparse
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fairmedagent.metrics import wild_cluster_bootstrap_ci  # noqa: E402


def one_trial(trial: int, clusters: int, per_cluster: int = 4) -> dict:
    rng = random.Random(trial)
    data = {}
    for i in range(clusters):
        effect = rng.gauss(0.0, 1.0)
        data["v%d" % i] = [effect + rng.gauss(0.0, 0.5) for _ in range(per_cluster)]
    return wild_cluster_bootstrap_ci(data, n_boot=199, grid=31, signed=True, seed=trial)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--clusters", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()

    covered = refused = 0
    widths = []
    for t in range(args.trials):
        ci = one_trial(args.seed + t, args.clusters)
        if ci.get("lo") is None:
            refused += 1
            continue
        widths.append(ci["hi"] - ci["lo"])
        if ci["lo"] <= 0.0 <= ci["hi"]:
            covered += 1

    n = args.trials - refused
    if not n:
        print("every trial was refused; nothing to report")
        return 1
    rate = covered / n
    # Monte Carlo standard error of a proportion, so the reader can see whether a gap from
    # the nominal level is real or is sampling noise in the simulation itself.
    mcse = (rate * (1 - rate) / n) ** 0.5
    print("G=%d, %d trials (%d refused), nominal 95%%" % (args.clusters, args.trials, refused))
    print("coverage of the true mean 0: %d/%d = %.3f" % (covered, n, rate))
    print("Monte Carlo standard error:  %.3f (%.1f percentage points)" % (mcse, 100 * mcse))
    print("mean interval width:         %.3f" % (sum(widths) / len(widths)))
    print()
    print("The small-G literature reports mild under-coverage for this estimator; a result "
          "a little under 0.95 is expected rather than a defect.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
