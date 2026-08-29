"""Does the instability floor generalise across models, or is it one model's artefact?

A floor measured on a single model bounds that model. The reviewer's question is whether the
phenomenon is a property of the instrument or of the system under test, and only a second model
answers it.

Two things can generalise independently, and they should be reported separately. The
*magnitude* of the floor is what an audit needs to subtract. The *ordering* of which decisions
are noisy is what a design needs, because it says whether instability attaches to the decision
or to the model making it. A high rank correlation with different magnitudes would mean the
same decisions are hard for both models while each has its own overall noise level, which is a
more useful finding than either number alone.

    python compare_models.py <dir-a> <label-a> <dir-b> <label-b>
"""
from __future__ import annotations

import itertools
import json
import os
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


def _load(d):
    reps = []
    for name in sorted(os.listdir(d)):
        p = os.path.join(d, name, "trajectories.json")
        if not os.path.exists(p):
            continue
        acts = {}
        for t in json.load(open(p, encoding="utf-8"))["trajectories"]:
            if t["complete"] and t["condition_id"] == REFERENCE:
                acts[t["vignette_id"]] = t["actions"]
        if acts:
            reps.append(acts)
    return reps


def floors(d):
    reps = _load(d)
    n = len(reps)
    vign = sorted(set.intersection(*[set(r) for r in reps]))
    per = {k: [0, 0] for k in OUTCOMES}
    fl = to = 0
    for a, b in itertools.combinations(range(n), 2):
        for v in vign:
            for k, proj in OUTCOMES.items():
                x, y = proj(reps[a][v]), proj(reps[b][v])
                if x is None or y is None:
                    continue
                to += 1
                per[k][1] += 1
                if x != y:
                    fl += 1
                    per[k][0] += 1
    return {k: v[0] / v[1] for k, v in per.items()}, fl / to, n, len(vign)


def spearman(xs, ys):
    """Rank correlation over a handful of items, computed directly."""
    def ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        r = [0] * len(vals)
        for pos, i in enumerate(order):
            r[i] = pos + 1
        return r
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1 - (6.0 * d2) / (n * (n * n - 1)), d2


def main(da, la, db, lb):
    fa, pa, na, va = floors(da)
    fb, pb, nb, vb = floors(db)

    print("%-14s %-22s %-22s" % ("", la, lb))
    print("%-14s %-22s %-22s" % ("", "%d reps, %d vignettes" % (na, va),
                                 "%d reps, %d vignettes" % (nb, vb)))
    print()
    keys = sorted(OUTCOMES, key=lambda k: fa[k])
    print("%-14s %-10s %-10s %s" % ("action", la[:9], lb[:9], "difference"))
    for k in keys:
        print("%-14s %-10.3f %-10.3f %+.3f" % (k, fa[k], fb[k], fb[k] - fa[k]))
    print("%-14s %-10.3f %-10.3f %+.3f" % ("POOLED", pa, pb, pb - pa))

    rho, d2 = spearman([fa[k] for k in keys], [fb[k] for k in keys])
    print()
    print("MAGNITUDE: pooled floors %.3f and %.3f, differing by %.3f." % (pa, pb, abs(pa - pb)))
    print("ORDERING : Spearman rank correlation across the six actions = %.2f (sum d^2 = %d)."
          % (rho, d2))
    print()
    quietest_a = min(fa, key=fa.get)
    quietest_b = min(fb, key=fb.get)
    noisiest_a = max(fa, key=fa.get)
    noisiest_b = max(fb, key=fb.get)
    print("   quietest action: %s (%s), %s (%s)" % (quietest_a, la, quietest_b, lb))
    print("   noisiest action: %s (%s), %s (%s)" % (noisiest_a, la, noisiest_b, lb))
    print()
    if rho >= 0.8 and noisiest_a == noisiest_b:
        print("The ordering is preserved and both models agree on which decision is least")
        print("stable, while the overall levels differ. That points at the decision rather")
        print("than the model: the same judgements are hard for both, and each carries its own")
        print("noise level on top. An audit therefore cannot borrow a floor from another")
        print("model's report, but it can expect the same actions to be the unstable ones.")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(*sys.argv[1:]))
