"""Zero-observed floor bounds, replicate-only (fixed-case) intervals, and S12 achieved shifts.

Three outputs, written to experiments/fixed_case_bounds_v3.json:

1. zero_bounds. For every floor (pooled or per action, every arm) whose observed value is 0 or
   whose crossed interval is [0, 0], one-sided 95% upper bounds:
     - fixed_case_exact: test inversion of the observed event "every vignette x action cell
       unanimous". With per-cell minority probabilities q_c, P(all n cells unanimous) =
       prod_c [(1-q_c)^R + q_c^R]. The set {q : P >= 0.05} is an exact 95% confidence region
       (the event is the most extreme value of the non-unanimous-cell count). The bound is the
       maximum of the fixed-case floor mean_c 2 q_c (1-q_c) over that region. Writing
       s_c = -log(1-q_c), the floor kernel 2(e^-s - e^-2s) is concave for s < ln 4 and every
       feasible s_c is below -ln(0.05)/R <= 0.6, so by Jensen the maximum is at equal q_c:
       the common-probability bound is ALSO the heterogeneity-robust bound for the fixed cells.
       Checked numerically (SLSQP from random heterogeneous starts) below.
     - common_p_cp: the simple Clopper-Pearson form q_u = 1 - 0.05^(1/N), N = cells x R,
       floor <= 2 q_u (1-q_u). Agrees with fixed_case_exact to 4 decimals.
     - per_vignette_own_bound: every cell at its own R-draw bound 1 - 0.05^(1/R). Not a 95%
       joint bound (far more conservative); reported for comparison.
     - population_bound: case-population estimand (floor of a NEW vignette from the generating
       distribution H). P(all G vignettes unanimous) = (E_H[g])^G with g the per-vignette
       unanimity probability over its K actions. Maximise E_H[h] s.t. E_H[g] >= 0.05^(1/G) by
       linear programming over a grid of vignette types (j of K actions at minority prob q).
2. replicate_only. Vignettes fixed, replicates resampled with replacement (off-diagonal
   m_a*m_b weighting, self-pairs excluded, as crossed_boot.py), B=5000, random.Random(42),
   one draw sequence per model in sorted label order. Fixed-case interval.
3. s12_achieved_shifts. Exact expectation (no simulation) of the clipped shift p1-p0 and its
   square for robustness.py item 8's pool (model A's 96 per-cell rates, six actions).

Run: FMA_PANEL=v3 python harness/scripts/fixed_case_bounds.py
"""
from __future__ import annotations

import json
import os
import random
import sys

import numpy as np
from scipy.optimize import brentq, linprog, minimize

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crossed_boot as cb  # noqa: E402
import robustness as rb  # noqa: E402

pc = cb.pc
ALPHA = 0.05
B = 5000
OUT = os.path.join(pc.EXP, "fixed_case_bounds%s.json" % pc.SUFFIX)


# ------------------------------------------------------------------ bounds

def g_cell(q, R):
    return (1 - q) ** R + q ** R


def fixed_case_exact(n_cells, R, alpha=ALPHA):
    target = alpha ** (1.0 / n_cells)
    q = brentq(lambda x: g_cell(x, R) - target, 0.0, 0.5 - 1e-12)
    return q, 2 * q * (1 - q)


def common_p_cp(n_cells, R, alpha=ALPHA):
    q = 1 - alpha ** (1.0 / (n_cells * R))
    return q, 2 * q * (1 - q)


def own_bound(R, alpha=ALPHA):
    q = 1 - alpha ** (1.0 / R)
    return q, 2 * q * (1 - q)


def hetero_check(n_cells, R, alpha=ALPHA, starts=20, seed=0):
    """Numerical max of mean 2q(1-q) s.t. sum log g(q_c) >= log alpha, from random starts."""
    rng = np.random.default_rng(seed)
    best = 0.0
    cons = {"type": "ineq", "fun": lambda q: np.sum(np.log(g_cell(q, R))) - np.log(alpha)}
    for _ in range(starts):
        x0 = rng.dirichlet(np.ones(n_cells) * 0.3) * 0.02 * n_cells
        x0 = np.clip(x0, 0, 0.45)
        r = minimize(lambda q: -np.mean(2 * q * (1 - q)), x0, method="SLSQP", constraints=[cons],
                     bounds=[(0, 0.5)] * n_cells, options={"maxiter": 500, "ftol": 1e-12})
        if r.success and cons["fun"](r.x) >= -1e-9:
            best = max(best, -r.fun)
    return best


def population_bound(G, R, K, alpha=ALPHA):
    """Max E_H[h] s.t. E_H[g] >= alpha^(1/G), H over vignette types (j of K actions at q)."""
    c = alpha ** (1.0 / G)
    qs = np.linspace(0.0, 0.5, 501)[1:]
    gs, hs = [1.0], [0.0]
    for j in range(1, K + 1):
        for q in qs:
            gs.append(g_cell(q, R) ** j)
            hs.append(j * 2 * q * (1 - q) / K)
    gs, hs = np.array(gs), np.array(hs)
    # variables: weights w_t >= 0; sum w = 1; sum w g >= c; maximise sum w h
    r = linprog(-hs, A_ub=[-gs], b_ub=[-c], A_eq=[np.ones_like(gs)], b_eq=[1.0], bounds=(0, None), method="highs")
    w = r.x
    atoms = [(int(i), float(w[i]), float(hs[i]), float(gs[i])) for i in np.nonzero(w > 1e-9)[0]]
    return float(-r.fun), atoms


def bound_row(label, G, K, R):
    n_cells = G * K
    qe, fe = fixed_case_exact(n_cells, R)
    qc, fc = common_p_cp(n_cells, R)
    qo, fo = own_bound(R)
    fp, atoms = population_bound(G, R, K)
    return {"quantity": label, "G": G, "K": K, "R": R, "n_cells": n_cells, "n_draws": n_cells * R,
            "fixed_case_exact_q": qe, "fixed_case_exact_floor_ub": fe,
            "common_p_cp_q": qc, "common_p_cp_floor_ub": fc,
            "hetero_numeric_max": hetero_check(n_cells, R) if n_cells <= 96 else None,
            "per_vignette_own_bound_floor": fo, "population_floor_ub": fp, "population_lp_atoms": atoms}


# ------------------------------------------------------------------ data

def arm_counts(arm):
    n, d = arm.counts(np.ones(arm.R), np.ones(arm.V))
    return n, d


def all_arms():
    models, _ = rb.load_models()
    arms = {}
    for lab in "ABCDEF":
        arms[lab] = cb.Arm(models[lab]["reps"], models[lab]["vignettes"])
    for lab in "CDEF":
        reps = cb.load_dir(pc.local_dir(lab, True))
        arms[lab + "_t0"] = cb.Arm(reps, sorted(cb.complete_vs(reps)))
        # paired with default arm (vignettes complete in both), as the temperature table
        d = cb.load_dir(pc.local_dir(lab))
        vs = sorted(cb.complete_vs(d) & cb.complete_vs(reps))
        arms[lab + "_t0_paired"] = cb.Arm(reps, vs)
    g0 = cb.load_dir("floor16_groq_t0")
    arms["groq_t0"] = cb.Arm(g0, sorted(cb.complete_vs(g0)))
    g1 = cb.load_dir("floor16_groq_t1")
    arms["groq_t1"] = cb.Arm(g1, sorted(cb.complete_vs(g1)))
    return arms


def unanimous_cells(arm, k):
    X = arm.X[:, :, k]
    ok = ~np.isnan(X).any(0)
    un = ok & ((np.nansum(X, 0) == 0) | (np.nansum(X, 0) == arm.R))
    return int(ok.sum()), int(un.sum())


def zero_bounds(arms):
    rows = []
    for name, arm in arms.items():
        n, d = arm_counts(arm)
        for tag, idx in (("pooled_5action", cb.I5), ("pooled_6action", list(range(6)))):
            if n[idx].sum() == 0:
                G = arm.V
                r = bound_row("%s %s" % (name, tag), G, len(idx), arm.R)
                r["observed"] = "0/%d" % int(d[idx].sum())
                rows.append(r)
        for k, key in enumerate(cb.KEYS):
            if d[k] > 0 and n[k] == 0:
                ncell, nun = unanimous_cells(arm, k)
                r = bound_row("%s %s" % (name, key), ncell, 1, arm.R)
                r["observed"] = "0/%d" % int(d[k])
                rows.append(r)
    return rows


# ------------------------------------------------------------------ replicate-only

def rep_only(arms, labs):
    rng = random.Random(42)
    draws = {lab: [[rng.randrange(arms[lab].R) for _ in range(arms[lab].R)] for _ in range(B)] for lab in labs}
    out = {}
    for lab in labs:
        a = arms[lab]
        w = np.ones(a.V)
        num = np.zeros((B, 6))
        den = np.zeros((B, 6))
        for b in range(B):
            num[b], den[b] = a.counts(cb.mult(draws[lab][b], a.R), w)
        n0, d0 = arm_counts(a)
        e = {"R": a.R, "G": a.V}
        for tag, idx in (("5action", cb.I5), ("6action", list(range(6)))):
            dd = den[:, idx].sum(1)
            v = np.where(dd > 0, num[:, idx].sum(1) / np.where(dd > 0, dd, 1), np.nan)
            e["floor_%s" % tag] = float(n0[idx].sum() / d0[idx].sum())
            e["rep_only_ci_%s" % tag] = cb.ci(v)
            e["n_dropped"] = int(np.isnan(v).sum())
        e["actions"] = {}
        for k, key in enumerate(cb.KEYS):
            v = np.where(den[:, k] > 0, num[:, k] / np.where(den[:, k] > 0, den[:, k], 1), np.nan)
            e["actions"][key] = {"floor": float(n0[k] / d0[k]), "rep_only_ci": cb.ci(v)}
        out[lab] = e
    return out


# ------------------------------------------------------------------ S12

def s12_shifts():
    models, _ = rb.load_models()
    rs_A, vs_A = models["A"]["reps"], models["A"]["vignettes"]
    pool = []
    for v in vs_A:
        for name, proj in rb.OUTCOMES.items():
            s = [proj(r[v]) for r in rs_A]
            if all(x is not None for x in s):
                pool.append(sum(1 for x in s if x) / len(s))
    p = np.array(pool)
    up = np.clip(p + 0.10, 0, 1) - p
    dn = np.clip(p - 0.10, 0, 1) - p
    out = {"pool_size": len(p), "frac_p_eq_0": float((p == 0).mean()), "frac_p_eq_1": float((p == 1).mean()),
           "uniform_+0.10": {"mean_signed": float(up.mean()), "mean_abs": float(np.abs(up).mean()),
                             "mean_sq": float((up ** 2).mean())},
           "opposing_+-0.10_half": {"plus_half_mean_signed": float(up.mean()), "minus_half_mean_signed": float(dn.mean()),
                                    "mean_signed": float((up.mean() + dn.mean()) / 2),
                                    "mean_abs": float((np.abs(up).mean() + np.abs(dn).mean()) / 2),
                                    "mean_sq": float(((up ** 2).mean() + (dn ** 2).mean()) / 2)}}
    return out


def main():
    arms = all_arms()
    res = {"meta": {"alpha_one_sided": ALPHA, "B_rep_only": B, "seed": 42,
                    "arms": {k: {"R": a.R, "G": a.V} for k, a in arms.items()}},
           "zero_bounds": zero_bounds(arms),
           "replicate_only": rep_only(arms, list("ABCDEF")),
           "s12_achieved_shifts": s12_shifts()}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=float)
    print("wrote", OUT)
    for r in res["zero_bounds"]:
        print("%-34s G=%2d K=%d R=%2d exact=%.4f cp=%.4f het=%s own=%.3f pop=%.4f obs=%s" % (
            r["quantity"], r["G"], r["K"], r["R"], r["fixed_case_exact_floor_ub"], r["common_p_cp_floor_ub"],
            "%.4f" % r["hetero_numeric_max"] if r["hetero_numeric_max"] is not None else "-",
            r["per_vignette_own_bound_floor"], r["population_floor_ub"], r["observed"]))
    for lab, e in res["replicate_only"].items():
        print(lab, "5a %.3f %s 6a %.3f %s" % (e["floor_5action"], np.round(e["rep_only_ci_5action"], 3),
                                             e["floor_6action"], np.round(e["rep_only_ci_6action"], 3)))
    for k, v in res["replicate_only"]["A"]["actions"].items():
        print("  A", k, round(v["floor"], 3), np.round(v["rep_only_ci"], 3))
    print(json.dumps(res["s12_achieved_shifts"], indent=1))


if __name__ == "__main__":
    main()
