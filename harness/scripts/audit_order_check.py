"""Order and elapsed-time checks for the counterbalanced end-to-end run (experiments/audit_cb_*).

Within each replicate the three conditions ran back to back in an order fixed in advance by
experiments/audit_cb_schedule.json (each condition four times in each position over twelve
replicates); every dispatched step is time-stamped in experiments/audit_cb_order_log.jsonl.

For one model, X[c, r, v, k] is the answer (0/1, missing as NaN) of condition c in replicate r for
vignette v and defined action k (the five pooled actions). Residuals remove the condition x
vignette x action mean over replicates, so they carry only replicate-level variation:
    e[c, r, v, k] = X[c, r, v, k] - mean_r X[c, r, v, k].
Two statistics, each summed over the five actions:
    position: T_pos = sum_k sum_p n_pk * mbar_pk^2, mbar_pk the mean residual at within-replicate
              position p (1, 2, 3) and n_pk its number of answers;
    time:     T_time = sum_k b_k^2 * S_k, b_k the least-squares slope of the replicate-mean
              residual on the condition-replicate's start time (hours since the model's first
              call) and S_k the corresponding sum of squares of centred time.
Null distribution: under no position or time effect the twelve replicates of a condition are
exchangeable, so the twelve (position, start time) labels are permuted among them within each
condition (B=5000 permutations, seed 42, the identity included in the p-value count). The test is
a check for gross order or drift effects in this run, not a power-calibrated test.

    python audit_order_check.py            # writes experiments/audit_order_check.json
"""
from __future__ import annotations

import json
import os
import random
import sys
from datetime import datetime

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import audit_validation as av  # noqa: E402
import crossed_boot as cb  # noqa: E402

EXP = av.EXP
ARMS = ("reference", "null", "demographic")
MODELS = {"llama": "llama3.1:8b-instruct-q4_K_M", "qwen3": "qwen3:4b-instruct-2507-q8_0"}
B, SEED = 5000, 42


def _t(s: str) -> float:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").timestamp() / 3600.0


def stats(E, pos, tim):
    """E (C,R,V,K) residuals; pos, tim (C,R) labels. Returns (T_pos, T_time)."""
    val = ~np.isnan(E)
    Ez = np.where(val, E, 0.0)
    tp = 0.0
    for p in (0, 1, 2):
        m = (pos == p)[:, :, None, None] & val
        n = m.sum(axis=(0, 1, 2))
        s = np.where(m, Ez, 0.0).sum(axis=(0, 1, 2))
        tp += float(np.sum(np.where(n > 0, s * s / np.maximum(n, 1), 0.0)))
    # replicate-mean residual per (c, r, k)
    n_cr = val.sum(axis=2)
    y = np.where(n_cr > 0, Ez.sum(axis=2) / np.maximum(n_cr, 1), 0.0)  # (C,R,K)
    t = tim.ravel()
    tc = t - t.mean()
    sxx = float(tc @ tc)
    yk = y.reshape(-1, y.shape[2])
    b = (tc @ (yk - yk.mean(axis=0))) / sxx
    return tp, float(np.sum(b * b) * sxx)


def main() -> int:
    sched = json.load(open(os.path.join(EXP, "audit_cb_schedule.json"), encoding="utf-8"))["orders"]
    log = [json.loads(l) for l in open(os.path.join(EXP, "audit_cb_order_log.jsonl"), encoding="utf-8") if l.strip()]
    out = {"meta": {"B": B, "seed": SEED, "actions_pooled": av.FIVE,
                    "permutation": "position and start-time labels permuted among the replicates of each condition"},
           "models": {}}
    for m, tag in MODELS.items():
        arms = {a: av.load("audit_cb_%s_%s" % (m, a), av.COND[a]) for a in ARMS}
        R = len(arms["reference"])
        assert all(len(v) == R for v in arms.values()), {a: len(v) for a, v in arms.items()}
        vs = sorted(set.intersection(*[cb.complete_vs(v) for v in arms.values()]))
        X = np.stack([av.tensor(arms[a], vs)[:, :, av.I5] for a in ARMS])  # (C,R,V,5)
        E = X - np.nanmean(X, axis=1, keepdims=True)
        pos = np.array([[sched[str(r + 1)].index(a) for r in range(R)] for a in ARMS])
        start = {}
        for rec in log:
            if rec["model"] == tag:
                key = (rec["condition"], rec["rep"])
                start[key] = min(start.get(key, 9e18), _t(rec["t_start"]))
        tim = np.array([[start[(av.COND[a], r + 1)] for r in range(R)] for a in ARMS])
        span = [min(rec["t_start"] for rec in log if rec["model"] == tag),
                max(rec["t_end"] for rec in log if rec["model"] == tag)]
        tim = tim - tim.min()
        obs = stats(E, pos, tim)
        rng = random.Random(SEED)
        ge = [1, 1]
        for _ in range(B - 1):
            pp, tt = pos.copy(), tim.copy()
            for c in range(len(ARMS)):
                idx = list(range(R))
                rng.shuffle(idx)
                pp[c], tt[c] = pos[c, idx], tim[c, idx]
            s = stats(E, pp, tt)
            ge[0] += s[0] >= obs[0] - 1e-12
            ge[1] += s[1] >= obs[1] - 1e-12
        # descriptive: pooled action rate by position, per condition
        rate = {a: [float(np.nanmean(X[c][pos[c] == p])) for p in (0, 1, 2)] for c, a in enumerate(ARMS)}
        out["models"][m] = {"model": tag, "R": R, "V": len(vs), "utc_span": span,
                            "hours": round(float(tim.max()), 3),
                            "T_position": obs[0], "p_position": ge[0] / B,
                            "T_time": obs[1], "p_time": ge[1] / B,
                            "pooled_rate_by_position": rate}
        print("%s R=%d V=%d span %s..%s  position p=%.4f  time p=%.4f" % (m, R, len(vs), span[0], span[1], ge[0] / B, ge[1] / B), flush=True)
    json.dump(out, open(os.path.join(EXP, "audit_order_check.json"), "w", encoding="utf-8"), indent=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
