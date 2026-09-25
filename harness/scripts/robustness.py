"""Robustness and sensitivity supplement for the panel floor.

The panel floor (panel_summary.py), the aggregation curve (aggregation_curve.py) and the
plateau null (plateau_null.py) each answer one question with one point estimate or one curve.
This script does not recompute those answers differently -- it imports them and asks how much
each one moves under resampling, deletion, and a null it did not have to pass. Everything here
either (a) puts a confidence interval on a number those scripts already report, (b) checks that
number against small, targeted perturbations (delete one vignette; simulate under a null; run
a director's-cut McNemar power study), or (c) checks numerical stability of the interval itself
(B=600 vs B=5000).

Reuse, not reimplementation: OUTCOMES/KEYS, the pairwise counting, and the panel come from
panel_summary.py (`ps`); the disjoint-split majority vote comes from aggregation_curve.py
(`ac`); the independent-noise null comes from plateau_null.py (`pn`). All three are imported,
not copied, so a change to any one of them cannot silently diverge from what this script uses.

Before anything else runs, the published point estimates for model A (haiku) are recomputed
from the artifact and checked byte-for-byte against the numbers this task was given:
pooled 0.087 (374/4320), escalate_icu 0.022, cs_caution 0.179, R=3 0.063, R=5 0.053. A mismatch
aborts the script rather than silently producing a supplement for numbers that no longer hold.

Bootstrap convention throughout: a "paired cluster bootstrap" resample is a length-16 list of
vignette ids drawn with replacement from the 16-vignette pool that is IDENTICAL across all six
models (checked below). The same resample index is applied to every model/action pair being
compared in one draw, which is what makes cross-model and cross-action differences and ratios
paired rather than independently noisy. One shared `random.Random(42)` instance drives every
draw in this script, consumed in the fixed order the sections run in below, so the whole run is
reproducible from the single seed=42 given in the task.

    python robustness.py
"""
from __future__ import annotations

import itertools
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

import aggregation_curve as ac  # noqa: E402  (disjoint splits, majority vote)
import panel_summary as ps  # noqa: E402  (OUTCOMES, KEYS, ATTRS, pairwise counting)
import plateau_null as pn  # noqa: E402  (independent-noise null curve)

OUTCOMES = ps.OUTCOMES
KEYS = ps.KEYS  # sorted list of the six binary outcomes
OUT_PATH = os.path.join(ROOT, "experiments", "robustness.json")

SEED = 42
B_MAIN = 5000     # items 1, 2, 3, 5: paired vignette-cluster bootstrap
B_SMALL = 600     # subset of the same stream, for the stability comparison
B_ITEM6 = 2000    # item 6: bootstrap of the majority-vote reduction
N_NULL_SIMS = 2000   # item 7
N_MCNEMAR_SIMS = 2000  # item 8

# Extra (temperature-0) directories the task allows if complete; skipped otherwise.
EXTRA_DIRS = {
    "floor16_ollama_t0": "C_t0",
    "floor16_mistral_t0": "D_t0",
    "floor16_qwen3_t0": "E_t0",
    "floor16_phi3_t0": "F_t0",
}


def pct_ci(vals):
    v = sorted(vals)
    n = len(v)
    lo = v[int(0.025 * n)]
    hi = v[min(n - 1, int(0.975 * n))]
    return lo, hi


def pooled_from_counts(cdict, keys=KEYS):
    num = sum(cdict[k][0] for k in keys)
    den = sum(cdict[k][1] for k in keys)
    return num / den if den else None


# ---------------------------------------------------------------------------------------
# Load the six-model panel (same directories/labels as panel_summary.ATTRS), plus any
# complete temperature-0 directories.
# ---------------------------------------------------------------------------------------

def load_models():
    models = {}
    for dirname, (lab, name, vendor, host, size) in ps.ATTRS.items():
        if lab not in "ABCDEF":
            continue
        rs = ps.reps(dirname)
        if not rs:
            continue
        vs = sorted(set.intersection(*[set(r) for r in rs]))
        models[lab] = {"dir": dirname, "name": name, "reps": rs, "vignettes": vs}
    skipped_extra = []
    for dirname, lab in EXTRA_DIRS.items():
        rs = ps.reps(dirname)
        if len(rs) >= 10:
            vs = sorted(set.intersection(*[set(r) for r in rs]))
            models[lab] = {"dir": dirname, "name": lab, "reps": rs, "vignettes": vs}
        else:
            skipped_extra.append((dirname, len(rs)))
    return models, skipped_extra


# ---------------------------------------------------------------------------------------
# Verification gate: the published point estimates must reproduce exactly before anything
# else runs.
# ---------------------------------------------------------------------------------------

def agg_rate(reps, vignettes, k, keys=None):
    keys = keys or KEYS
    fl = to = 0
    for a, b in ac._disjoint_splits(len(reps), k):
        for v in vignettes:
            for name in keys:
                proj = OUTCOMES[name]
                xa = ac._vote([proj(reps[i][v]) for i in a])
                xb = ac._vote([proj(reps[i][v]) for i in b])
                if xa is None or xb is None:
                    continue
                to += 1
                if xa != xb:
                    fl += 1
    return fl, to, (fl / to if to else None)


def verify_published(models):
    a = models["A"]
    rs, vs = a["reps"], a["vignettes"]
    per = ps.counts(rs, vs)
    pooled_num = sum(per[k][0] for k in KEYS)
    pooled_den = sum(per[k][1] for k in KEYS)
    pooled = pooled_num / pooled_den
    icu = per["escalate_icu"][0] / per["escalate_icu"][1]
    cs = per["cs_caution"][0] / per["cs_caution"][1]
    _, _, r3 = agg_rate(rs, vs, 3)
    _, _, r5 = agg_rate(rs, vs, 5)

    checks = [
        ("pooled floor", round(pooled, 3), 0.087),
        ("pooled numerator", pooled_num, 374),
        ("pooled denominator", pooled_den, 4320),
        ("escalate_icu floor", round(icu, 3), 0.022),
        ("cs_caution floor", round(cs, 3), 0.179),
        ("R=3 floor", round(r3, 3), 0.063),
        ("R=5 floor", round(r5, 3), 0.053),
    ]
    mismatches = [(label, got, want) for label, got, want in checks if got != want]
    result = {
        "checks": [{"label": l, "computed": g, "published": w} for l, g, w in checks],
        "mismatches": mismatches,
        "ok": not mismatches,
    }
    return result, per, vs, pooled_num, pooled_den


# ---------------------------------------------------------------------------------------
# Items 1, 2, 3, 5: paired vignette-cluster bootstrap, shared across all six models.
# ---------------------------------------------------------------------------------------

def build_resamples(rng, canonical_v, b):
    return [[rng.choice(canonical_v) for _ in canonical_v] for _ in range(b)]


def cache_bootstrap_counts(models, resamples):
    """cache[lab] = list of ps.counts(...) dicts, one per resample, in resample order."""
    cache = {}
    for lab, m in models.items():
        rs = m["reps"]
        cache[lab] = [ps.counts(rs, samp) for samp in resamples]
    return cache


def item1(models, obs_counts, cache, b_values=(B_SMALL, B_MAIN)):
    out = {"B_values": list(b_values), "models": {}}
    for lab in sorted(models):
        per_obs = obs_counts[lab]
        model_out = {"actions": {}, "pooled": {}}
        for k in KEYS:
            num, den = per_obs[k]
            entry = {"num": num, "den": den, "floor": num / den if den else None, "ci": {}}
            for b in b_values:
                vals = [c[k][0] / c[k][1] for c in cache[lab][:b] if c[k][1]]
                entry["ci"]["B=%d" % b] = pct_ci(vals) if vals else None
            model_out["actions"][k] = entry
        pooled_num = sum(per_obs[k][0] for k in KEYS)
        pooled_den = sum(per_obs[k][1] for k in KEYS)
        pooled_entry = {"num": pooled_num, "den": pooled_den,
                         "floor": pooled_num / pooled_den, "ci": {}}
        for b in b_values:
            vals = [pooled_from_counts(c) for c in cache[lab][:b]]
            pooled_entry["ci"]["B=%d" % b] = pct_ci(vals)
        model_out["pooled"] = pooled_entry
        out["models"][lab] = model_out
    return out


def item2(models, obs_counts, cache):
    per = obs_counts["A"]
    cs_num, cs_den = per["cs_caution"]
    icu_num, icu_den = per["escalate_icu"]
    obs_cs, obs_icu = cs_num / cs_den, icu_num / icu_den
    diffs, ratios = [], []
    icu_zero = 0
    for c in cache["A"]:
        cs = c["cs_caution"][0] / c["cs_caution"][1] if c["cs_caution"][1] else None
        icu = c["escalate_icu"][0] / c["escalate_icu"][1] if c["escalate_icu"][1] else None
        if cs is None or icu is None:
            continue
        diffs.append(cs - icu)
        if icu == 0:
            icu_zero += 1
        else:
            ratios.append(cs / icu)
    return {
        "observed": {"cs_caution": obs_cs, "escalate_icu": obs_icu,
                      "difference": obs_cs - obs_icu,
                      "ratio": obs_cs / obs_icu if obs_icu else None},
        "difference_ci_B5000": pct_ci(diffs),
        "ratio": {
            "n_resamples": len(cache["A"]),
            "n_icu_floor_zero": icu_zero,
            "fraction_icu_floor_zero": icu_zero / len(cache["A"]),
            "bounded": icu_zero == 0,
            "finite_subset_ci": pct_ci(ratios) if ratios else None,
            "note": ("ratio CI is not a valid bounded interval: in %.1f%% of resamples the "
                     "escalate_icu floor is 0 (no disagreeing pair among the 16 resampled "
                     "vignettes), making cs_caution/escalate_icu undefined (division by "
                     "zero) rather than merely large. The finite_subset_ci excludes those "
                     "draws and understates the true spread." % (100 * icu_zero / len(cache["A"]))),
        },
    }


def item3(models, obs_counts, cache):
    labs = sorted(models)
    pairs = []
    obs_pooled = {lab: pooled_from_counts(obs_counts[lab]) for lab in labs}
    pooled_boot = {lab: [pooled_from_counts(c) for c in cache[lab]] for lab in labs}
    for i, j in itertools.combinations(range(len(labs)), 2):
        li, lj = labs[i], labs[j]
        diffs = [a - b for a, b in zip(pooled_boot[li], pooled_boot[lj])]
        pairs.append({
            "pair": "%s-%s" % (li, lj),
            "observed_diff": obs_pooled[li] - obs_pooled[lj],
            "ci_B5000": pct_ci(diffs),
        })
    return pairs


def item5(models, cache):
    excl = [k for k in KEYS if k != "cs_caution"]
    out = {"excluded": "cs_caution", "models": {}}
    for lab in sorted(models):
        rs, vs = models[lab]["reps"], models[lab]["vignettes"]
        per = ps.counts(rs, vs)
        num = sum(per[k][0] for k in excl)
        den = sum(per[k][1] for k in excl)
        vals = [pooled_from_counts(c, excl) for c in cache[lab]]
        out["models"][lab] = {"num": num, "den": den, "floor": num / den,
                               "ci_B5000": pct_ci(vals)}
    # Model A majority-vote curve excluding cs_caution, at R=1,3,5 (real data, no bootstrap).
    rs, vs = models["A"]["reps"], models["A"]["vignettes"]
    curve = {}
    for k in (1, 3, 5):
        fl, to, rate = agg_rate(rs, vs, k, excl)
        curve[k] = {"flips": fl, "total": to, "rate": rate}
    reduction = 1 - curve[5]["rate"] / curve[1]["rate"]
    out["modelA_majority_vote_excl_cs_caution"] = {"curve": curve, "reduction_1_minus_f5_f1": reduction}
    return out


# ---------------------------------------------------------------------------------------
# Item 4: leave-one-vignette-out.
# ---------------------------------------------------------------------------------------

def item4(models):
    out = {}
    for lab in sorted(models):
        rs, vs = models[lab]["reps"], models[lab]["vignettes"]
        floors = []
        for dv in vs:
            remaining = [v for v in vs if v != dv]
            per = ps.counts(rs, remaining)
            floors.append(pooled_from_counts(per))
        entry = {"n_deletions": len(vs), "min_pooled_floor": min(floors), "max_pooled_floor": max(floors)}
        if lab == "A":
            diffs = []
            for dv in vs:
                remaining = [v for v in vs if v != dv]
                per = ps.counts(rs, remaining)
                diffs.append(per["cs_caution"][0] / per["cs_caution"][1]
                              - per["escalate_icu"][0] / per["escalate_icu"][1])
            entry["cs_minus_icu_min"] = min(diffs)
            entry["cs_minus_icu_max"] = max(diffs)
        out[lab] = entry
    return out


# ---------------------------------------------------------------------------------------
# Item 6: majority-vote reduction, bootstrapped with the identical disjoint-split procedure
# inside every resample. Splits are precomputed once per model (they depend only on which
# replicate indices are compared, not on which vignettes are drawn), and the per-(split,
# vignette,outcome) flip indicator is precomputed once too, since it also does not depend on
# the resample -- only on which vignette identity was drawn and how many times. This turns an
# O(splits x vignettes x outcomes) recomputation into a table lookup per resample, which is
# what keeps B=2000 tractable in pure Python.
# ---------------------------------------------------------------------------------------

def _flip_table(reps, vignettes, k, keys):
    splits = list(ac._disjoint_splits(len(reps), k))
    table = []
    for a, b in splits:
        row = []
        for name in keys:
            proj = OUTCOMES[name]
            col = []
            for v in vignettes:
                xa = ac._vote([proj(reps[i][v]) for i in a])
                xb = ac._vote([proj(reps[i][v]) for i in b])
                col.append(None if (xa is None or xb is None) else int(xa != xb))
            row.append(col)
        table.append(row)
    return table, len(splits)


def _flip_rate(table, idx):
    fl = to = 0
    for row in table:
        for col in row:
            for vi in idx:
                val = col[vi]
                if val is None:
                    continue
                to += 1
                fl += val
    return fl / to if to else None


def item6(models, rng, b=B_ITEM6):
    out = {"B": b, "models": {}}
    for lab in ("A", "C", "D", "E", "F"):
        if lab not in models:
            continue
        rs, vs = models[lab]["reps"], models[lab]["vignettes"]
        n = len(rs)
        table1, n_splits1 = _flip_table(rs, vs, 1, KEYS)
        table5, n_splits5 = _flip_table(rs, vs, 5, KEYS)
        V = len(vs)

        # Observed (real data, no resampling).
        _, _, f1_obs = agg_rate(rs, vs, 1)
        _, _, f5_obs = agg_rate(rs, vs, 5)
        observed_reduction = 1 - f5_obs / f1_obs

        reds = []
        for _ in range(b):
            idx = [rng.randrange(V) for _ in range(V)]
            f1 = _flip_rate(table1, idx)
            f5 = _flip_rate(table5, idx)
            if f1:
                reds.append(1 - f5 / f1)
        out["models"][lab] = {
            "n_reps": n,
            "f1_observed": f1_obs,
            "f5_observed": f5_obs,
            "reduction_observed": observed_reduction,
            "reduction_ci": pct_ci(reds),
            "n_valid_resamples": len(reds),
            "n_splits_R1": n_splits1,
            "n_splits_R5": n_splits5,
        }
    return out


# ---------------------------------------------------------------------------------------
# Item 7: null-simulation sensitivity at R=5, plug-in vs. Jeffreys.
# ---------------------------------------------------------------------------------------

def item7(models, rng, n_sims=N_NULL_SIMS):
    rs, vs = models["A"]["reps"], models["A"]["vignettes"]
    n = len(rs)
    observed_cells = {}
    for v in vs:
        for name, proj in OUTCOMES.items():
            series = [proj(r[v]) for r in rs]
            if all(x is not None for x in series):
                observed_cells[(v, name)] = series
    ks = {key: sum(1 for x in s if x) for key, s in observed_cells.items()}
    probs = {key: ks[key] / n for key in observed_cells}

    def run(draw_p):
        vals = []
        for _ in range(n_sims):
            sim_cells = {key: [rng.random() < draw_p(key) for _ in range(n)] for key in observed_cells}
            c = pn._curve(sim_cells, n, [5])
            if c[5] is not None:
                vals.append(c[5])
        return vals

    plugin_vals = run(lambda key: probs[key])
    jeffreys_vals = run(lambda key: rng.betavariate(ks[key] + 0.5, n - ks[key] + 0.5))

    def summarize(vals):
        lo, hi = pct_ci(vals)
        return {"n_sims": len(vals), "mean": sum(vals) / len(vals), "ci_2.5_97.5": (lo, hi)}

    return {
        "observed_R5_floor": 0.053,
        "n_cells": len(observed_cells),
        "plugin": summarize(plugin_vals),
        "jeffreys": summarize(jeffreys_vals),
    }


# ---------------------------------------------------------------------------------------
# Item 8: McNemar simulation. One Bernoulli draw per condition per vignette per simulation.
# ---------------------------------------------------------------------------------------

def _mcnemar_exact(b, c):
    n = b + c
    if n == 0:
        return 1.0
    obs = math.comb(n, b) * (0.5 ** n)
    total = 0.0
    for k in range(n + 1):
        pk = math.comb(n, k) * (0.5 ** n)
        if pk <= obs * (1 + 1e-9):
            total += pk
    return min(total, 1.0)


def item8(pool_rates, rng, n_sims=N_MCNEMAR_SIMS, v_values=(16, 50, 100, 300)):
    def floor_p(p):
        return 2 * p * (1 - p)

    def deltas_for(scenario, v):
        if scenario == "null":
            return [0.0] * v
        if scenario == "uniform":
            return [0.10] * v
        if scenario == "heterogeneous":
            n_pos = -(-v // 2)  # ceil
            return [0.10] * n_pos + [-0.10] * (v - n_pos)
        raise ValueError(scenario)

    out = {}
    for scenario in ("null", "uniform", "heterogeneous"):
        out[scenario] = {}
        for v in v_values:
            deltas = deltas_for(scenario, v)
            raw_flip_rates, floor_exps, delta2_excs, rejections = [], [], [], 0
            for _ in range(n_sims):
                b = c = 0
                floor_exp_sum = 0.0
                delta2_sum = 0.0
                for i in range(v):
                    p0 = rng.choice(pool_rates)
                    p1 = min(1.0, max(0.0, p0 + deltas[i]))
                    x0 = rng.random() < p0
                    x1 = rng.random() < p1
                    if x0 and not x1:
                        b += 1
                    elif x1 and not x0:
                        c += 1
                    floor_exp_sum += 0.5 * (floor_p(p0) + floor_p(p1))
                    delta2_sum += (p1 - p0) ** 2
                raw_flip_rates.append((b + c) / v)
                floor_exps.append(floor_exp_sum / v)
                delta2_excs.append(delta2_sum / v)
                pval = _mcnemar_exact(b, c)
                if pval < 0.05:
                    rejections += 1
            out[scenario][v] = {
                "mean_raw_flip_rate": sum(raw_flip_rates) / n_sims,
                "mean_floor_expectation": sum(floor_exps) / n_sims,
                "mean_delta2_excess": sum(delta2_excs) / n_sims,
                "mcnemar_rejection_rate": rejections / n_sims,
            }
    return out


# ---------------------------------------------------------------------------------------

def main():
    t_start = time.time()
    models, skipped_extra = load_models()

    canonical_v = models["A"]["vignettes"]
    for lab, m in models.items():
        if m["vignettes"] != canonical_v:
            print("FATAL: vignette set for model %s (%s) differs from model A's; the paired "
                  "bootstrap requires a shared vignette id space across models." % (lab, m["dir"]))
            return 1

    verification, obs_A_counts, vs_A, pooled_num_A, pooled_den_A = verify_published(models)
    if not verification["ok"]:
        print("PUBLISHED-ESTIMATE MISMATCH -- stopping without producing a supplement.")
        for label, got, want in verification["mismatches"]:
            print("  %-20s computed=%s published=%s" % (label, got, want))
        json.dump({"verification": verification}, open(OUT_PATH, "w"), indent=2)
        return 1
    print("Published estimates reproduced exactly (%d checks)." % len(verification["checks"]))

    obs_counts = {lab: ps.counts(m["reps"], m["vignettes"]) for lab, m in models.items()}

    rng = random.Random(SEED)  # single shared stream, consumed in this fixed order

    t0 = time.time()
    resamples = build_resamples(rng, canonical_v, B_MAIN)
    cache = cache_bootstrap_counts(models, resamples)
    r1 = item1(models, obs_counts, cache)
    r2 = item2(models, obs_counts, cache)
    r3 = item3(models, obs_counts, cache)
    r5 = item5(models, cache)
    t_boot = time.time() - t0

    t0 = time.time()
    r4 = item4(models)
    t_lovo = time.time() - t0

    t0 = time.time()
    r6 = item6(models, rng)
    t_item6 = time.time() - t0

    t0 = time.time()
    r7 = item7(models, rng)
    t_item7 = time.time() - t0

    # Item 8's reference pool: model A's 96 per-cell (vignette, action) observed rates.
    rs_A = models["A"]["reps"]
    pool_rates = []
    for v in vs_A:
        for name, proj in OUTCOMES.items():
            series = [proj(r[v]) for r in rs_A]
            if all(x is not None for x in series):
                pool_rates.append(sum(1 for x in series if x) / len(series))

    t0 = time.time()
    r8 = item8(pool_rates, rng)
    t_item8 = time.time() - t0

    n_splits = {}
    for k in (3, 5):
        n = math.comb(10, k) * math.comb(10 - k, k) // 2
        n_splits["R=%d" % k] = {"n_splits": n, "replicates_used_per_split": 2 * k,
                                 "replicates_unused_per_split": 10 - 2 * k}

    total_time = time.time() - t_start
    report = {
        "meta": {
            "seed": SEED,
            "B_main_bootstrap": B_MAIN,
            "B_small_bootstrap": B_SMALL,
            "B_item6": B_ITEM6,
            "n_null_sims": N_NULL_SIMS,
            "n_mcnemar_sims": N_MCNEMAR_SIMS,
            "models_loaded": {lab: m["dir"] for lab, m in models.items()},
            "extra_t0_dirs_skipped": skipped_extra,
            "canonical_vignette_count": len(canonical_v),
            "split_enumeration": n_splits,
            "runtime_seconds": {
                "bootstrap_items_1_2_3_5": round(t_boot, 1),
                "leave_one_vignette_out": round(t_lovo, 2),
                "item6_majority_vote_bootstrap": round(t_item6, 1),
                "item7_null_simulation": round(t_item7, 1),
                "item8_mcnemar_simulation": round(t_item8, 1),
                "total": round(total_time, 1),
            },
        },
        "verification": verification,
        "item1_per_model_action_floors": r1,
        "item2_modelA_cs_caution_vs_escalate_icu": r2,
        "item3_pairwise_model_pooled_floor_diffs": r3,
        "item4_leave_one_vignette_out": r4,
        "item5_excluding_cs_caution": r5,
        "item6_majority_vote_reduction": r6,
        "item7_null_simulation_sensitivity": r7,
        "item8_mcnemar_simulation": r8,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # --- compact printed summary -----------------------------------------------------
    print("\nwrote %s" % OUT_PATH)
    print("\nItem 1 -- pooled floor, B=600 vs B=5000 (stability):")
    for lab in sorted(models):
        p = r1["models"][lab]["pooled"]
        print("  %s  floor=%.3f  B=600 %s  B=5000 %s"
              % (lab, p["floor"],
                 "[%.3f, %.3f]" % p["ci"]["B=600"],
                 "[%.3f, %.3f]" % p["ci"]["B=5000"]))

    print("\nItem 2 -- model A cs_caution vs escalate_icu:")
    print("  diff=%.3f  CI(B5000)=[%.3f, %.3f]  ratio=%.2f  icu-floor-zero in %.1f%% of resamples (bounded=%s)"
          % (r2["observed"]["difference"], r2["difference_ci_B5000"][0], r2["difference_ci_B5000"][1],
             r2["observed"]["ratio"], 100 * r2["ratio"]["fraction_icu_floor_zero"], r2["ratio"]["bounded"]))

    print("\nItem 3 -- pairwise pooled-floor diffs (15 pairs), largest |diff| pairs:")
    for row in sorted(r3, key=lambda r: -abs(r["observed_diff"]))[:5]:
        print("  %-4s diff=%.3f CI=[%.3f, %.3f]" % (row["pair"], row["observed_diff"], *row["ci_B5000"]))

    print("\nItem 4 -- leave-one-vignette-out, pooled floor range:")
    for lab in sorted(r4):
        e = r4[lab]
        print("  %s  [%.3f, %.3f]" % (lab, e["min_pooled_floor"], e["max_pooled_floor"]), end="")
        if "cs_minus_icu_min" in e:
            print("   (A: cs-icu diff [%.3f, %.3f])" % (e["cs_minus_icu_min"], e["cs_minus_icu_max"]), end="")
        print()

    print("\nItem 5 -- excluding cs_caution:")
    for lab in sorted(r5["models"]):
        e = r5["models"][lab]
        print("  %s  floor=%.3f CI=[%.3f, %.3f]" % (lab, e["floor"], *e["ci_B5000"]))
    mA = r5["modelA_majority_vote_excl_cs_caution"]
    print("  A curve: " + "  ".join("R=%d %.3f" % (k, mA["curve"][k]["rate"]) for k in (1, 3, 5))
          + "  reduction=%.3f" % mA["reduction_1_minus_f5_f1"])

    print("\nItem 6 -- majority-vote reduction 1-f5/f1 (B=%d):" % r6["B"])
    for lab, e in r6["models"].items():
        print("  %s  observed=%.3f CI=[%.3f, %.3f]" % (lab, e["reduction_observed"], *e["reduction_ci"]))

    print("\nItem 7 -- R=5 null sensitivity (observed=0.053):")
    print("  plug-in : mean=%.3f CI=[%.3f, %.3f]" % (r7["plugin"]["mean"], *r7["plugin"]["ci_2.5_97.5"]))
    print("  Jeffreys: mean=%.3f CI=[%.3f, %.3f]" % (r7["jeffreys"]["mean"], *r7["jeffreys"]["ci_2.5_97.5"]))

    print("\nItem 8 -- McNemar simulation (mean raw flip / mean floor-exp / mean delta^2 / rejection rate):")
    for scenario in ("null", "uniform", "heterogeneous"):
        print("  %s:" % scenario)
        for v in (16, 50, 100, 300):
            e = r8[scenario][v]
            print("    V=%-4d flip=%.3f floor_exp=%.3f delta2=%.3f reject=%.3f"
                  % (v, e["mean_raw_flip_rate"], e["mean_floor_expectation"],
                     e["mean_delta2_excess"], e["mcnemar_rejection_rate"]))

    print("\ntotal runtime: %.1f s" % total_time)
    return 0


if __name__ == "__main__":
    sys.exit(main())
