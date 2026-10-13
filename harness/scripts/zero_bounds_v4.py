"""Dependence-robust zero-discordance bounds (v4). Writes experiments/zero_bounds_v4.json.

Unit: a vignette v (all K actions, R replicates). F_v = mean_k f_vk, f = 2q(1-q).
P(v all-unanimous) <= min_k U(f_vk) <= U(F_v), U(f) = (1-q)^R + q^R, q = smaller root of f = 2q(1-q).
Vignettes independent -> bound = max (1/V) sum F_v s.t. sum log U(F_v) >= log alpha.
Run: FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/zero_bounds_v4.py
"""
from __future__ import annotations

import itertools
import json
import os

import numpy as np
from scipy.optimize import brentq, minimize, minimize_scalar

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "experiments", "zero_bounds_v4.json")
ALPHA = 0.05


def q_of_f(f):
    return (1 - np.sqrt(np.maximum(1 - 2 * f, 0))) / 2


def U(f, R):
    q = q_of_f(f)
    return (1 - q) ** R + q ** R


def phi(f, R):
    return np.log(U(f, R))


def equal_bound(V, R, alpha=ALPHA):
    """Equal F_v: exact solution of [(1-q)^R+q^R]^V = alpha."""
    t = alpha ** (1.0 / V)
    q = brentq(lambda x: (1 - x) ** R + x ** R - t, 0.0, 0.5 - 1e-13)
    return q, 2 * q * (1 - q)


def b_from_rem(rem, R):
    if rem <= phi(0.5, R):
        return 0.5
    return brentq(lambda x: phi(x, R) - rem, 0.0, 0.5)


def two_level_max(V, R, alpha=ALPHA, ngrid=4001):
    """Max mean F with m vignettes at level a and V-m at level b (b solved from the constraint)."""
    c = np.log(alpha)
    best = (-1.0, None)
    fa = np.linspace(0, 0.5, ngrid)
    pa = phi(fa, R)
    for m in range(1, V + 1):
        if m == V:
            ok = pa >= c / V
            i = np.nonzero(ok)[0].max()
            if fa[i] > best[0]:
                best = (fa[i], (V, float(fa[i]), 0, 0.0))
            continue
        for i in range(ngrid):
            rem = (c - m * pa[i]) / (V - m)
            if rem > 0:
                continue
            b = b_from_rem(rem, R)
            val = (m * fa[i] + (V - m) * b) / V
            if val > best[0]:
                best = (val, (m, float(fa[i]), V - m, float(b)))
    return best[0], best[1]


def multi_start(V, R, starts=300, seed=42, alpha=ALPHA):
    rng = np.random.default_rng(seed)
    c = np.log(alpha)
    cons = {"type": "ineq", "fun": lambda f: np.sum(phi(np.clip(f, 0, .5), R)) - c}
    best, bestx = 0.0, None
    for s in range(starts):
        kind = s % 3
        if kind == 0:
            x0 = rng.dirichlet(np.ones(V) * 0.3) * rng.uniform(0.1, 0.6) * V
        elif kind == 1:
            x0 = rng.random(V) * rng.uniform(0.0, 0.1)
        else:
            x0 = np.zeros(V)
            x0[rng.integers(V)] = rng.uniform(0.2, 0.5)
        x0 = np.clip(x0, 0, 0.5)
        r = minimize(lambda f: -np.mean(f), x0, method="SLSQP", constraints=[cons], bounds=[(0, 0.5)] * V,
                     options={"maxiter": 1000, "ftol": 1e-14})
        if cons["fun"](r.x) >= -1e-9 and -r.fun > best:
            best, bestx = -r.fun, np.sort(r.x)[::-1]
    return float(best), bestx


def new_bound(V, R, alpha=ALPHA):
    eq_q, eq_f = equal_bound(V, R, alpha)
    tl, cfg = two_level_max(V, R, alpha)
    ms, x = multi_start(V, R, alpha=alpha)
    m, a, nb, b = cfg
    c = np.log(alpha)

    def val(a_):
        if m == V:
            return -a_
        rem = (c - m * phi(a_, R)) / (V - m)
        if rem > 0:
            return 1.0
        return -(m * a_ + (V - m) * b_from_rem(rem, R)) / V

    r = minimize_scalar(val, bounds=(max(0, a - 2.5e-4), min(0.5, a + 2.5e-4)), method="bounded",
                        options={"xatol": 1e-14})
    refined = max(-r.fun, tl)
    return {"V": V, "R": R, "equal_F_bound": eq_f, "equal_F_q": eq_q, "true_max": refined,
            "two_level_config": {"m_at_a": m, "a": float(a), "n_at_b": nb, "b": float(b)},
            "multistart_max": ms, "multistart_argmax": [float(v) for v in x] if x is not None else None,
            "max_at_equal": bool(abs(refined - eq_f) < 1e-6), "n_starts": 300}


def population_bound(G, R, alpha=ALPHA):
    """Case-population bound: max E_H[F] s.t. E_H[U(F)]^G >= alpha, H over vignette floors F in [0, .5]."""
    from scipy.optimize import linprog
    grid = np.linspace(0, 0.5, 5001)
    u = U(grid, R)
    r = linprog(-grid, A_ub=[-u], b_ub=[-alpha ** (1.0 / G)], A_eq=[np.ones_like(grid)], b_eq=[1.0],
                bounds=(0, None), method="highs")
    w = r.x
    return float(-r.fun), [(float(grid[i]), float(w[i])) for i in np.nonzero(w > 1e-9)[0]]


def old_bound(V, R, K=1):
    t = ALPHA ** (1.0 / (V * K))
    q = brentq(lambda x: (1 - x) ** R + x ** R - t, 0.0, 0.5 - 1e-13)
    return 2 * q * (1 - q)


def brute(Ks=(2, 3, 4, 5, 6), Rs=(5, 10), n=60000, seed=42):
    rng = np.random.default_rng(seed)
    out = []
    for K in Ks:
        pats = np.array(list(itertools.product([0, 1], repeat=K)))
        for R in Rs:
            worst = -1.0
            for alpha_d in (0.05, 0.2, 1.0, 5.0):
                P = np.vstack([rng.dirichlet(np.full(2 ** K, alpha_d), size=n),
                               rng.dirichlet(np.full(2 ** K, 0.02), size=n)])
                q = P @ pats
                F = (2 * q * (1 - q)).mean(1)
                worst = max(worst, float(((P ** R).sum(1) - U(F, R)).max()))
            adv = -1.0
            for _ in range(60):
                z0 = rng.normal(size=2 ** K) * rng.choice([0.5, 2, 5])

                def obj(z):
                    p = np.exp(z - z.max())
                    p /= p.sum()
                    qq = p @ pats
                    F_ = float((2 * qq * (1 - qq)).mean())
                    return -((p ** R).sum() - float(U(F_, R)))

                r = minimize(obj, z0, method="Nelder-Mead" if K <= 3 else "BFGS", options={"maxiter": 2000})
                adv = max(adv, -r.fun)
            out.append({"K": K, "R": R, "n_random": 8 * n, "max_violation_random": worst,
                        "max_violation_adversarial": adv})
    return out


def counterexample(nsim=2_000_000, seed=42):
    V, R, K, qq = 16, 5, 5, 0.02
    rng = np.random.default_rng(seed)
    f = 2 * qq * (1 - qq)
    old, new = old_bound(V, R, K), new_bound(V, R)["true_max"]
    exact_p = ((1 - qq) ** R + qq ** R) ** V
    s = rng.binomial(R, qq, size=(nsim, V))          # five identical actions: one binomial per vignette
    allun = ((s == 0) | (s == R)).all(1)
    res = {"V": V, "R": R, "K": K, "q": qq, "true_floor": f, "exact_P_all_unanimous": exact_p,
           "mc_P_all_unanimous": float(allun.mean()), "nsim": nsim, "seed": seed,
           "old_bound_if_zero_observed": old, "new_bound_if_zero_observed": new,
           "mc_P_zero_and_truth_above_old_bound": float((allun & (f > old)).mean()),
           "mc_P_zero_and_truth_above_new_bound": float((allun & (f > new)).mean()),
           "nominal_alpha": ALPHA}
    s2 = rng.binomial(R, qq, size=(nsim, V, K))      # independent actions (the old bound's own model)
    al2 = ((s2 == 0) | (s2 == R)).all((1, 2))
    res["independent_actions"] = {"P_all_unanimous_mc": float(al2.mean()),
                                  "mc_P_zero_and_truth_above_old_bound": float((al2 & (f > old)).mean()),
                                  "mc_P_zero_and_truth_above_new_bound": float((al2 & (f > new)).mean())}
    return res


def main():
    cases = [("pooled 5-action, temp 0 (R=5, V=16)", 16, 5, 5), ("pooled 6-action, temp 0 (R=5, V=16)", 16, 5, 6),
             ("single action R=10, V=16 (qwen3 zero cells)", 16, 10, 1), ("single action R=5, V=16 (temp 0)", 16, 5, 1),
             ("single action R=5, V=15 (phi3 t0 / groq t1)", 15, 5, 1)]
    rows = []
    for name, V, R, K in cases:
        nb = new_bound(V, R)
        nb["case"] = name
        nb["K"] = K
        nb["old_bound_independence"] = old_bound(V, R, K)
        nb["population_bound"], nb["population_atoms"] = population_bound(V, R)
        rows.append(nb)
        print("%-48s old %.4f equal %.4f true_max %.4f (multi %.4f) cfg %s pop %.4f" % (
            name, nb["old_bound_independence"], nb["equal_F_bound"], nb["true_max"], nb["multistart_max"],
            nb["two_level_config"], nb["population_bound"]), flush=True)
    br = brute()
    for b in br:
        print("brute K=%d R=%d random %.3e adv %.3e" % (b["K"], b["R"], b["max_violation_random"],
                                                      b["max_violation_adversarial"]), flush=True)
    ce = counterexample()
    print(json.dumps(ce, indent=1))
    grid = np.linspace(0, .5, 2001)
    shape = {}
    for R in (5, 10):
        d2 = np.diff(phi(grid, R), 2)
        shape["R%d_phi_convex_somewhere" % R] = bool((d2 > 1e-12).any())
        shape["R%d_first_convex_f" % R] = float(grid[1:-1][d2 > 1e-12][0]) if (d2 > 1e-12).any() else None
    print(shape)
    json.dump({"meta": {"alpha_one_sided": ALPHA, "seed": 42,
                        "note": "K does not enter the dependence-robust bound; 5- and 6-action pooled bounds coincide."},
               "bounds": rows, "inequality_bruteforce": br, "counterexample": ce, "phi_shape": shape},
              open(OUT, "w"), indent=1, default=float)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
