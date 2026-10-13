"""Interleaved default-sampling versus temperature-0 comparison on the four local models.

Data: experiments/temp_il_<model>_{default,t0}/rep01..rep06 (driver experiments/run_temp_il.sh), where
for each replicate index one default and one temperature-0 replicate ran back to back, default first on
odd indices and temperature 0 first on even ones. Floors, intervals and the reduction use
crossed_boot.temp_pair (vignette-paired crossed bootstrap, B=5000, seed 42); an arm with no observed
discordance gets the vignette-unit one-sided 95% bound of zero_bounds_v4.new_bound instead of an
interval. Writes experiments/temp_il_compare.json.

    python temp_il_compare.py
"""
from __future__ import annotations

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_validation as av  # noqa: E402
import crossed_boot as cb  # noqa: E402
import zero_bounds_v4 as zb  # noqa: E402

MODELS = ("llama", "mistral", "qwen3", "phi3")


def main() -> int:
    rng = random.Random(cb.SEED)
    out = {"meta": {"B": cb.B, "seed": cb.SEED, "design": "default and temperature-0 replicates interleaved, alternating first arm"},
           "models": {}}
    log = [json.loads(l) for l in open(os.path.join(av.EXP, "temp_il_order_log.jsonl"), encoding="utf-8") if l.strip()]
    for m in MODELS:
        d = av.load("temp_il_%s_default" % m, av.REF)
        t = av.load("temp_il_%s_t0" % m, av.REF)
        res = cb.temp_pair(d, t, rng, True)
        for tag, r in res.items():
            r["R_default"], r["R_t0"] = len(d), len(t)
            if r["temp0"] == 0:
                r["temp0_zero_bound"] = float(zb.new_bound(r["n_vignettes"], len(t))["true_max"])
        tag = next(iter({rec["model"] for rec in log if rec["model"].startswith(m)}))
        span = [min(rec["t_start"] for rec in log if rec["model"] == tag), max(rec["t_end"] for rec in log if rec["model"] == tag)]
        res["model"], res["utc_span"] = tag, span
        out["models"][m] = res
        r5 = res["5action"]
        print("%-8s V=%d R=%d/%d default %.3f [%.3f, %.3f]  t0 %.3f [%.3f, %.3f]  reduction %.2f [%.2f, %.2f]  %s..%s" % (
            m, r5["n_vignettes"], len(d), len(t), r5["default"], *r5["ci_default"], r5["temp0"], *r5["ci_temp0"],
            r5["reduction"], *r5["ci_reduction"], *span), flush=True)
    json.dump(out, open(os.path.join(av.EXP, "temp_il_compare.json"), "w", encoding="utf-8"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
