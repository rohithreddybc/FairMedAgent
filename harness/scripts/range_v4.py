"""Range factor (unconditional and conditional), absolute range, and highest-minus-lowest model difference.

Reuses crossed_boot.run_panel (identical resamples to robustness_v3_crossed.json: seed 42, B=5000).
Writes experiments/range_v4.json.  Run: FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/range_v4.py
"""
from __future__ import annotations

import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crossed_boot as cb  # noqa: E402

pc, rb = cb.pc, cb.rb
OUT = os.path.join(pc.EXP, "range_v4.json")


def lohi(v):
    v = np.sort(np.asarray(v, dtype=float))
    n = len(v)
    return [float(v[int(0.025 * n)]), float(v[min(n - 1, int(0.975 * n))])]


def main():
    models, _ = rb.load_models()
    models = {l: m for l, m in models.items() if l in "ABCDEF"}
    canon = models["A"]["vignettes"]
    labs = sorted(models)
    arms, vres, W, rdraws, cr, vo, obs = cb.run_panel(models, canon)
    P = {l: cb.pooled(cr[l], cb.I5) for l in labs}
    O = {l: float(cb.pooled(obs[l], cb.I5)) for l in labs}
    M = np.vstack([P[l] for l in labs])
    B = M.shape[1]
    mx, mn = M.max(0), M.min(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        ratio = np.where(mn > 0, mx / np.where(mn > 0, mx * 0 + mn, 1), np.inf)   # undefined -> +inf
    undefined = ~(mn > 0)
    ratio = np.where(undefined, np.inf, mx / np.where(mn > 0, mn, 1))
    cond = ratio[~undefined]
    omax, omin = max(O.values()), min(O.values())
    res = {"meta": {"panel": pc.PANEL, "seed": cb.SEED, "B": B, "source": "crossed_boot.run_panel (same resamples as robustness_v3_crossed.json)",
                    "observed_floors_5action": O,
                    "highest_model": max(O, key=O.get), "lowest_model": min(O, key=O.get)}}
    nu = int(undefined.sum())
    res["range_factor"] = {
        "observed": omax / omin, "n_undefined_resamples": nu, "share_undefined": nu / B,
        "unconditional_undefined_as_plus_inf": {"ci": lohi(ratio), "upper_is_infinite": bool(np.isinf(lohi(ratio)[1])),
                                                "note": "min floor = 0 in the resample -> ratio +inf; percentile indices int(0.025B), int(0.975B) over all B"},
        "conditional_on_positive_min": {"ci": lohi(cond), "n": int(len(cond)),
                                        "note": "drops undefined resamples; this is the interval printed in the paper (6.7-92.7)"},
        "share_undefined_exceeds_2.5pct": bool(nu / B > 0.025)}
    absr = mx - mn
    res["absolute_range_max_minus_min"] = {"observed": omax - omin, "ci": lohi(absr), "mean_boot": float(absr.mean()),
                                           "note": "max and min taken within each resample (identity of models may change)"}
    hi, lo = res["meta"]["highest_model"], res["meta"]["lowest_model"]
    d = P[hi] - P[lo]
    res["pairwise_highest_minus_lowest"] = {"pair": "%s - %s" % (hi, lo), "observed": O[hi] - O[lo], "ci": lohi(d),
                                            "n_dropped": int(np.isnan(d).sum())}
    ref = json.load(open(os.path.join(pc.EXP, "robustness%s_crossed.json" % pc.SUFFIX), encoding="utf-8"))
    rf = ref["crossed"]["range_factor_5action"]
    res["check_vs_robustness_v3_crossed"] = {"range_factor_observed": rf["observed"], "range_factor_ci_conditional": rf["ci"],
                                             "n_undefined": rf["n_undefined_resamples"],
                                             "matches": bool(abs(rf["observed"] - res["range_factor"]["observed"]) < 1e-9
                                                             and rf["ci"] == res["range_factor"]["conditional_on_positive_min"]["ci"]
                                                             and rf["n_undefined_resamples"] == nu)}
    pr = [p for p in ref["crossed"]["pairs_5action"] if p["pair"] in ("%s-%s" % (lo, hi), "%s-%s" % (hi, lo))]
    res["check_vs_robustness_v3_crossed"]["pair_entry"] = pr
    json.dump(res, open(OUT, "w"), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float))


if __name__ == "__main__":
    main()
