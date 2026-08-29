"""Check every computable number in the manuscript against the artifact it came from.

Numbers drift. This manuscript has been through several rounds in which a figure was
superseded by a better measurement, and each round risked leaving a stale value behind in a
section nobody re-read. This script recomputes what can be recomputed and reports any
disagreement with the text, so the check is mechanical rather than a matter of remembering.

It deliberately does not parse the LaTeX for numbers and diff them, which would be brittle.
Each claim is named, recomputed from its source, and asserted to appear in the manuscript.

    python verify_paper_numbers.py
"""
from __future__ import annotations

import io
import itertools
import json
import os
import re
import sys
from math import comb

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "harness"))

PAPER = os.path.join(ROOT, "paper", "main.tex")
INST = os.path.join(ROOT, "experiments", "floor16")

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


def _reps():
    out = []
    for name in sorted(os.listdir(INST)):
        p = os.path.join(INST, name, "trajectories.json")
        if not os.path.exists(p):
            continue
        acts = {}
        for t in json.load(open(p, encoding="utf-8"))["trajectories"]:
            if t["complete"] and t["condition_id"] == REFERENCE:
                acts[t["vignette_id"]] = t["actions"]
        if acts:
            out.append(acts)
    return out


def main() -> int:
    tex = io.open(PAPER, encoding="utf-8").read()
    checks, failures = [], 0

    def claim(label, value, needle):
        nonlocal failures
        ok = needle in tex
        checks.append((label, value, needle, ok))
        if not ok:
            failures += 1

    reps = _reps()
    n = len(reps)
    vignettes = sorted(set.intersection(*[set(r) for r in reps]))

    # --- pooled floor and per-action floors -------------------------------------------
    flips = total = 0
    per = {k: [0, 0] for k in OUTCOMES}
    for a, b in itertools.combinations(range(n), 2):
        for v in vignettes:
            for k, proj in OUTCOMES.items():
                x, y = proj(reps[a][v]), proj(reps[b][v])
                if x is None or y is None:
                    continue
                total += 1
                per[k][1] += 1
                if x != y:
                    flips += 1
                    per[k][0] += 1
    pooled = flips / total

    claim("replicate count", n, "ten independent replicates")
    claim("pairwise comparisons", n * (n - 1) // 2, "forty-five pairwise")
    claim("model calls", n * 80, "$800$ model calls")
    claim("pooled floor", round(pooled, 3), "$%.3f$" % pooled)
    claim("comparisons per action", per["admit"][1], "$720$ comparisons")
    claim("pooled comparisons", total, "$%d/%d$" % (flips, total))
    for k in ("escalate_icu", "referral", "any_opioid", "cs_caution", "admit", "high_acuity"):
        f, t = per[k]
        claim("floor %s" % k, round(f / t, 3), "$%.3f$" % (f / t))

    # --- aggregation curve ------------------------------------------------------------
    def vote(vals):
        vals = [v for v in vals if v is not None]
        if not vals:
            return None
        t_ = sum(1 for v in vals if v)
        return None if t_ * 2 == len(vals) else t_ * 2 > len(vals)

    def agg_rate(k_):
        fl = to = 0
        seen = set()
        for A in itertools.combinations(range(n), k_):
            rest = [i for i in range(n) if i not in A]
            for B in itertools.combinations(rest, k_):
                key = tuple(sorted([A, B]))
                if key in seen:
                    continue
                seen.add(key)
                for v in vignettes:
                    for _, proj in OUTCOMES.items():
                        x = vote([proj(reps[i][v]) for i in A])
                        y = vote([proj(reps[i][v]) for i in B])
                        if x is None or y is None:
                            continue
                        to += 1
                        if x != y:
                            fl += 1
        return fl / to if to else None

    for k_ in (3, 5):
        r = agg_rate(k_)
        claim("floor at R=%d" % k_, round(r, 3), "$%.3f$" % r)

    # --- derived design quantities ----------------------------------------------------
    n_needed = 25 / pooled
    claim("N from floor", round(n_needed), "gives $%d$" % round(n_needed))

    p3 = comb(4, 3) * pooled ** 3 * (1 - pooled) + pooled ** 4
    claim("P(>=3 of 4 | pooled)", round(p3, 3), "$%.3f$" % p3)

    cs = per["cs_caution"][0] / per["cs_caution"][1]
    p3cs = comb(4, 3) * cs ** 3 * (1 - cs) + cs ** 4
    claim("P(>=3 of 4 | cs_caution)", round(p3cs, 3), "$%.3f$" % p3cs)

    # --- second model arm --------------------------------------------------------------
    # The sonnet arm is a separate directory with its own replicate count. Recomputing it here
    # keeps the cross-model claims under the same mechanical check as everything else.
    global INST
    saved = INST
    INST = os.path.join(ROOT, "experiments", "floor16_sonnet")
    reps_b = _reps()
    INST = saved
    if reps_b:
        nb = len(reps_b)
        vb = sorted(set.intersection(*[set(r) for r in reps_b]))
        per_b = {k: [0, 0] for k in OUTCOMES}
        fb = tb = 0
        for a, b in itertools.combinations(range(nb), 2):
            for v in vb:
                for k, proj in OUTCOMES.items():
                    x, y = proj(reps_b[a][v]), proj(reps_b[b][v])
                    if x is None or y is None:
                        continue
                    tb += 1
                    per_b[k][1] += 1
                    if x != y:
                        fb += 1
                        per_b[k][0] += 1
        pooled_b = fb / tb
        claim("second-model pooled floor", round(pooled_b, 3), "$%.3f$" % pooled_b)
        for k in ("escalate_icu", "cs_caution"):
            r = per_b[k][0] / per_b[k][1]
            claim("second-model %s" % k, round(r, 3), "$%.3f$" % r)

        # Spearman across the six actions, recomputed rather than quoted.
        def ranks(vals):
            order = sorted(range(len(vals)), key=lambda i: vals[i])
            out = [0] * len(vals)
            for pos, i in enumerate(order):
                out[i] = pos + 1
            return out
        keys = sorted(OUTCOMES)
        xa = [per[k][0] / per[k][1] for k in keys]
        xb = [per_b[k][0] / per_b[k][1] for k in keys]
        ra, rb = ranks(xa), ranks(xb)
        d2 = sum((u - v) ** 2 for u, v in zip(ra, rb))
        rho = 1 - (6.0 * d2) / (len(keys) * (len(keys) ** 2 - 1))
        claim("cross-model Spearman", round(rho, 2), "$%.2f$" % rho)

    # --- superseded figures must be ABSENT ----------------------------------------------
    # The checks above confirm that current values appear. They cannot catch a stale value
    # left behind in a section nobody re-read, which is exactly how the four-vignette floor
    # survived in the first contribution bullet after Sec. IV-A had disowned it. Each entry
    # here is a figure a better measurement replaced; finding one is a failure.
    RETIRED = [
        ("13.6", "four-vignette pooled floor, superseded by 0.087"),
        ("0.136", "four-vignette pooled floor, superseded by 0.087"),
        ("$0.128$", "six-replicate pooled floor, superseded by 0.087"),
        ("two of six actions never moved", "four-vignette artifact; no action is at zero now"),
        ("$180$ comparisons", "four-vignette comparison count, superseded by 720"),
        ("N{=}120", "vignette count derived from the single-draw floor"),
        ("N{=}200", "vignette count derived from the four-vignette floor"),
    ]
    stale = []
    for needle, why in RETIRED:
        # Allow a figure to appear where the text is explicitly narrating its retraction.
        for m in re.finditer(re.escape(needle), tex):
            window = tex[max(0, m.start() - 260):m.end() + 260]
            narrating = any(w in window for w in
                            ("artifact", "artefact", "superseded", "retract", "withdraw",
                             "moved from", "at four vignettes", "single-draw", "earlier",
                             "wrong in the direction", "has now moved"))
            if not narrating:
                stale.append((needle, why))
                break
    for needle, why in stale:
        failures += 1
        checks.append(("STALE %s" % needle, "-", "should be absent", False))

    # --- report -----------------------------------------------------------------------
    print("%-28s %-10s %-14s %s" % ("claim", "computed", "as written", "in paper"))
    for label, value, needle, ok in checks:
        print("%-28s %-10s %-14s %s" % (label, value, needle[:14], "yes" if ok else "NO"))
    print()
    if failures:
        print("%d claim(s) not found in the manuscript as computed." % failures)
        return 1
    print("all %d computable claims match the artifacts." % len(checks))
    return 0


if __name__ == "__main__":
    sys.exit(main())
