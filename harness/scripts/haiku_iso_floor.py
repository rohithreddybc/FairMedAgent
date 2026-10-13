"""Isolated-call sensitivity arm for endpoint A (claude-haiku-4-5).

Compares the five- and six-action floors of endpoint A as originally run (experiments/floor16:
one shared sub-agent context answers all sixteen vignettes of a step) with the same model
answering every prompt in its own `claude -p` call (experiments/floor16_haiku_iso, written by
experiments/run_haiku_iso.sh). Intervals: crossed vignette x replicate bootstrap, B=5000, seed
42 (crossed_boot.temp_pair; the two arms are resampled with shared vignette draws and
independent replicate draws). Also reports per-action floors and the replicate-dependence
permutation diagnostic for the isolated arm. Output: experiments/haiku_iso_floor.json.
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

A_DIR, ISO_DIR = "floor16", "floor16_haiku_iso"


def main():
    a, iso = cb.load_dir(A_DIR), cb.load_dir(ISO_DIR)
    vs = sorted(cb.complete_vs(a) & cb.complete_vs(iso))
    out = {"meta": {"batched_dir": A_DIR, "isolated_dir": ISO_DIR, "n_vignettes": len(vs),
                    "R_batched": len(a), "R_isolated": len(iso), "seed": cb.SEED, "B": cb.B}}
    # temp_pair labels its arms "default" (first) and "temp0" (second); here first = batched.
    out["crossed"] = cb.temp_pair(a, iso, random.Random(cb.SEED), True)
    per = {}
    for lab, reps in (("batched", a), ("isolated", iso)):
        arm = cb.Arm(reps, vs)
        n, d = arm.counts(np.ones(arm.R), np.ones(len(vs)))
        per[lab] = {k: float(n[i] / d[i]) for i, k in enumerate(cb.KEYS)}
    out["per_action"] = per
    out["dependence_isolated"] = cb.dependence(cb.Arm(iso, vs), np.random.default_rng(cb.SEED))
    path = os.path.join(cb.pc.EXP, "haiku_iso_floor.json")
    json.dump(out, open(path, "w", encoding="utf-8"), indent=1, default=float)
    print(json.dumps(out, indent=1, default=float))


if __name__ == "__main__":
    main()
