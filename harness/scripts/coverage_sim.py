"""Coverage of the crossed (vignette x replicate) bootstrap percentile interval for the floor.

For each data-generating scenario we simulate datasets of G=16 vignettes x
K=5 actions x R replicates (binary answers), compute the pooled floor (discordant replicate
pairs / all pairs, as crossed_boot.py) and three 95% percentile intervals with B resamples:

  crossed     vignettes and replicates resampled independently with replacement; off-diagonal
              m_a*m_b pair weighting (self-pairs of one replicate excluded), as crossed_boot.py
  rep_only    vignettes fixed, replicates resampled (same pair rule)  -> fixed-case interval
  vig_only    replicates fixed, vignettes resampled (the pre-crossed method)

and a hybrid rule: crossed interval if the observed floor > 0, else [0, U] with U the exact
one-sided 95% fixed-case bound of fixed_case_bounds.py (2q(1-q), q solving
[(1-q)^R + q^R]^(G*K) = 0.05).

Two estimands, both computed exactly (no plug-in):
  fixed-case   theta_F = mean over the dataset's G*K cells of 2 m_c (1 - m_c), where
               m_c = E_u[expit(logit p_c + u)] integrates the replicate shift u (0 when the
               scenario has none). The expected floor on THESE vignettes over new replicates.
  population   theta_P = E[2 m (1 - m)] over the cell-generating distribution (a new vignette),
               by Monte Carlo over 2,000,000 cells (MC s.e. reported).

Between-model difference: model 1 = the scenario, model 2 = S3 (model-A fit, R=10, no replicate
shift), cells coupled through a Gaussian copula (rho = 0.5) on their instability rank
min(p, 1-p); vignette resample shared, replicate resamples independent per model, as in
crossed_boot.py. Coverage of theta(model 1) - theta(model 2) for both estimands.

Scenarios (p = probability of the positive answer in a cell):
  S1 sparse        q ~ Beta(0.3, 25), random orientation; true floor ~ 0.022
  S2 near-boundary 90% of cells q = 0, else q ~ Beta(1, 19); true floor ~ 0.009
  S3 heterogeneous model A's five-action cells, MLE of p ~ w0*delta0 + w1*delta1 + wm*Beta(a,b)
                   fitted by beta-binomial likelihood to the 80 observed (k of 10) cells
  S4 replicate dep S3 plus a shared per-replicate logit shift u_r ~ N(0, sigma^2); sigma tuned so
                   the between-replicate variance ratio of the per-replicate mean rate (the
                   permutation diagnostic of CROSSED_BOOT.md) is about 1.5-2 at R=10
  S5               S4 at R=6 (model B's replicate count)
S1-S3 are also run at R=5 (temperature-0-like replicate count).

Run:  python harness/scripts/coverage_sim.py [--nsim 1000] [--B 1000] [--seed 20261012]
Writes experiments/COVERAGE_SIM.json.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
from scipy.optimize import brentq
from scipy.special import expit, logit
from scipy.stats import norm

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "experiments", "COVERAGE_SIM.json")

G, K = 16, 5
# Model A five-action fit (beta-binomial mixture MLE on the 80 observed cells, R=10; see
# fit_model_a() for the reproducible fit, run when --refit is given).
A_FIT = {"w0": 0.452, "w1": 0.0, "wm": 0.548, "a": 0.626, "b": 0.135}
GH_X, GH_W = np.polynomial.hermite_e.hermegauss(40)
GH_W = GH_W / GH_W.sum()


# ------------------------------------------------------------------ cell distributions

def orient(q, rng):
    return np.where(rng.random(q.shape) < 0.5, q, 1 - q)


def draw_p(scn, n, rng):
    if scn == "S1":
        return orient(rng.beta(0.3, 25, n), rng)
    if scn == "S2":
        q = np.where(rng.random(n) < 0.9, 0.0, rng.beta(1, 19, n))
        return orient(q, rng)
    # S3 / S4 / S5 / model-2: model-A fit
    u = rng.random(n)
    p = rng.beta(A_FIT["a"], A_FIT["b"], n)
    p = np.where(u < A_FIT["w0"], 0.0, np.where(u < A_FIT["w0"] + A_FIT["w1"], 1.0, p))
    return p


def m_of(p, sigma):
    """E_u[expit(logit p + u)], u ~ N(0, sigma^2); boundary cells stay at 0 / 1."""
    if sigma == 0:
        return p
    inner = (p > 0) & (p < 1)
    m = p.astype(float).copy()
    lp = logit(np.clip(p[inner], 1e-300, 1 - 1e-16))
    m[inner] = expit(lp[:, None] + sigma * GH_X[None, :]) @ GH_W
    return m


def population_truth(scn, sigma, rng, n=2_000_000):
    p = draw_p(scn, n, rng)
    m = m_of(p, sigma)
    f = 2 * m * (1 - m)
    return float(f.mean()), float(f.std() / np.sqrt(n))


# ------------------------------------------------------------------ data + bootstrap

def simulate(p_cells, R, sigma, rng):
    """p_cells (G, K) -> X (R, G, K) binary with shared per-replicate logit shift."""
    if sigma > 0:
        u = rng.normal(0, sigma, R)
        inner = (p_cells > 0) & (p_cells < 1)
        lp = logit(np.clip(p_cells, 1e-300, 1 - 1e-16))
        P = np.where(inner[None], expit(lp[None] + u[:, None, None]), p_cells[None])
    else:
        P = np.broadcast_to(p_cells, (R,) + p_cells.shape)
    return (rng.random((R,) + p_cells.shape) < P).astype(np.int8)


RHO_DEP = 0.8


def simulate_dep(p_cells, R, dep, rng):
    """Within-trajectory action dependence (v4). p_cells (G, K) marginals are kept exactly.
    'copula'    : per (replicate, vignette) a Gaussian copula with equicorrelation RHO_DEP across the K actions.
    'identical' : one uniform per (replicate, vignette) shared by all K actions (comonotone; p_cells columns equal).
    Replicates are independent draws in both."""
    Gv, Kv = p_cells.shape
    if dep == "identical":
        u = rng.random((R, Gv, 1))
    else:
        w = rng.standard_normal((R, Gv, 1))
        e = rng.standard_normal((R, Gv, Kv))
        u = norm.cdf(np.sqrt(RHO_DEP) * w + np.sqrt(1 - RHO_DEP) * e)
    return (u < p_cells[None]).astype(np.int8)


def pair_tensor(X):
    R = X.shape[0]
    ia, ib = np.triu_indices(R, 1)
    return ia, ib, (X[ia] != X[ib]).sum(-1).astype(float)    # (P, G): discordant actions per pair x vignette


def boot_stats(D, ia, ib, R, W, M):
    """Pooled floor for vignette weights W (B, G) and replicate multiplicities M (B, R)."""
    MP = M[:, ia] * M[:, ib]
    num = np.einsum("bp,pg,bg->b", MP, D, W)
    den = MP.sum(1) * W.sum(1) * K
    out = np.full(len(num), np.nan)
    ok = den > 0
    out[ok] = num[ok] / den[ok]
    return out


def pct(v):
    v = np.sort(v[~np.isnan(v)])
    n = len(v)
    return v[int(0.025 * n)], v[min(n - 1, int(0.975 * n))]


def zero_bound(n_cells, R, alpha=0.05):
    t = alpha ** (1.0 / n_cells)
    q = brentq(lambda x: (1 - x) ** R + x ** R - t, 0.0, 0.5 - 1e-12)
    return 2 * q * (1 - q)


def dep_robust_bound(Gv, R, alpha=0.05):
    """v4 bound: each vignette a unit with floor F_v; equal F_v is the maximum (zero_bounds_v4.py)."""
    t = alpha ** (1.0 / Gv)
    q = brentq(lambda x: (1 - x) ** R + x ** R - t, 0.0, 0.5 - 1e-12)
    return 2 * q * (1 - q)


def couple(n, rho, rng):
    z1 = rng.standard_normal(n)
    z2 = rho * z1 + np.sqrt(1 - rho ** 2) * rng.standard_normal(n)
    return norm.cdf(z1), norm.cdf(z2)


def draw_by_rank(scn, u, rng, ref):
    """Cell p with instability rank u (ref: sorted reference sample by min(p,1-p))."""
    idx = np.minimum((u * len(ref)).astype(int), len(ref) - 1)
    return ref[idx]


def make_ref(scn, rng, n=400_000):
    p = draw_p(scn, n, rng)
    q = np.minimum(p, 1 - p)
    return p[np.argsort(q, kind="stable")]


# ------------------------------------------------------------------ dependence diagnostic (tuning)

def rep_var_ratio(sigma, R, rng, nsets=300, nperm=30):
    obs, null = [], []
    for _ in range(nsets):
        p = draw_p("S3", G * K, rng).reshape(G, K)
        X = simulate(p, R, sigma, rng).reshape(R, -1).astype(float)
        obs.append(np.var(X.mean(1), ddof=1))
        for _ in range(nperm):
            perm = np.argsort(rng.random(X.shape), axis=0)
            null.append(np.var(np.take_along_axis(X, perm, 0).mean(1), ddof=1))
    return float(np.mean(obs) / np.mean(null))


def tune_sigma(rng, target=1.75):
    grid = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]
    ratios = {s: rep_var_ratio(s, 10, rng) for s in grid}
    # pick grid point closest to target, then refine linearly
    s_sorted = sorted(ratios)
    best = min(s_sorted, key=lambda s: abs(ratios[s] - target))
    return best, ratios


# ------------------------------------------------------------------ one scenario

def run_scenario(name, scn, R, sigma, nsim, B, rng, ref1, ref2, theta_p1, theta_p2, dep=None):
    zb = zero_bound(G * K, R)
    zb_new = dep_robust_bound(G, R)
    zstat = {"n_zero": 0, "old_miss_F": 0, "new_miss_F": 0, "old_miss_P": 0, "new_miss_P": 0}
    R2 = 10
    keys = ["crossed", "rep_only", "vig_only", "hybrid"]
    hit = {e: {k: 0 for k in keys} for e in ("fixed", "population")}
    miss_lo = {e: 0 for e in ("fixed", "population")}   # truth below interval (crossed)
    miss_hi = {e: 0 for e in ("fixed", "population")}   # truth above interval (crossed)
    dhit = {e: {"crossed": 0, "vig_only": 0, "rep_only": 0} for e in ("fixed", "population")}
    n_zero = 0
    hybnew_hit_F = hybnew_hit_P = 0
    widths = []
    theta_f_all, est_all = [], []
    for _ in range(nsim):
        u1, u2 = couple(G * K, 0.5, rng)
        p1 = draw_by_rank(scn, u1, rng, ref1).reshape(G, K)
        if dep == "identical":
            p1 = np.repeat(p1[:, :1], K, axis=1)
        p2 = draw_by_rank("S3", u2, rng, ref2).reshape(G, K)
        m1 = m_of(p1.ravel(), sigma)
        th_f1 = float(np.mean(2 * m1 * (1 - m1)))
        th_f2 = float(np.mean(2 * p2 * (1 - p2)))
        X1 = simulate(p1, R, sigma, rng) if dep is None else simulate_dep(p1, R, dep, rng)
        X2 = simulate(p2, R2, 0.0, rng)
        ia, ib, D1 = pair_tensor(X1)
        ja, jb, D2 = pair_tensor(X2)
        est = D1.sum() / (len(ia) * G * K)
        est2 = D2.sum() / (len(ja) * G * K)
        W = rng.multinomial(G, np.full(G, 1.0 / G), size=B).astype(float)
        M1 = rng.multinomial(R, np.full(R, 1.0 / R), size=B).astype(float)
        M2 = rng.multinomial(R2, np.full(R2, 1.0 / R2), size=B).astype(float)
        onesW, onesM1, onesM2 = np.ones_like(W), np.ones_like(M1), np.ones_like(M2)
        bc = boot_stats(D1, ia, ib, R, W, M1)
        br = boot_stats(D1, ia, ib, R, onesW, M1)
        bv = boot_stats(D1, ia, ib, R, W, onesM1)
        ci = {"crossed": pct(bc), "rep_only": pct(br), "vig_only": pct(bv)}
        if est == 0:
            n_zero += 1
            ci["hybrid"] = (0.0, zb)
            zstat["n_zero"] += 1
            zstat["old_miss_F"] += int(th_f1 > zb)
            zstat["new_miss_F"] += int(th_f1 > zb_new)
            zstat["old_miss_P"] += int(theta_p1 > zb)
            zstat["new_miss_P"] += int(theta_p1 > zb_new)
        else:
            ci["hybrid"] = ci["crossed"]
        hyb_new = (0.0, zb_new) if est == 0 else ci["crossed"]
        hybnew_hit_F += int(hyb_new[0] - 1e-12 <= th_f1 <= hyb_new[1] + 1e-12)
        hybnew_hit_P += int(hyb_new[0] - 1e-12 <= theta_p1 <= hyb_new[1] + 1e-12)
        widths.append(ci["crossed"][1] - ci["crossed"][0])
        for e, th in (("fixed", th_f1), ("population", theta_p1)):
            for k in keys:
                lo, hi = ci[k]
                hit[e][k] += int(lo - 1e-12 <= th <= hi + 1e-12)
            lo, hi = ci["crossed"]
            miss_lo[e] += int(th < lo - 1e-12)
            miss_hi[e] += int(th > hi + 1e-12)
        # difference model1 - model2
        dc = bc - boot_stats(D2, ja, jb, R2, W, M2)
        dr = br - boot_stats(D2, ja, jb, R2, onesW, M2)
        dv = bv - boot_stats(D2, ja, jb, R2, W, onesM2)
        for e, th in (("fixed", th_f1 - th_f2), ("population", theta_p1 - theta_p2)):
            for k, arr in (("crossed", dc), ("rep_only", dr), ("vig_only", dv)):
                lo, hi = pct(arr)
                dhit[e][k] += int(lo - 1e-12 <= th <= hi + 1e-12)
        theta_f_all.append(th_f1)
        est_all.append(est)
    f = lambda c: round(c / nsim, 4)
    return {"scenario": name, "R": R, "sigma": sigma, "nsim": nsim, "B": B,
            "theta_population": theta_p1, "mean_theta_fixed": float(np.mean(theta_f_all)),
            "mean_estimate": float(np.mean(est_all)), "zero_bound": zb,
            "frac_zero_observed": f(n_zero), "mean_crossed_width": float(np.mean(widths)),
            "coverage_floor": {e: {k: f(v) for k, v in hit[e].items()} for e in hit},
            "crossed_miss_truth_below": {e: f(v) for e, v in miss_lo.items()},
            "crossed_miss_truth_above": {e: f(v) for e, v in miss_hi.items()},
            "coverage_difference_vs_S3_model": {e: {k: f(v) for k, v in dhit[e].items()} for e in dhit},
            "theta_population_model2": theta_p2, "dependence": dep or "none",
            "zero_bound_old_independence": zb, "zero_bound_new_dependence_robust": zb_new,
            "coverage_hybrid_new_bound": {"fixed": f(hybnew_hit_F), "population": f(hybnew_hit_P)},
            "zero_bound_check": {"n_zero_observed": zstat["n_zero"],
                                 "P_zero_and_truth_above_old_bound": {"fixed": f(zstat["old_miss_F"]), "population": f(zstat["old_miss_P"])},
                                 "P_zero_and_truth_above_new_bound": {"fixed": f(zstat["new_miss_F"]), "population": f(zstat["new_miss_P"])},
                                 "nominal_max": 0.05}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--nsim", type=int, default=1000)
    ap.add_argument("--B", type=int, default=1000)
    ap.add_argument("--seed", type=int, default=20261012)
    ap.add_argument("--v4", action="store_true", help="also run the within-trajectory dependence scenarios; write COVERAGE_SIM_v4.json")
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)
    t0 = time.time()
    sigma, ratios = tune_sigma(rng)
    t_tune = time.time() - t0
    ratio_R6 = rep_var_ratio(sigma, 6, rng)
    plan = [("S1 sparse", "S1", 10, 0.0), ("S1 sparse", "S1", 5, 0.0),
            ("S2 near-boundary", "S2", 10, 0.0), ("S2 near-boundary", "S2", 5, 0.0),
            ("S3 heterogeneous (A fit)", "S3", 10, 0.0), ("S3 heterogeneous (A fit)", "S3", 5, 0.0),
            ("S4 replicate dependence", "S3", 10, sigma), ("S5 replicate dependence, R=6", "S3", 6, sigma)]
    if args.v4:
        for dep, tag in (("copula", "rho=0.8 copula"), ("identical", "identical actions")):
            for scn, nm in (("S1", "S1 sparse"), ("S2", "S2 near-boundary"), ("S3", "S3 heterogeneous")):
                for R_ in (10, 5):
                    plan.append(("%s + %s" % (nm, tag), scn, R_, 0.0, dep))
    plan = [pl if len(pl) == 5 else pl + (None,) for pl in plan]
    ref2 = make_ref("S3", rng)
    th2, _ = population_truth("S3", 0.0, rng)
    refs, truths = {}, {}
    res = []
    for name, scn, R, sg, dep in plan:
        if scn not in refs:
            refs[scn] = make_ref(scn, rng)
        if (scn, sg) not in truths:
            truths[(scn, sg)] = population_truth(scn, sg, rng)
        t1 = time.time()
        r = run_scenario(name, scn, R, sg, args.nsim, args.B, rng, refs[scn], ref2, truths[(scn, sg)][0], th2, dep)
        r["population_truth_mc_se"] = truths[(scn, sg)][1]
        r["seconds"] = round(time.time() - t1, 1)
        res.append(r)
        cf, cp = r["coverage_floor"]["fixed"], r["coverage_floor"]["population"]
        print("%-30s R=%2d th_P=%.4f zero=%.3f | fixed: X %.3f rep %.3f vig %.3f hyb %.3f | pop: X %.3f rep %.3f vig %.3f hyb %.3f | diff X F %.3f P %.3f (%ss)" % (
            name, R, r["theta_population"], r["frac_zero_observed"], cf["crossed"], cf["rep_only"], cf["vig_only"], cf["hybrid"],
            cp["crossed"], cp["rep_only"], cp["vig_only"], cp["hybrid"],
            r["coverage_difference_vs_S3_model"]["fixed"]["crossed"], r["coverage_difference_vs_S3_model"]["population"]["crossed"],
            r["seconds"]), flush=True)
    out = {"meta": {"G": G, "K": K, "nsim": args.nsim, "B": args.B, "seed": args.seed, "A_fit": A_FIT,
                    "sigma_tuned": sigma, "rep_var_ratio_by_sigma_R10": ratios, "rep_var_ratio_at_sigma_R6": ratio_R6,
                    "tuning_seconds": round(t_tune, 1), "total_seconds": round(time.time() - t0, 1),
                    "interval": "percentile, index int(0.025n) and min(n-1, int(0.975n)) as crossed_boot.pct",
                    "copula_rho_model2": 0.5},
           "scenarios": res}
    if args.v4:
        out["meta"]["v4_dependence"] = {"copula_rho_within_trajectory": RHO_DEP,
                                        "note": "scenarios with dep != none keep every cell marginal and hence both truths; first 8 scenarios are the original plan rerun in the same RNG stream"}
    with open(OUT.replace(".json", "_v4.json") if args.v4 else OUT, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1, default=float)
    print("wrote", OUT, "sigma", sigma, ratios, "R6 ratio", ratio_R6)


if __name__ == "__main__":
    main()
