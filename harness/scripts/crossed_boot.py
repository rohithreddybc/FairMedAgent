"""Two-way (crossed) vignette x replicate bootstrap for the instability floor.

Why this exists. Endpoints A (haiku-4.5, R=10) and B (sonnet-5, R=6) answered each step's 16
vignettes inside ONE shared sub-agent context per replicate (experiments/floor16*/rep*/ans*/
ref.json holds 16 answers per call). A replicate is therefore a cluster too: anything the
shared context does to one answer it may do to the other fifteen. The vignette-cluster
bootstrap in robustness.py / panel_summary.py / five_action_extras.py resamples vignettes only
and holds the replicate set fixed, so it ignores that replicate-level dependence. Here the
data are treated as a crossed design (vignettes x replicates, both random), and both factors
are resampled independently with replacement: the pigeonhole bootstrap of Owen (2007, Ann.
Appl. Stat. 1:519-537) for crossed random effects.

The estimator is unchanged. For one model, with replicate answers X[r, v, k] (0/1, or missing),
    floor = sum over replicate pairs a<b, vignettes v, actions k of [X[a,v,k] != X[b,v,k]]
            / number of such comparisons with both answers present,
pooled over C(R,2) pairs (= ps.counts, then summed over actions).

Duplicated replicates. A replicate resample r*_1..r*_R drawn with replacement contains repeats.
Comparing two copies of the same replicate always gives agreement, so counting those pairs
would bias every resampled floor toward zero (a pure artifact: no such comparison exists in the
data). We therefore keep only pairs of draws whose UNDERLYING replicates differ. Concretely the
resampled floor is the multiplicity-weighted U-statistic
    sum_{a<b} m_a m_b * sum_v w_v * D[a,b,v,k]  /  sum_{a<b} m_a m_b * sum_v w_v * N[a,b,v,k],
with m_a the number of times original replicate a was drawn and w_v the number of times
vignette v was drawn. Because the sum runs over distinct ORIGINAL indices a<b, same-replicate
pairs are excluded automatically, and each surviving pair of distinct originals enters exactly
as often as it appears among the draw-position pairs. This is the off-diagonal (U-statistic)
bootstrap rather than the V-statistic one (Arcones & Gine 1992); it keeps the kernel h(a,a)=0
out of the estimand, which is the point. A resample in which every draw is the same replicate
has no admissible pair and is dropped (probability R^(1-R); reported as n_dropped).

Majority vote. For depth k the observed procedure enumerates every unordered pair of disjoint
k-subsets of the replicate POSITIONS. Under resampling we enumerate the same position splits of
the drawn multiset and keep only splits in which no underlying replicate appears on both sides
(the generalisation of the self-pair rule: a replicate on both sides manufactures agreement
between the two votes). Within one side a repeated replicate votes as often as it was drawn,
as resampling intends. Resamples with no admissible split are dropped and counted. At k=1 this
reduces exactly to the pair rule above.

Draw order (seed 42). One random.Random(42) stream. First the B=5000 vignette resamples are
drawn exactly as robustness.build_resamples draws them, so the vignette multisets are
IDENTICAL to those behind the published vignette-only intervals; the only thing that differs
is the replicate resampling layered on top. Then, per resample b, one replicate draw per model
in sorted label order (A..F). Pairwise model differences therefore share the vignette resample
(paired over vignettes) and use independent replicate resamples per model, matching the design
(each model's replicates are separate runs). The temperature and Groq comparisons and the
diagnostics use their own seeded streams (documented at each).

Run:  FMA_PANEL=v3 python crossed_boot.py
 or   FMA_PANEL=v3 FMA_BOOT=crossed python robustness.py      (dispatches here)
Writes experiments/robustness_v3_crossed.json; refuses to overwrite any other file.
"""
from __future__ import annotations

import itertools
import json
import os
import random
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import robustness as rb  # noqa: E402
import aggregation_curve as ac  # noqa: E402

ps, pc = rb.ps, rb.pc
SEED = 42
B = 5000
KEYS = list(rb.KEYS)                       # six actions, sorted
FIVE = [k for k in KEYS if k != "cs_caution"]
I5 = [KEYS.index(k) for k in FIVE]
OUT = os.environ.get("FMA_CROSSED_OUT") or os.path.join(pc.EXP, "robustness%s_crossed.json" % pc.SUFFIX)
N_PERM = 2000


def pct(vals):
    v = sorted(vals)
    n = len(v)
    return [v[int(0.025 * n)], v[min(n - 1, int(0.975 * n))]] if n else None


# ---------------------------------------------------------------------------------------
# Data tensors
# ---------------------------------------------------------------------------------------

class Arm:
    """One model/arm: answers X[r, v, k] in {0, 1, nan} and the pair tensors over a<b."""

    def __init__(self, reps, vignettes, keys=KEYS):
        self.R, self.V, self.K = len(reps), len(vignettes), len(keys)
        X = np.full((self.R, self.V, self.K), np.nan)
        for r, rep in enumerate(reps):
            for j, v in enumerate(vignettes):
                if v not in rep:
                    continue
                for k, name in enumerate(keys):
                    x = rb.OUTCOMES[name](rep[v])
                    if x is not None:
                        X[r, j, k] = float(bool(x))
        self.X = X
        self.vignettes = list(vignettes)
        ia, ib = np.triu_indices(self.R, 1)
        self.ia, self.ib = ia, ib
        xa, xb = X[ia], X[ib]
        valid = ~np.isnan(xa) & ~np.isnan(xb)
        self.N = valid.astype(float)                       # (P, V, K)
        self.D = (valid & (xa != xb)).astype(float)

    def counts(self, m, w):
        """num[k], den[k] for replicate multiplicities m (len R) and vignette weights w (len V)."""
        M = m[self.ia] * m[self.ib]
        num = np.einsum("p,v,pvk->k", M, w, self.D)
        den = np.einsum("p,v,pvk->k", M, w, self.N)
        return num, den


def mult(draw, n):
    return np.bincount(np.asarray(draw, dtype=int), minlength=n).astype(float)


def vweights(samp, canon):
    pos = {v: i for i, v in enumerate(canon)}
    return mult([pos[v] for v in samp], len(canon))


# ---------------------------------------------------------------------------------------
# Majority vote under replicate resampling
# ---------------------------------------------------------------------------------------

class Splits:
    def __init__(self, R, k):
        sp = list(ac._disjoint_splits(R, k))
        self.GA = np.array([a for a, _ in sp])
        self.GB = np.array([b for _, b in sp])
        self.R = R


def vote_counts(arm, draw, w, splits, kidx):
    """Flip and total counts of disjoint-group majority votes, with admissible splits only."""
    rr = np.asarray(draw)
    onehot = np.eye(arm.R)[rr]                         # (pos, R)
    OA = onehot[splits.GA].sum(1)                      # (S, R)
    OB = onehot[splits.GB].sum(1)
    ok = ((OA > 0) & (OB > 0)).sum(1) == 0
    if not ok.any():
        return None
    Xr = arm.X[rr][:, :, kidx]                         # (pos, V, K')
    XA, XB = Xr[splits.GA[ok]], Xr[splits.GB[ok]]      # (S', k, V, K')
    tA, fA = (XA == 1).sum(1), (XA == 0).sum(1)
    tB, fB = (XB == 1).sum(1), (XB == 0).sum(1)
    vA, vB = tA != fA, tB != fB
    both = vA & vB
    flip = both & ((tA > fA) != (tB > fB))
    return float(np.einsum("svk,v->", flip.astype(float), w)), float(np.einsum("svk,v->", both.astype(float), w))


# ---------------------------------------------------------------------------------------
# Main bootstrap: per-model counts per resample, crossed and (same vignette draws) vignette-only
# ---------------------------------------------------------------------------------------

def run_panel(models, canon):
    labs = sorted(models)
    arms = {lab: Arm(models[lab]["reps"], canon) for lab in labs}
    rng = random.Random(SEED)
    vres = rb.build_resamples(rng, canon, B)            # identical to robustness.py item 1
    rdraws = {lab: [] for lab in labs}
    for _ in range(B):
        for lab in labs:
            R = arms[lab].R
            rdraws[lab].append([rng.randrange(R) for _ in range(R)])

    cr = {lab: {"num": np.zeros((B, 6)), "den": np.zeros((B, 6))} for lab in labs}
    vo = {lab: {"num": np.zeros((B, 6)), "den": np.zeros((B, 6))} for lab in labs}
    W = [vweights(s, canon) for s in vres]
    for lab in labs:
        a = arms[lab]
        ones = np.ones(a.R)
        for b in range(B):
            n, d = a.counts(mult(rdraws[lab][b], a.R), W[b])
            cr[lab]["num"][b], cr[lab]["den"][b] = n, d
            n, d = a.counts(ones, W[b])
            vo[lab]["num"][b], vo[lab]["den"][b] = n, d
    obs = {}
    for lab in labs:
        n, d = arms[lab].counts(np.ones(arms[lab].R), np.ones(len(canon)))
        obs[lab] = {"num": n, "den": d}
    return arms, vres, W, rdraws, cr, vo, obs


def pooled(c, idx):
    num = c["num"][..., idx].sum(-1)
    den = c["den"][..., idx].sum(-1)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)


def action(c, k):
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(c["den"][..., k] > 0, c["num"][..., k] / np.where(c["den"][..., k] > 0, c["den"][..., k], 1), np.nan)


def ci(arr):
    a = arr[~np.isnan(arr)]
    return pct(a.tolist())


def summarize(boot, obs, labs, tag):
    """Every interval family the manuscript reports, from one per-resample count cache."""
    out = {"models": {}, "pairs_5action": [], "pairs_6action": []}
    p5 = {l: pooled(boot[l], I5) for l in labs}
    p6 = {l: pooled(boot[l], list(range(6))) for l in labs}
    o5 = {l: float(pooled(obs[l], I5)) for l in labs}
    o6 = {l: float(pooled(obs[l], list(range(6)))) for l in labs}
    for l in labs:
        e = {"floor_5action": o5[l], "ci_5action": ci(p5[l]), "n_dropped_5": int(np.isnan(p5[l]).sum()),
             "floor_6action": o6[l], "ci_6action": ci(p6[l]), "actions": {}}
        for k, name in enumerate(KEYS):
            e["actions"][name] = {"floor": float(obs[l]["num"][k] / obs[l]["den"][k]),
                                  "ci": ci(action(boot[l], k))}
        out["models"][l] = e
    for tagk, P, O in (("pairs_5action", p5, o5), ("pairs_6action", p6, o6)):
        for li, lj in itertools.combinations(labs, 2):
            d = P[li] - P[lj]
            lo, hi = ci(d)
            out[tagk].append({"pair": "%s-%s" % (li, lj), "observed_diff": O[li] - O[lj],
                              "ci": [lo, hi], "separated": not (lo <= 0 <= hi)})
    out["n_separated_5action"] = sum(p["separated"] for p in out["pairs_5action"])
    out["n_separated_6action"] = sum(p["separated"] for p in out["pairs_6action"])

    for tagk, P, O in (("range_factor_5action", p5, o5), ("range_factor_6action", p6, o6)):
        M = np.vstack([P[l] for l in labs])               # (models, B)
        good = ~np.isnan(M).any(0) & (M.min(0) > 0)
        ratios = (M.max(0)[good] / M.min(0)[good]).tolist()
        out[tagk] = {"observed": max(O.values()) / min(O.values()), "ci": pct(ratios),
                     "n_undefined_resamples": int((~good).sum())}

    # Model A: per-action ratio (five actions), admission - ICU, caution - ICU (six-action sensitivity).
    A = boot["A"]
    F = np.vstack([action(A, KEYS.index(k)) for k in FIVE])   # (5, B)
    good = ~np.isnan(F).any(0) & (F.min(0) > 0)
    oF = [float(obs["A"]["num"][KEYS.index(k)] / obs["A"]["den"][KEYS.index(k)]) for k in FIVE]
    out["A_per_action_ratio_5action"] = {"observed": max(oF) / min(oF), "finite_subset_ci": pct((F.max(0)[good] / F.min(0)[good]).tolist()),
                                         "n_undefined": int((~good).sum())}
    icu = action(A, KEYS.index("escalate_icu"))
    for nm in ("admit", "cs_caution"):
        x = action(A, KEYS.index(nm))
        o = float(obs["A"]["num"][KEYS.index(nm)] / obs["A"]["den"][KEYS.index(nm)]
                  - obs["A"]["num"][KEYS.index("escalate_icu")] / obs["A"]["den"][KEYS.index("escalate_icu")])
        g = icu > 0
        out["A_%s_minus_icu" % nm] = {"observed": o, "ci": ci(x - icu), "n_icu_zero": int((icu == 0).sum()),
                                      "ratio_finite_subset_ci": pct((x[g] / icu[g]).tolist())}
    return out


def run_votes(models, arms, W, rdraws):
    out = {}
    for keys_tag, kidx in (("5action", I5), ("6action", list(range(6)))):
        out[keys_tag] = {}
        for lab in ("A", "C", "D", "E", "F"):
            a = arms[lab]
            s1, s5 = Splits(a.R, 1), Splits(a.R, 5)
            ident = list(range(a.R))
            ones = np.ones(a.V)
            f1o = vote_counts(a, ident, ones, s1, kidx)
            f5o = vote_counts(a, ident, ones, s5, kidx)
            f1o, f5o = f1o[0] / f1o[1], f5o[0] / f5o[1]
            reds_c, reds_v, dropped = [], [], 0
            for b in range(B):
                for draw, sink in ((rdraws[lab][b], reds_c), (ident, reds_v)):
                    c1 = vote_counts(a, draw, W[b], s1, kidx)
                    c5 = vote_counts(a, draw, W[b], s5, kidx)
                    if c1 is None or c5 is None or c1[1] == 0 or c5[1] == 0 or c1[0] == 0:
                        if sink is reds_c:
                            dropped += 1
                        continue
                    sink.append(1 - (c5[0] / c5[1]) / (c1[0] / c1[1]))
            out[keys_tag][lab] = {"f1": f1o, "f5": f5o, "reduction": 1 - f5o / f1o,
                                  "ci_crossed": pct(reds_c), "ci_vignette_only_same_draws": pct(reds_v),
                                  "median_crossed": float(np.median(reds_c)),
                                  "median_vignette_only": float(np.median(reds_v)),
                                  "n_dropped_crossed": dropped}
    # NOT A VALID INTERVAL. At R=10, k=5 the vote statistic is one evaluation of a degree-10
    # symmetric kernel that uses every replicate. A with-replacement replicate resample has ~6.5
    # distinct replicates, so a "five-vote" side contains repeats and is effectively a vote of
    # fewer draws; f5 is pushed toward f1 and the bootstrap distribution of 1 - f5/f1 is centred
    # far below the observed reduction (compare median_crossed with reduction). The replicate
    # component of this statistic's variance cannot be estimated nonparametrically from R=10 at
    # k=5 (no replicate can be deleted or repeated without changing the estimator itself), so the
    # crossed percentile interval is recorded for transparency only.
    out["note"] = ("ci_crossed is biased (see median_crossed vs reduction) and is not a valid "
                   "interval; the vote reduction's replicate-level uncertainty is not estimable "
                   "nonparametrically at R=10, k=5. Treat ci_vignette_only as conditional on the "
                   "replicate set.")
    return out


# ---------------------------------------------------------------------------------------
# Temperature-0 and Groq comparisons (vignettes paired, replicates independent per arm)
# ---------------------------------------------------------------------------------------

def load_dir(d):
    import glob
    reps = []
    for p in sorted(glob.glob(os.path.join(pc.EXP, d, "rep*", "trajectories.json"))):
        reps.append({t["vignette_id"]: t["actions"] for t in json.load(open(p, encoding="utf-8"))["trajectories"]
                     if t["complete"] and t["condition_id"] == ps.REFERENCE})
    return reps


def complete_vs(reps):
    return set.intersection(*[set(r) for r in reps])


def temp_pair(d_reps, t_reps, rng, crossed):
    vs = sorted(complete_vs(d_reps) & complete_vs(t_reps))
    ad, at = Arm(d_reps, vs), Arm(t_reps, vs)
    res = {}
    for tag, idx in (("5action", I5), ("6action", list(range(6)))):
        def rate(arm, m, w):
            n, d = arm.counts(m, w)
            return n[idx].sum() / d[idx].sum() if d[idx].sum() else np.nan
        od, ot = rate(ad, np.ones(ad.R), np.ones(len(vs))), rate(at, np.ones(at.R), np.ones(len(vs)))
        res[tag] = {"n_vignettes": len(vs), "default": od, "temp0": ot, "reduction": 1 - ot / od, "_b": ([], [], [])}
    for _ in range(B):
        w = mult([rng.randrange(len(vs)) for _ in vs], len(vs))
        md = mult([rng.randrange(ad.R) for _ in range(ad.R)], ad.R) if crossed else np.ones(ad.R)
        mt = mult([rng.randrange(at.R) for _ in range(at.R)], at.R) if crossed else np.ones(at.R)
        nd, dd = ad.counts(md, w)
        nt, dt = at.counts(mt, w)
        for tag, idx in (("5action", I5), ("6action", list(range(6)))):
            a = nd[idx].sum() / dd[idx].sum() if dd[idx].sum() else np.nan
            t = nt[idx].sum() / dt[idx].sum() if dt[idx].sum() else np.nan
            bd, bt, br = res[tag]["_b"]
            bd.append(a)
            bt.append(t)
            br.append(1 - t / a if a and a == a else np.nan)
    for tag in res:
        bd, bt, br = res[tag].pop("_b")
        res[tag]["ci_default"] = ci(np.array(bd))
        res[tag]["ci_temp0"] = ci(np.array(bt))
        res[tag]["ci_reduction"] = ci(np.array(br))
    return res


def run_temperature():
    out = {}
    for crossed in (True, False):
        rng = random.Random(SEED)
        key = "crossed" if crossed else "vignette_only"
        out[key] = {}
        for lab in ("C", "D", "E", "F"):
            d = pc.local_dir(lab)
            out[key][lab] = temp_pair(load_dir(d), load_dir(d + "_t0"), rng, crossed)
        out[key]["groq_t1_vs_t0"] = temp_pair(load_dir("floor16_groq_t1"), load_dir("floor16_groq_t0"), rng, crossed)
        # Standalone Groq temperature-0 floor over all of its complete vignettes (main text 0.028).
        g = load_dir("floor16_groq_t0")
        vs = sorted(complete_vs(g))
        arm = Arm(g, vs)
        n, d = arm.counts(np.ones(arm.R), np.ones(len(vs)))
        bs = []
        for _ in range(B):
            w = mult([rng.randrange(len(vs)) for _ in vs], len(vs))
            m = mult([rng.randrange(arm.R) for _ in range(arm.R)], arm.R) if crossed else np.ones(arm.R)
            nb, db = arm.counts(m, w)
            bs.append(nb[I5].sum() / db[I5].sum() if db[I5].sum() else np.nan)
        out[key]["groq_t0_alone_5action"] = {"n_vignettes": len(vs), "num": float(n[I5].sum()), "den": float(d[I5].sum()),
                                             "floor": float(n[I5].sum() / d[I5].sum()), "ci": ci(np.array(bs))}
    return out


# ---------------------------------------------------------------------------------------
# Diagnostic: replicate-level (shared-context) dependence
# ---------------------------------------------------------------------------------------

def dependence(arm, rng_np, kidx=I5):
    """Two permutation checks of replicate-level dependence, five actions.

    Null: within every (vignette, action) cell the R answers are exchangeable across
    replicates (no replicate effect). Permuting each cell's answers independently across
    replicates preserves every cell's marginal rate exactly and destroys only cross-cell
    linkage within a replicate. Statistics:
      (i) between-replicate variance of the per-replicate mean action rate (does a replicate
          lean high or low across all its cells?);
      (ii) variance across replicate pairs of the per-pair floor (do some replicate pairs
          disagree more than others?).
    Reported: observed / mean-null ratio (1 = no replicate effect beyond binomial/cell
    expectation) and a one-sided permutation p-value.
    """
    X = arm.X[:, :, kidx]
    R = X.shape[0]

    def stats(Y):
        m = np.nanmean(Y.reshape(R, -1), axis=1)
        ia, ib = np.triu_indices(R, 1)
        ya, yb = Y[ia], Y[ib]
        val = ~np.isnan(ya) & ~np.isnan(yb)
        pf = ((ya != yb) & val).reshape(len(ia), -1).sum(1) / val.reshape(len(ia), -1).sum(1)
        return np.var(m, ddof=1), np.var(pf, ddof=1)

    o1, o2 = stats(X)
    flat = X.reshape(R, -1)
    n1, n2 = [], []
    for _ in range(N_PERM):
        P = np.empty_like(flat)
        perm = np.argsort(rng_np.random(flat.shape), axis=0)
        P = np.take_along_axis(flat, perm, axis=0)
        s1, s2 = stats(P.reshape(X.shape))
        n1.append(s1)
        n2.append(s2)
    n1, n2 = np.array(n1), np.array(n2)
    return {"R": R,
            "rep_mean_rate_var_ratio": float(o1 / n1.mean()), "rep_mean_rate_p": float((1 + (n1 >= o1).sum()) / (1 + N_PERM)),
            "pair_floor_var_ratio": float(o2 / n2.mean()), "pair_floor_p": float((1 + (n2 >= o2).sum()) / (1 + N_PERM))}


def main():
    if os.path.abspath(OUT) != os.path.abspath(os.path.join(pc.EXP, "robustness%s_crossed.json" % pc.SUFFIX)) \
            and os.path.exists(OUT):
        raise SystemExit("refusing to overwrite %s" % OUT)
    models, _ = rb.load_models()
    models = {l: m for l, m in models.items() if l in "ABCDEF"}
    canon = models["A"]["vignettes"]
    assert all(m["vignettes"] == canon for m in models.values())
    labs = sorted(models)

    arms, vres, W, rdraws, cr, vo, obs = run_panel(models, canon)
    s_cr = summarize(cr, obs, labs, "crossed")
    s_vo = summarize(vo, obs, labs, "vignette_only")

    # Regression check: vignette-only branch must reproduce robustness_v3.json item 9 exactly.
    ref = json.load(open(os.path.join(pc.EXP, "robustness%s.json" % pc.SUFFIX), encoding="utf-8"))
    i9 = ref.get("item9_five_action_analysis")
    check = {}
    if i9:
        for l in labs:
            check[l] = [list(i9["models"][l]["ci_5action_B5000"]) == s_vo["models"][l]["ci_5action"],
                        list(i9["models"][l]["ci_6action_B5000"]) == s_vo["models"][l]["ci_6action"]]
    votes = run_votes(models, arms, W, rdraws)
    temp = run_temperature()

    rng_np = np.random.default_rng(SEED)
    diag = {}
    for l in labs:
        diag[l] = dependence(arms[l], rng_np)
        for tag in ("5action", "6action"):
            wc = s_cr["models"][l]["ci_%s" % tag]
            wv = s_vo["models"][l]["ci_%s" % tag]
            diag[l]["width_ratio_%s" % tag] = (wc[1] - wc[0]) / (wv[1] - wv[0])
    for name, d in (("groq_t1", "floor16_groq_t1"), ("groq_t0", "floor16_groq_t0"), ("F_t0", pc.local_dir("F", True))):
        rs = load_dir(d)
        diag[name] = dependence(Arm(rs, sorted(complete_vs(rs))), rng_np)
    wc, wv = temp["crossed"]["groq_t1_vs_t0"]["5action"]["ci_default"], temp["vignette_only"]["groq_t1_vs_t0"]["5action"]["ci_default"]
    diag["groq_t1"]["width_ratio_5action"] = (wc[1] - wc[0]) / (wv[1] - wv[0])

    res = {"meta": {"panel": pc.PANEL, "seed": SEED, "B": B, "method": "crossed vignette x replicate bootstrap "
                    "(Owen 2007), off-diagonal U-statistic weighting m_a*m_b over distinct original replicates; "
                    "vignette resamples identical to robustness.py item 1",
                    "models": {l: models[l]["dir"] for l in labs},
                    "n_reps": {l: arms[l].R for l in labs},
                    "vignette_only_reproduces_robustness_json_item9": check},
           "crossed": s_cr, "vignette_only_same_draws": s_vo,
           "majority_vote": votes, "temperature": temp, "dependence_diagnostics": diag}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=1, default=float)
    print("wrote", OUT)
    print("regression check (5a, 6a CIs identical to robustness json):", check)
    return res


if __name__ == "__main__":
    main()
