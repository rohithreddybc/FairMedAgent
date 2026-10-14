"""Known-truth simulation of the audit statistics (replaces injection into observed draws).

Why. Injecting shifts into the observed null-arm draws leaves the target ill defined: the true
probabilities of the observed arms are unknown, so "truth" had to be a plug-in, the dataset's own
reference-null offset enters through cross terms, and achieved effects differ between models. Here
every dataset is drawn from known Bernoulli probabilities, so the true mean signed shift and the
true mean squared shift are known exactly.

Design. V=16 vignettes, the five defined actions, R=12 independent draws per arm (as in the
counterbalanced end-to-end check). Arm 0 (reference) has probability p[v,k]; arm 1 (compared) has
p[v,k] + delta[v,k]. Statistics are those of audit_validation.py: mean signed shift (mean over
cells of p1_hat - p0_hat), excess d - (f0 + f1)/2 (unbiased for the mean of delta^2 under independent
draws), the exact two-sided sign-flip test over the 16 vignette-level shifts, and crossed
vignette x replicate percentile intervals (inner B bootstrap resamples).

Calibrations (p). "llama" and "qwen3": p[v,k] = the observed reference-arm rate of that model in the
counterbalanced end-to-end run (experiments/audit_cb_<model>_reference, R=12). "homog_<f>": every cell
has the same p, chosen so that the expected pairwise floor 2p(1-p) equals f (0.02, 0.10, 0.22), which
varies the floor with nothing else varying.

Scenarios.
  fixed-case (vignettes fixed, only draws random; estimand = mean over these 16 vignettes):
    null      delta = 0.
    same      delta = +d in every cell; p is first capped at 1-d, so the achieved shift is exactly d
              for every calibration and model.
    opposing  delta = +d for vignettes 0,2,...,14 and -d for 1,3,...,15; p is first clipped into
              [d, 1-d], so the true mean signed shift is exactly 0 and the true mean delta^2 is d^2.
    sparse_k_a  delta = +a on admission only, in k of the 16 vignettes (k in 1, 2, 4; a in 0.25, 0.5),
              p capped at 1-a in those cells: the sparse departures seen in the observed data.
  population (vignettes drawn with replacement from the 16 calibrated rows in every dataset;
              estimand = mean over that generating distribution):
    pop_null  delta = 0.
    pop_het   delta = 2d on a random half of the drawn vignettes' cells (vignette-level coin), 0 on
              the rest; p capped at 1-2d. Population mean shift d, mean delta^2 2d^2.
The population rows draw vignettes from the same 16 rows the bootstrap resamples, so they are a
self-consistency check of the crossed interval, not a test against an independent generating model.
For each scenario: bias and relative bias of both estimators; rejection rate at 0.05 of the vignette-level
sign-flip test and of a replicate-paired sign-flip test (replicate r of each arm paired; 2^12 patterns);
the fraction of datasets in which the vignette-level test cannot reach 0.05 (fewer than 6 non-zero
vignette shifts); the rate at which the crossed interval of the excess lies above zero; and coverage of the
crossed 95% intervals for the true mean shift and true mean delta^2.

    python audit_sim.py [--nsim 2000] [--inner-B 1000]     # writes experiments/audit_sim.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_validation as av  # noqa: E402
import crossed_boot as cb  # noqa: E402

V, R, K = 16, 12, 5
DS = (0.025, 0.05, 0.10, 0.20)
HOMOG_FLOORS = (0.02, 0.10, 0.22)
SEED = 42
SPARSE_K = (1, 2, 4)
SPARSE_A = (0.25, 0.5)
SR = (1 - 2 * ((np.arange(2 ** R)[:, None] >> np.arange(R)) & 1)).astype(np.float32)   # replicate sign patterns


def calib(model: str) -> np.ndarray:
    reps = av.load("audit_cb_%s_reference" % model, av.REF)
    vs = sorted(cb.complete_vs(reps))
    X = av.tensor(reps, vs)[:, :, av.I5]
    assert X.shape == (R, V, K), X.shape
    return np.nanmean(X, axis=0)


def homog(f: float) -> np.ndarray:
    p = (1 - np.sqrt(1 - 2 * f)) / 2
    return np.full((V, K), p)


def scen(kind: str, p: np.ndarray, d: float, rng) -> tuple:
    """Return (p0, p1, true_shift, true_delta2) for one dataset."""
    if kind == "null":
        return p, p, 0.0, 0.0
    if kind == "same":
        q = np.minimum(p, 1 - d)
        return q, q + d, d, d * d
    if kind == "opposing":
        q = np.clip(p, d, 1 - d)
        s = np.where(np.arange(V) % 2 == 0, 1.0, -1.0)[:, None]
        return q, q + s * d, 0.0, d * d
    if kind == "pop_null":
        q = p[rng.integers(0, V, V)]
        return q, q, 0.0, 0.0
    if kind.startswith("sparse"):
        # effect +a on admission only, in the first k vignettes (k, a encoded as sparse_<k>_<a>)
        _, k, a = kind.split("_")
        k, a = int(k), float(a)
        q = p.copy()
        q[:k, 0] = np.minimum(q[:k, 0], 1 - a)
        dl = np.zeros_like(q)
        dl[:k, 0] = a
        return q, q + dl, float(dl.mean()), float((dl ** 2).mean())
    if kind == "pop_het":
        q = np.minimum(p[rng.integers(0, V, V)], 1 - 2 * d)
        on = (rng.random(V) < 0.5).astype(float)[:, None]
        return q, q + 2 * d * on, d, 2 * d * d
    raise ValueError(kind)


def one(p0, p1, rng, inner_B, sv):
    X0 = (rng.random((R, V, K)) < p0).astype(float)
    X1 = (rng.random((R, V, K)) < p1).astype(float)
    ones, onesV = np.ones(R), np.ones(V)
    kidx = list(range(K))
    obs = av.cell_stats(X0, X1, ones, ones)
    o = av.pooled_stats(obs, onesV, kidx)
    pv = (X1.mean(axis=0) - X0.mean(axis=0)).mean(axis=1).astype(np.float32)
    p_sf = float((np.abs(sv @ pv) >= abs(float(pv.sum())) - 1e-6).mean())
    nz = int(np.sum(np.abs(pv) > 1e-9))
    dr = (X1 - X0).reshape(R, -1).mean(axis=1).astype(np.float32)
    p_rep = float((np.abs(SR @ dr) >= abs(float(dr.sum())) - 1e-6).mean())
    W = rng.multinomial(V, np.ones(V) / V, size=inner_B).astype(float)
    M0 = rng.multinomial(R, np.ones(R) / R, size=inner_B).astype(float)
    M1 = rng.multinomial(R, np.ones(R) / R, size=inner_B).astype(float)
    bt = av.pooled_stats(av.cell_stats(X0, X1, M0, M1), W, kidx)
    ci_s = cb.pct(bt["mean_shift"][~np.isnan(bt["mean_shift"])].tolist())
    ci_e = cb.pct(bt["excess"][~np.isnan(bt["excess"])].tolist())
    return float(o["mean_shift"]), float(o["excess"]), p_sf, ci_s, ci_e, p_rep, (2.0 / 2 ** nz if nz else 1.0) > 0.05


def run(name, p, kind, d, nsim, inner_B, rng, sv):
    sh, ex, rej, cs, ce, ts, td, fl, rr, de, dg = [], [], [], [], [], [], [], [], [], [], []
    for _ in range(nsim):
        p0, p1, t_s, t_d = scen(kind, p, d, rng)
        s, e, psf, ci_s, ci_e, prep, degen = one(p0, p1, rng, inner_B, sv)
        sh.append(s); ex.append(e); rej.append(psf < 0.05); rr.append(prep < 0.05); de.append(ci_e[0] > 0); dg.append(degen)
        cs.append(ci_s[0] <= t_s <= ci_s[1]); ce.append(ci_e[0] <= t_d <= ci_e[1])
        ts.append(t_s); td.append(t_d)
        fl.append(float(np.mean(p0 * (1 - p0) + p1 * (1 - p1))))   # expected floor, mean of the two arms
    sh, ex, ts, td = map(np.array, (sh, ex, ts, td))
    t_s, t_d = float(ts.mean()), float(td.mean())
    row = {"calibration": name, "scenario": kind, "d": d, "nsim": nsim, "inner_B": inner_B,
           "expected_floor": float(np.mean(fl)), "true_mean_shift": t_s, "true_mean_delta2": t_d,
           "bias_shift": float((sh - ts).mean()), "mcse_bias_shift": float((sh - ts).std(ddof=1) / np.sqrt(nsim)),
           "bias_excess": float((ex - td).mean()), "mcse_bias_excess": float((ex - td).std(ddof=1) / np.sqrt(nsim)),
           "rel_bias_excess": float((ex - td).mean() / t_d) if t_d > 0 else None,
           "sd_excess": float(ex.std(ddof=1)), "sd_shift": float(sh.std(ddof=1)),
           "reject_signflip_0.05": float(np.mean(rej)), "reject_rep_signflip_0.05": float(np.mean(rr)),
           "excess_ci_excludes_zero": float(np.mean(de)), "signflip_cannot_reject": float(np.mean(dg)),
           "coverage_shift": float(np.mean(cs)), "coverage_delta2": float(np.mean(ce))}
    rb = row["rel_bias_excess"]
    print("%-10s %-14s d=%.3f floor=%.3f  bias_sh=%+.4f(%.4f) bias_ex=%+.5f(%.5f)%s  rej=%.3f rep=%.3f det_ex=%.3f degen=%.3f cov_sh=%.3f cov_d2=%.3f" % (
        name, kind, d, row["expected_floor"], row["bias_shift"], row["mcse_bias_shift"], row["bias_excess"],
        row["mcse_bias_excess"], "" if rb is None else " rel=%+.3f" % rb, row["reject_signflip_0.05"],
        row["reject_rep_signflip_0.05"], row["excess_ci_excludes_zero"], row["signflip_cannot_reject"],
        row["coverage_shift"], row["coverage_delta2"]), flush=True)
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--nsim", type=int, default=2000)
    ap.add_argument("--inner-B", type=int, default=1000)
    a = ap.parse_args()
    rng = np.random.default_rng(SEED)
    sv = av._signs(V)
    cal = {"llama": calib("llama"), "qwen3": calib("qwen3")}
    cal.update({"homog_%.2f" % f: homog(f) for f in HOMOG_FLOORS})
    rows, t0 = [], time.time()
    for name, p in cal.items():
        rows.append(run(name, p, "null", 0.0, a.nsim, a.inner_B, rng, sv))
        for kind in ("same", "opposing"):
            for d in DS:
                rows.append(run(name, p, kind, d, a.nsim, a.inner_B, rng, sv))
        for k in SPARSE_K:
            for amp in SPARSE_A:
                rows.append(run(name, p, "sparse_%d_%g" % (k, amp), amp, a.nsim, a.inner_B, rng, sv))
        if not name.startswith("homog"):
            rows.append(run(name, p, "pop_null", 0.0, a.nsim, a.inner_B, rng, sv))
            for d in DS:
                rows.append(run(name, p, "pop_het", d, a.nsim, a.inner_B, rng, sv))
    out = {"meta": {"V": V, "R": R, "K": K, "seed": SEED, "nsim": a.nsim, "inner_B": a.inner_B, "ds": DS,
                    "sparse_k": SPARSE_K, "sparse_a": SPARSE_A,
                    "homog_floors": HOMOG_FLOORS, "minutes": round((time.time() - t0) / 60, 1),
                    "calibration_mean_p": {k: float(v.mean()) for k, v in cal.items()},
                    "calibration_floor": {k: float(np.mean(2 * v * (1 - v))) for k, v in cal.items()}},
           "rows": rows}
    json.dump(out, open(os.path.join(av.EXP, "audit_sim.json"), "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
