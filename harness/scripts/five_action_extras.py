"""Five-action analyses that robustness.py and temperature_compare.py do not carry.

The controlled-substance caution flag has no operational criteria, so the headline, pooled and
cross-model statements are made over the five defined actions. robustness.py (item 9) already
gives the five-action pooled floors, paired separations and range factors. This script adds
the pieces that paper statements need and that were only available over six actions:

  A. majority-vote reduction 1 - f5/f1 over the five actions, with a paired vignette-cluster
     bootstrap (B=5000, seed 42), for models A and C-F;
  B. model A's cell-level diagnostics over the five actions (unanimous cells, near-boundary
     cells, exact five-five ties) and the independent-noise null for the R=5 floor;
  C. the homogeneous-rate (prevalence) normalization of model A and B, five actions;
  D. temperature-0 versus default floors over the five actions for phi3:mini and the hosted
     Groq check.

    FMA_PANEL=v3 python five_action_extras.py      -> experiments/five_action_extras_v3.json
"""
from __future__ import annotations

import glob
import itertools
import json
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import panel_config as pc  # noqa: E402
import robustness as rb  # noqa: E402
import plateau_null as pn  # noqa: E402
import aggregation_curve as ac  # noqa: E402

EXP = pc.EXP
SEED = 42
B = 5000
FIVE = [k for k in rb.KEYS if k != "cs_caution"]
OUT = os.environ.get("FMA_FIVE_OUT") or pc.out_path("five_action_extras", "json")
O = rb.OUTCOMES


def pct_ci(vals):
    v = sorted(vals)
    n = len(v)
    return [v[int(0.025 * n)], v[min(n - 1, int(0.975 * n))]]


# --- A. five-action majority-vote reduction ------------------------------------------
def vote_reduction(models):
    rng = random.Random(SEED)
    out = {"B": B, "actions": FIVE, "models": {}}
    for lab in ("A", "C", "D", "E", "F"):
        rs, vs = models[lab]["reps"], models[lab]["vignettes"]
        t1, n1 = rb._flip_table(rs, vs, 1, FIVE)
        t5, n5 = rb._flip_table(rs, vs, 5, FIVE)
        _, _, f1 = rb.agg_rate(rs, vs, 1, FIVE)
        _, _, f3 = rb.agg_rate(rs, vs, 3, FIVE)
        _, _, f5 = rb.agg_rate(rs, vs, 5, FIVE)
        V = len(vs)
        reds = []
        for _ in range(B):
            idx = [rng.randrange(V) for _ in range(V)]
            a, b = rb._flip_rate(t1, idx), rb._flip_rate(t5, idx)
            if a:
                reds.append(1 - b / a)
        out["models"][lab] = {"f1": f1, "f3": f3, "f5": f5, "reduction": 1 - f5 / f1,
                              "reduction_ci": pct_ci(reds), "n_valid_resamples": len(reds)}
    return out


# --- B. model A cell diagnostics and null ----------------------------------------------
def cell_diagnostics(models):
    rs, vs = models["A"]["reps"], models["A"]["vignettes"]
    n = len(rs)
    cells = {}
    for v in vs:
        for name in FIVE:
            s = [O[name](r[v]) for r in rs]
            if all(x is not None for x in s):
                cells[(v, name)] = s
    ks = {key: sum(1 for x in s if x) for key, s in cells.items()}
    unanimous = sum(1 for k in ks.values() if k in (0, n))
    contested = [key for key, k in ks.items() if k not in (0, n)]
    near = [key for key in contested if 0.3 <= ks[key] / n <= 0.7]
    ties = [key for key in near if ks[key] * 2 == n]
    p_tie = math.comb(n, n // 2) / 2 ** n
    obs = pn._curve(cells, n, [1, 3, 5])

    def sim(draw_p, n_sims, rng):
        vals = []
        for _ in range(n_sims):
            sim_cells = {key: [rng.random() < draw_p(key, rng) for _ in range(n)] for key in cells}
            c = pn._curve(sim_cells, n, [5])
            if c[5] is not None:
                vals.append(c[5])
        return vals

    probs = {key: ks[key] / n for key in cells}
    plug400 = sim(lambda key, r: probs[key], 400, random.Random(0))     # plateau_null.py default
    rng = random.Random(SEED)
    plug2000 = sim(lambda key, r: probs[key], 2000, rng)
    jef2000 = sim(lambda key, r: r.betavariate(ks[key] + 0.5, n - ks[key] + 0.5), 2000, rng)

    def summ(vals):
        return {"n_sims": len(vals), "mean": sum(vals) / len(vals), "ci_2.5_97.5": pct_ci(vals)}

    return {"n_cells": len(cells), "n_unanimous": unanimous, "n_contested": len(contested),
            "n_near_boundary_0.3_0.7": len(near), "n_exact_ties": len(ties),
            "p_tie_at_half": p_tie, "expected_ties_if_all_near_at_half": len(near) * p_tie,
            "observed_curve": {str(k): v for k, v in obs.items()},
            "R5_as_share_of_R1": obs[5] / obs[1],
            "null_plugin_400sims_seed0": summ(plug400),
            "null_plugin_2000sims": summ(plug2000), "null_jeffreys_2000sims": summ(jef2000)}


# --- C. prevalence normalization --------------------------------------------------------
def homogeneous_ratio(models, lab):
    rs, vs = models[lab]["reps"], models[lab]["vignettes"]
    rows = {}
    for name in FIVE:
        obs_f = obs_p = pos = tot = 0
        for v in vs:
            s = [O[name](r[v]) for r in rs]
            s = [x for x in s if x is not None]
            if len(s) < 2:
                continue
            pos += sum(1 for x in s if x)
            tot += len(s)
            for a, b in itertools.combinations(range(len(s)), 2):
                obs_p += 1
                obs_f += s[a] != s[b]
        pbar = pos / tot
        pred = 2 * pbar * (1 - pbar)
        rows[name] = {"prevalence": pbar, "observed": obs_f / obs_p, "predicted_homogeneous": pred,
                      "ratio": (obs_f / obs_p) / pred if pred else None}
    ratios = {k: v["ratio"] for k, v in rows.items() if v["ratio"] is not None}
    lo, hi = min(ratios, key=ratios.get), max(ratios, key=ratios.get)
    return {"actions": rows, "ratio_min_action": lo, "ratio_min": ratios[lo],
            "ratio_max_action": hi, "ratio_max": ratios[hi], "ratio_spread": ratios[hi] / ratios[lo]}


# --- D. temperature 0, five actions ---------------------------------------------------------
def load_dir(d, first=None):
    reps = []
    for p in sorted(glob.glob(os.path.join(EXP, d, "rep*", "trajectories.json")))[:first]:
        reps.append({t["vignette_id"]: t["actions"] for t in json.load(open(p, encoding="utf-8"))["trajectories"]
                     if t["complete"] and t["condition_id"] == "ref_white_man_private"})
    return reps


def per_vignette(reps):
    out = {}
    for v in set.intersection(*[set(r) for r in reps]):
        f = n = 0
        for a, b in itertools.combinations(range(len(reps)), 2):
            for name in FIVE:
                x, y = O[name](reps[a][v]), O[name](reps[b][v])
                if x is None or y is None:
                    continue
                n += 1
                f += x != y
        out[v] = (f, n)
    return out


def rate(pv, vs):
    f, n = sum(pv[v][0] for v in vs), sum(pv[v][1] for v in vs)
    return f / n if n else float("nan")


def paired(dflt, t0, rng):
    vs = sorted(set(dflt) & set(t0))
    obs = {"default": rate(dflt, vs), "temp0": rate(t0, vs)}
    bd, b0, br = [], [], []
    for _ in range(B):
        s = [rng.choice(vs) for _ in vs]
        a, b = rate(dflt, s), rate(t0, s)
        bd.append(a)
        b0.append(b)
        br.append(1 - b / a if a > 0 else float("nan"))
    ci = {}
    for k, xs in (("default", bd), ("temp0", b0), ("reduction", br)):
        xs = sorted(x for x in xs if x == x)
        ci[k] = [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]]
    return {"n_vignettes": len(vs), "observed": obs, "ci_B5000": ci,
            "reduction": 1 - obs["temp0"] / obs["default"]}


def temperature():
    rng = random.Random(SEED)
    out = {"actions": FIVE, "models": {}}
    for lab in ("C", "D", "E", "F"):
        d = pc.local_dir(lab)
        out["models"][lab] = paired(per_vignette(load_dir(d)), per_vignette(load_dir(d + "_t0")), rng)
    g0 = per_vignette(load_dir("floor16_groq_t0"))
    vs = sorted(g0)
    f, n = sum(g0[v][0] for v in vs), sum(g0[v][1] for v in vs)
    bs = sorted(rate(g0, [rng.choice(vs) for _ in vs]) for _ in range(B))
    out["hosted_t0"] = {"disagreeing": f, "comparisons": n, "floor": f / n,
                        "ci_B5000": [bs[int(0.025 * B)], bs[int(0.975 * B) - 1]]}
    out["hosted_paired"] = paired(per_vignette(load_dir("floor16_groq_t1")), g0, rng)
    return out


# --- E. model A admission minus ICU escalation; five-action leave-one-vignette-out --------
def paired_and_lovo(models):
    ps = rb.ps
    canon = models["A"]["vignettes"]
    rng = random.Random(SEED)
    resamples = rb.build_resamples(rng, canon, B)       # same stream robustness.py uses
    rsA = models["A"]["reps"]
    diffs = []
    for samp in resamples:
        c = ps.counts(rsA, samp)
        if c["admit"][1] and c["escalate_icu"][1]:
            diffs.append(c["admit"][0] / c["admit"][1] - c["escalate_icu"][0] / c["escalate_icu"][1])
    obs = ps.counts(rsA, canon)
    d_obs = obs["admit"][0] / obs["admit"][1] - obs["escalate_icu"][0] / obs["escalate_icu"][1]
    loo_d = []
    for dv in canon:
        c = ps.counts(rsA, [v for v in canon if v != dv])
        loo_d.append(c["admit"][0] / c["admit"][1] - c["escalate_icu"][0] / c["escalate_icu"][1])
    lovo = {}
    for lab in sorted(models):
        rs, vs = models[lab]["reps"], models[lab]["vignettes"]
        fl = []
        for dv in vs:
            c = ps.counts(rs, [v for v in vs if v != dv])
            fl.append(rb.pooled_from_counts(c, FIVE))
        lovo[lab] = {"min": min(fl), "max": max(fl)}
    return {"admit_minus_icu_A": {"observed": d_obs, "ci_B5000": pct_ci(diffs),
                                  "lovo_min": min(loo_d), "lovo_max": max(loo_d)},
            "pooled_5action_lovo": lovo}


def main():
    models, _ = rb.load_models()
    res = {"panel": pc.PANEL, "seed": SEED, "B": B, "actions": FIVE}
    res["paired_lovo_5action"] = paired_and_lovo(models)
    res["majority_vote_5action"] = vote_reduction(models)
    res["modelA_cells_5action"] = cell_diagnostics(models)
    res["homogeneous_ratio_5action"] = {lab: homogeneous_ratio(models, lab) for lab in ("A", "B")}
    res["temperature_5action"] = temperature()
    json.dump(res, open(OUT, "w", encoding="utf-8"), indent=1)
    print("wrote", OUT)
    for lab, e in res["majority_vote_5action"]["models"].items():
        print(lab, "f1 %.3f f3 %.3f f5 %.3f reduction %.3f [%.3f, %.3f]"
              % (e["f1"], e["f3"], e["f5"], e["reduction"], *e["reduction_ci"]))
    c = res["modelA_cells_5action"]
    print({k: v for k, v in c.items() if not k.startswith("null")})
    for k in ("null_plugin_400sims_seed0", "null_plugin_2000sims", "null_jeffreys_2000sims"):
        print(k, c[k])
    for lab, e in res["homogeneous_ratio_5action"].items():
        print(lab, {k: round(v["ratio"], 2) for k, v in e["actions"].items()}, "spread %.1f" % e["ratio_spread"])
    t = res["temperature_5action"]
    for lab, e in t["models"].items():
        print(lab, e)
    print("hosted", t["hosted_t0"], t["hosted_paired"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
