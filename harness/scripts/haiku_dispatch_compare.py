"""Interleaved dispatch comparison for endpoint A (claude-haiku-4-5, reference condition).

Compares floor16_haiku_il_iso (one `claude -p` call per prompt) with floor16_haiku_il_batch (one call
per step carrying all sixteen prompts), run replicate-by-replicate in alternating order by
experiments/run_haiku_interleaved.sh so time drift does not align with the arm. Reports, for the
five- and six-action pooled floors: each arm's floor with a crossed vignette x replicate interval
(B=5000, seed 42, crossed_boot.Arm.counts machinery: shared vignette draws, independent replicate
draws per arm), the batched/isolated ratio and the batched-minus-isolated difference with percentile
intervals, per-action floors with intervals, and the replicate-dependence permutation diagnostic
(crossed_boot.dependence) for each arm. The earlier arms floor16 (batched, earlier window) and
floor16_haiku_iso (isolated, earlier window) are listed descriptively with the same estimator and
are NOT part of the contrast. Works on partial data (needs >= 2 complete replicates per arm).
Output: experiments/haiku_dispatch_compare.json.
"""
from __future__ import annotations

import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crossed_boot as cb  # noqa: E402

ISO = os.environ.get("FMA_DC_ISO", "floor16_haiku_il_iso")      # env overrides are for stand-in tests only
BATCH = os.environ.get("FMA_DC_BATCH", "floor16_haiku_il_batch")
OUT = os.environ.get("FMA_DC_OUT") or os.path.join(cb.pc.EXP, "haiku_dispatch_compare.json")
EARLIER = {"floor16": "earlier window, shared sub-agent context per replicate (endpoint A as run)",
           "floor16_haiku_iso": "earlier window, isolated calls (sensitivity arm)"}
TAGS = {"5action": cb.I5, "6action": list(range(6))}


def rate(num, den, idx):
    d = den[..., idx].sum(-1)
    return np.where(d > 0, num[..., idx].sum(-1) / np.where(d > 0, d, 1), np.nan)


def main():
    iso, bat = cb.load_dir(ISO), cb.load_dir(BATCH)
    out = {"meta": {"iso_dir": ISO, "batch_dir": BATCH, "R_iso": len(iso), "R_batch": len(bat), "seed": cb.SEED, "B": cb.B,
                    "design": "replicates run interleaved, arm order alternating (iso first on odd r)"}}
    if len(iso) < 2 or len(bat) < 2:
        out["status"] = "insufficient complete replicates"
        print(out)
        json.dump(out, open(OUT, "w", encoding="utf-8"), indent=1)
        return
    vs = sorted(cb.complete_vs(iso) & cb.complete_vs(bat))
    ai, ab = cb.Arm(iso, vs), cb.Arm(bat, vs)
    out["meta"]["n_vignettes"] = len(vs)
    rng = random.Random(cb.SEED)
    V = len(vs)
    # draws
    bi, bb = [], []
    for _ in range(cb.B):
        w = cb.mult([rng.randrange(V) for _ in vs], V)
        mi = cb.mult([rng.randrange(ai.R) for _ in range(ai.R)], ai.R)
        mb = cb.mult([rng.randrange(ab.R) for _ in range(ab.R)], ab.R)
        bi.append(ai.counts(mi, w)); bb.append(ab.counts(mb, w))
    Ni, Di = np.array([x[0] for x in bi]), np.array([x[1] for x in bi])
    Nb, Db = np.array([x[0] for x in bb]), np.array([x[1] for x in bb])
    oni, odi = ai.counts(np.ones(ai.R), np.ones(V))
    onb, odb = ab.counts(np.ones(ab.R), np.ones(V))
    out["pooled"] = {}
    for tag, idx in TAGS.items():
        fi, fb = rate(oni, odi, idx), rate(onb, odb, idx)
        bfi, bfb = rate(Ni, Di, idx), rate(Nb, Db, idx)
        good = ~np.isnan(bfi) & ~np.isnan(bfb)
        ratio = bfb[good & (bfi > 0)] / bfi[good & (bfi > 0)]
        diff = (bfb - bfi)[good]
        out["pooled"][tag] = {
            "floor_iso": float(fi), "ci_iso": cb.pct(bfi[~np.isnan(bfi)].tolist()),
            "floor_batch": float(fb), "ci_batch": cb.pct(bfb[~np.isnan(bfb)].tolist()),
            "ratio_batch_over_iso": float(fb / fi), "ci_ratio": cb.pct(ratio.tolist()),
            "diff_batch_minus_iso": float(fb - fi), "ci_diff": cb.pct(diff.tolist()),
            "diff_ci_excludes_zero": not (cb.pct(diff.tolist())[0] <= 0 <= cb.pct(diff.tolist())[1])}
    out["per_action"] = {}
    for k, name in enumerate(cb.KEYS):
        fi, fb = rate(oni, odi, [k]), rate(onb, odb, [k])
        bfi, bfb = rate(Ni, Di, [k]), rate(Nb, Db, [k])
        d = (bfb - bfi)[~np.isnan(bfi) & ~np.isnan(bfb)]
        out["per_action"][name] = {"iso": float(fi), "ci_iso": cb.pct(bfi[~np.isnan(bfi)].tolist()),
                                   "batch": float(fb), "ci_batch": cb.pct(bfb[~np.isnan(bfb)].tolist()),
                                   "diff": float(fb - fi), "ci_diff": cb.pct(d.tolist())}
    nrng = np.random.default_rng(cb.SEED)
    out["dependence"] = {"iso": cb.dependence(ai, nrng), "batch": cb.dependence(ab, nrng)}
    out["earlier_arms_descriptive"] = {}
    for d, note in EARLIER.items():
        reps = cb.load_dir(d)
        if len(reps) < 2:
            continue
        v2 = sorted(cb.complete_vs(reps))
        arm = cb.Arm(reps, v2)
        n, dn = arm.counts(np.ones(arm.R), np.ones(len(v2)))
        out["earlier_arms_descriptive"][d] = {
            "note": note, "R": arm.R, "n_vignettes": len(v2),
            "floor_5action": float(n[cb.I5].sum() / dn[cb.I5].sum()), "floor_6action": float(n.sum() / dn.sum()),
            "per_action": {k: float(n[i] / dn[i]) for i, k in enumerate(cb.KEYS)}}
    path = OUT
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1, default=float)
    print(json.dumps(out["pooled"], indent=1, default=float))
    print(json.dumps(out["earlier_arms_descriptive"], indent=1, default=float)[:1500])
    print("wrote", path)


if __name__ == "__main__":
    main()
