"""Audit-validation analysis: does the cross-condition audit statistic behave as the decomposition says?

Setup. Condition c0 (reference) and condition c (null re-render, or one demographic contrast) are each
answered R0 and R1 times per vignette v and action k (binary). With true rates p0, p1 and
delta_v = p1 - p0 the exact identity (per vignette and action) is

    d_v = p0(1-p1) + p1(1-p0) = 1/2 [ f0_v + f1_v ] + delta_v^2,    f_i,v = 2 p_i (1-p_i)

where f is the within-condition pairwise disagreement probability (the instability floor) and d the
cross-condition one. Estimators (all unbiased for their targets, per vignette x action cell):

  f_hat_i = n_i (R_i - n_i) / C(R_i, 2)                  (fraction of discordant within-condition pairs;
                                                           = 2 R/(R-1) p_hat (1-p_hat))
  d_hat   = [n0 (R1 - n1) + n1 (R0 - n0)] / (R0 R1)       (fraction of discordant cross-condition pairs
                                                           = p0_hat(1-p1_hat) + p1_hat(1-p0_hat))
  excess  = d_hat - 1/2 (f_hat_0 + f_hat_1)               (unbiased for delta^2)

The plug-in squared shift (p1_hat - p0_hat)^2 is biased upward by p0(1-p0)/R0 + p1(1-p1)/R1; the
bias-corrected version (p1_hat-p0_hat)^2 - p0_hat(1-p0_hat)/(R0-1) - p1_hat(1-p1_hat)/(R1-1) is
algebraically IDENTICAL to excess, so "d vs 1/2(f0+f1) + mean delta^2" is verified as an identity
(identity_gap ~ 1e-16) and the informative quantity is excess itself, whose null expectation is 0
and whose alternative expectation is the mean squared shift. Pooled quantities are ratios of summed
counts over the cells (vignette x action) in scope, i.e. identical to the cell mean when R is
constant and no answer is missing. mean_shift is the mean over vignettes (and, pooled, the five
actions) of p1_hat - p0_hat; its test is an exact two-sided sign-flip permutation test over the
vignette-level shifts (2^V sign patterns, V=16 -> 65,536; p = share of patterns with |T| >= |T_obs|).

Intervals: crossed vignette x replicate bootstrap (Owen 2007 pigeonhole), B=5000, seed 42, same
machinery as crossed_boot.py (cb.mult multiplicities, random.Random(42) draws): one shared vignette
resample per b, independent replicate resamples per arm (arms are separate runs). Within-condition
floors use the off-diagonal weighted U-statistic (pairs of one replicate with itself excluded):
sum_{a<b} m_a m_b [x_a != x_b] = s (n-s) with s=sum m x, n=sum m, over sum_{a<b} m_a m_b =
(n^2 - sum m^2)/2. Cross-condition pairs carry weights m0_a m1_b with no exclusion.

Known-effect injection (default on): on the real null-arm draws, each (vignette, replicate) answer
for action k is set to 1 with probability theta (independently); the true shift in p_v is
theta(1-p_v), p_v estimated by the pooled phat over reference + null arms (plug-in). Opposing
variant: a random half of the vignettes get +theta toward 1, the other half toward 0 (shift
-theta p_v). Per seed the inner CI uses B_inner=500 bootstrap resamples (numpy multinomial
multiplicities, seeded) instead of 5000. Any genuine reference-vs-null drift contaminates the bias
by that drift, which is reported un-injected in the contrasts block. Because every seed injects into
the SAME observed reference and null draws, the data's own sampling offset (p_hat_null - p_hat_ref
before injection) is constant across seeds: it does not average out of "bias_mean_shift" and it is
reported as baseline_mean_shift_uninjected; bias_mean_shift_net_of_baseline removes it. Coverage and
power are therefore conditional on this one realised dataset, not a frequentist average over datasets.

    python audit_validation.py                      # real data: experiments/audit_val_<model>_<arm>
    python audit_validation.py --standin            # stand-in from floor16v3_* (writes *_standin.json)
    python audit_validation.py --no-inject --models llama
"""
from __future__ import annotations

import argparse
import json
import os
import random
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import crossed_boot as cb  # noqa: E402

SEED, B = cb.SEED, cb.B
KEYS, FIVE, I5 = cb.KEYS, cb.FIVE, cb.I5
REF = "ref_white_man_private"
COND = {"reference": REF, "null": "rerender_control", "demographic": "black_woman_medicaid"}
EXP = cb.pc.EXP


# ---------------------------------------------------------------------------- data
def load(dirname: str, cond: str) -> list:
    import glob
    reps = []
    for p in sorted(glob.glob(os.path.join(EXP, dirname, "rep*", "trajectories.json"))):
        d = {t["vignette_id"]: t["actions"] for t in json.load(open(p, encoding="utf-8"))["trajectories"]
             if t["complete"] and t["condition_id"] == cond}
        if d:
            reps.append(d)
    return reps


def tensor(reps, vs):
    """X (R,V,K) with NaN for missing; reuses crossed_boot.Arm's outcome projection."""
    return cb.Arm(reps, vs).X


# ---------------------------------------------------------------------------- estimators
def _sn(X, M):
    val = ~np.isnan(X)
    Xz = np.where(val, X, 0.0)
    vf = val.astype(float)
    s = np.einsum("...r,rvk->...vk", M, Xz)
    n = np.einsum("...r,rvk->...vk", M, vf)
    q = np.einsum("...r,rvk->...vk", M * M, vf)
    return s, n, q


def cell_stats(X0, X1, M0, M1):
    """Per-cell numerators/denominators; arrays (..., V, K). M are replicate multiplicities."""
    s0, n0, q0 = _sn(X0, M0)
    s1, n1, q1 = _sn(X1, M1)
    return dict(f0n=s0 * (n0 - s0), f0d=(n0 * n0 - q0) / 2, f1n=s1 * (n1 - s1), f1d=(n1 * n1 - q1) / 2,
                dn=s0 * (n1 - s1) + s1 * (n0 - s0), dd=n0 * n1, s0=s0, n0=n0, s1=s1, n1=n1)


def _ratio(num, den):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)


def pooled_stats(c, W, kidx):
    """Pooled f0, f1, d, excess, mean shift for vignette weights W (...,V) over action indices kidx."""
    def tot(a):
        return np.einsum("...v,...vk->...", W, a[..., kidx])
    f0, f1, d = _ratio(tot(c["f0n"]), tot(c["f0d"])), _ratio(tot(c["f1n"]), tot(c["f1d"])), _ratio(tot(c["dn"]), tot(c["dd"]))
    p0, p1 = _ratio(c["s0"], c["n0"]), _ratio(c["s1"], c["n1"])
    ok = (~np.isnan(p0) & ~np.isnan(p1))[..., kidx]
    sh = np.nan_to_num(p1 - p0)[..., kidx]
    shift = np.einsum("...v,...vk->...", W, sh * ok) / np.einsum("...v,...vk->...", W, ok.astype(float))
    return dict(f0=f0, f1=f1, d=d, excess=d - 0.5 * (f0 + f1), mean_shift=shift)


def plugin_delta2(c, kidx):
    """Plug-in and bias-corrected mean squared shift over cells (unweighted; observed data)."""
    p0, p1 = _ratio(c["s0"], c["n0"]), _ratio(c["s1"], c["n1"])
    plug = (p1 - p0) ** 2
    corr = _ratio(p0 * (1 - p0), c["n0"] - 1) + _ratio(p1 * (1 - p1), c["n1"] - 1)
    sel = ((c["n0"] >= 2) & (c["n1"] >= 2))[..., kidx]
    pl, co = plug[..., kidx][sel], corr[..., kidx][sel]
    return float(pl.mean()), float(co.mean())


# ---------------------------------------------------------------------------- sign-flip test
_SIGNS = {}


def _signs(V):
    if V not in _SIGNS:
        _SIGNS[V] = (1 - 2 * ((np.arange(2 ** V)[:, None] >> np.arange(V)) & 1)).astype(np.float32)
    return _SIGNS[V]


def signflip_p(delta) -> float:
    """Exact two-sided sign-flip permutation p over vignettes (zeros contribute nothing)."""
    delta = np.asarray(delta, np.float32)
    delta = delta[~np.isnan(delta)]
    T = np.abs(_signs(len(delta)) @ delta)
    return float((T >= abs(float(delta.sum())) - 1e-6).mean())


# ---------------------------------------------------------------------------- one contrast
def analyse(X0, X1, vs, label, rng_py):
    V = len(vs)
    R0, R1 = X0.shape[0], X1.shape[0]
    obs = cell_stats(X0, X1, np.ones(R0), np.ones(R1))
    W = np.zeros((B, V)); M0 = np.zeros((B, R0)); M1 = np.zeros((B, R1))
    for b in range(B):
        W[b] = cb.mult([rng_py.randrange(V) for _ in range(V)], V)
        M0[b] = cb.mult([rng_py.randrange(R0) for _ in range(R0)], R0)
        M1[b] = cb.mult([rng_py.randrange(R1) for _ in range(R1)], R1)
    boot = cell_stats(X0, X1, M0, M1)
    p0, p1 = _ratio(obs["s0"], obs["n0"]), _ratio(obs["s1"], obs["n1"])
    dv = p1 - p0

    def block(kidx, per_vig_shift):
        o = {k: float(v) for k, v in pooled_stats(obs, np.ones(V), kidx).items()}
        bt = pooled_stats(boot, W, kidx)
        pl, co = plugin_delta2(obs, kidx)
        ci = lambda x: cb.pct(x[~np.isnan(x)].tolist())  # noqa: E731
        return {**o, "half_sum_floors": 0.5 * (o["f0"] + o["f1"]),
                "delta2_plugin_biased": pl, "delta2_bias_correction": co, "delta2_corrected": pl - co,
                "identity_gap_excess_minus_corrected": o["excess"] - (pl - co),
                "ci_f0": ci(bt["f0"]), "ci_f1": ci(bt["f1"]), "ci_d": ci(bt["d"]),
                "ci_excess": ci(bt["excess"]), "ci_mean_shift": ci(bt["mean_shift"]),
                "n_boot_dropped": int(np.isnan(bt["excess"]).sum()),
                "sign_flip_p_two_sided": signflip_p(per_vig_shift)}

    out = {"label": label, "n_vignettes": V, "R_ref": R0, "R_cmp": R1, "per_action": {}}
    for k, name in enumerate(KEYS):
        out["per_action"][name] = block([k], dv[:, k])
    out["pooled_5action"] = block(I5, np.nanmean(dv[:, I5], axis=1))
    return out


# ---------------------------------------------------------------------------- injection
def inject(X0, X1, n_seeds, inner_B, thetas=(0.05, 0.10, 0.20, 0.30), seed=SEED):
    """Known-effect injection on the null arm X1, compared with the reference arm X0 (NaN-aware)."""
    rng = np.random.default_rng(seed)
    V, R0, R1 = X0.shape[1], X0.shape[0], X1.shape[0]
    pbar = np.nanmean(np.concatenate([X0, X1], axis=0), axis=0)          # (V,K) pooled phat = plug-in truth
    sv = _signs(V)
    ones0, ones1, onesV = np.ones(R0), np.ones(R1), np.ones(V)
    scopes = [(name, [k]) for k, name in enumerate(KEYS) if name != "cs_caution"] + [("pooled_5action", I5)]
    res = {"settings": [], "pooled_p_hat_by_action": {n: float(np.nanmean(pbar[:, k])) for k, n in enumerate(KEYS)}}
    t_start = time.time()
    for mode in ("same_sign", "opposing"):
        for theta in thetas:
            for scope, kidx in scopes:
                est, t_sh, cov, rej, ex, t_d2, cov_ex = [], [], [], [], [], [], []
                base = pooled_stats(cell_stats(X0, X1, ones0, ones1), onesV, kidx)     # un-injected statistics
                for _ in range(n_seeds):
                    if mode == "same_sign":
                        sgn = np.ones(V)
                    else:
                        sgn = -np.ones(V); sgn[rng.permutation(V)[: V // 2]] = 1.0
                    X = X1.copy()
                    for k in kidx:
                        mask = rng.random((R1, V)) < theta
                        col = X[:, :, k]
                        col = np.where(mask & (sgn > 0)[None, :], 1.0, np.where(mask & (sgn < 0)[None, :], 0.0, col))
                        X[:, :, k] = np.where(np.isnan(X1[:, :, k]), np.nan, col)
                    dtrue = np.where(sgn[:, None] > 0, theta * (1 - pbar), -theta * pbar)[:, kidx]
                    obs = cell_stats(X0, X, ones0, ones1)
                    o = pooled_stats(obs, onesV, kidx)
                    p0, p1 = _ratio(obs["s0"], obs["n0"]), _ratio(obs["s1"], obs["n1"])
                    pv = np.asarray(np.nanmean((p1 - p0)[:, kidx], axis=1), np.float32)
                    rej.append(float((np.abs(sv @ pv) >= abs(float(pv.sum())) - 1e-6).mean()) < 0.05)
                    W = rng.multinomial(V, np.ones(V) / V, size=inner_B).astype(float)
                    M0 = rng.multinomial(R0, np.ones(R0) / R0, size=inner_B).astype(float)
                    M1 = rng.multinomial(R1, np.ones(R1) / R1, size=inner_B).astype(float)
                    bt = pooled_stats(cell_stats(X0, X, M0, M1), W, kidx)
                    lo, hi = cb.pct(bt["mean_shift"][~np.isnan(bt["mean_shift"])].tolist())
                    lo2, hi2 = cb.pct(bt["excess"][~np.isnan(bt["excess"])].tolist())
                    ts, td = float(dtrue.mean()), float((dtrue ** 2).mean())
                    cov.append(lo <= ts <= hi); cov_ex.append(lo2 <= td <= hi2)
                    est.append(float(o["mean_shift"])); t_sh.append(ts); ex.append(float(o["excess"])); t_d2.append(td)
                est, t_sh, ex, t_d2 = map(np.array, (est, t_sh, ex, t_d2))
                row = {"mode": mode, "theta": theta, "scope": scope, "n_seeds": n_seeds, "inner_B": inner_B,
                       "true_mean_shift": float(t_sh.mean()), "est_mean_shift": float(est.mean()),
                       "bias_mean_shift": float((est - t_sh).mean()),
                       "baseline_mean_shift_uninjected": float(base["mean_shift"]),
                       "bias_mean_shift_net_of_baseline": float((est - t_sh).mean() - base["mean_shift"]),
                       "baseline_excess_uninjected": float(base["excess"]),
                       "mc_se_bias_shift": float((est - t_sh).std(ddof=1) / np.sqrt(n_seeds)),
                       "coverage_mean_shift_ci": float(np.mean(cov)), "power_sign_test_0.05": float(np.mean(rej)),
                       "true_mean_delta2": float(t_d2.mean()), "est_excess": float(ex.mean()),
                       "bias_excess_vs_delta2": float((ex - t_d2).mean()),
                       "mc_se_bias_excess": float((ex - t_d2).std(ddof=1) / np.sqrt(n_seeds)),
                       "coverage_excess_ci": float(np.mean(cov_ex))}
                res["settings"].append(row)
                print("  inject %-9s theta=%.2f %-15s bias_shift=%+.4f cov=%.3f power=%.3f bias_excess=%+.5f cov_ex=%.3f (%.0fs)" % (
                    mode, theta, scope, row["bias_mean_shift"], row["coverage_mean_shift_ci"], row["power_sign_test_0.05"],
                    row["bias_excess_vs_delta2"], row["coverage_excess_ci"], time.time() - t_start), flush=True)
    return res


# ---------------------------------------------------------------------------- driver
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--standin", action="store_true", help="use floor16v3_* as stand-in data (see docstring)")
    ap.add_argument("--models", default="llama,qwen3")
    ap.add_argument("--no-inject", action="store_true")
    ap.add_argument("--n-seeds", type=int, default=1000)
    ap.add_argument("--inner-B", type=int, default=500)
    ap.add_argument("--out", default=None)
    ap.add_argument("--min-reps", type=int, default=2)
    a = ap.parse_args()
    out_path = a.out or os.path.join(EXP, "audit_validation%s.json" % ("_standin" if a.standin else ""))
    result = {"meta": {"seed": SEED, "B": B, "inner_B": a.inner_B, "n_seeds": a.n_seeds, "actions_pooled": FIVE,
                       "standin": a.standin, "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                       "bootstrap": "crossed vignette x replicate; shared vignette draws, independent replicate draws per arm",
                       "note": "pooled = ratio of summed counts over (vignette x action) cells; sign-flip test exact over vignettes"},
              "models": {}}
    for m in a.models.split(","):
        if a.standin:
            base = {"llama": "floor16v3_llama", "qwen3": "floor16v3_qwen3"}[m]
            other = {"llama": "floor16v3_qwen3", "qwen3": "floor16v3_llama"}[m]
            allr = load(base, REF)
            arms = {"reference": allr[0::2], "null": allr[1::2], "demographic": load(other, REF)[1::2]}
            src = {"reference": base + " odd reps", "null": base + " even reps",
                   "demographic": other + " even reps (different model: stand-in for a large genuine shift)"}
        else:
            arms = {k: load("audit_val_%s_%s" % (m, k), COND[k]) for k in COND}
            src = {k: "audit_val_%s_%s" % (m, k) for k in COND}
        info = {"sources": src, "R": {k: len(v) for k, v in arms.items()}, "contrasts": {}}
        result["models"][m] = info
        if min(len(arms["reference"]), len(arms["null"])) < a.min_reps:
            info["status"] = "insufficient replicates (need >= %d in reference and null)" % a.min_reps
            print(m, info["status"], info["R"]); continue
        rng_py = random.Random(SEED)
        for arm in ("null", "demographic"):
            if len(arms[arm]) < a.min_reps:
                info["contrasts"][arm] = {"status": "insufficient replicates"}; continue
            vs = sorted(cb.complete_vs(arms["reference"]) & cb.complete_vs(arms[arm]))
            info["contrasts"][arm] = analyse(tensor(arms["reference"], vs), tensor(arms[arm], vs), vs, "%s vs reference" % arm, rng_py)
            p = info["contrasts"][arm]["pooled_5action"]
            print("%s %-11s R=%d/%d V=%d f0=%.4f f1=%.4f d=%.4f excess=%+.4f [%+.4f,%+.4f] shift=%+.4f [%+.4f,%+.4f] sign p=%.4f gap=%.1e" % (
                m, arm, len(arms["reference"]), len(arms[arm]), len(vs), p["f0"], p["f1"], p["d"], p["excess"], *p["ci_excess"],
                p["mean_shift"], *p["ci_mean_shift"], p["sign_flip_p_two_sided"], p["identity_gap_excess_minus_corrected"]), flush=True)
        if not a.no_inject:
            vs = sorted(cb.complete_vs(arms["reference"]) & cb.complete_vs(arms["null"]))
            info["injection"] = inject(tensor(arms["reference"], vs), tensor(arms["null"], vs), a.n_seeds, a.inner_B)
    json.dump(result, open(out_path, "w", encoding="utf-8"), indent=1, default=float)
    print("wrote", out_path)


if __name__ == "__main__":
    main()
