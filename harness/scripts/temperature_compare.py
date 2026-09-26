"""Default-sampling versus temperature-0 floors on the four locally served models.

Floors use all replicate pairs within each run (an unbiased estimate of 2p(1-p) per cell
whatever the replicate count), so the ten-replicate default runs and the five-replicate
temperature-0 runs are comparable; a sensitivity row restricts the default runs to their
first five replicates. Intervals are vignette-paired percentile bootstraps (B=5000, seed 42):
each resample draws one vignette multiset and applies it to both runs.

    python temperature_compare.py
"""
import glob
import itertools
import json
import os
import random

HERE = os.path.dirname(os.path.abspath(__file__))
EXP = os.path.join(os.path.dirname(os.path.dirname(HERE)), "experiments")
REF = "ref_white_man_private"
O = {
    "high_acuity": lambda a: (lambda e: None if e is None else e <= 2)((a.get("triage") or {}).get("esi_acuity")),
    "admit": lambda a: (a.get("reassess") or {}).get("admit"),
    "escalate_icu": lambda a: (a.get("reassess") or {}).get("escalate_icu"),
    "any_opioid": lambda a: (lambda t: None if t is None else t >= 2)((a.get("prescribe") or {}).get("analgesia_tier")),
    "cs_caution": lambda a: (a.get("prescribe") or {}).get("controlled_substance_caution"),
    "referral": lambda a: (a.get("document") or {}).get("referral"),
}
MODELS = [("C", "llama3.1:8b", "floor16_ollama"), ("D", "mistral:7b", "floor16_mistral"),
          ("E", "qwen3:4b", "floor16_qwen3"), ("F", "phi3:mini", "floor16_phi3")]


def load(d, first=None):
    reps = []
    for p in sorted(glob.glob(os.path.join(EXP, d, "rep*", "trajectories.json")))[:first]:
        reps.append({t["vignette_id"]: t["actions"] for t in json.load(open(p, encoding="utf-8"))["trajectories"]
                     if t["complete"] and t["condition_id"] == REF})
    return reps


def per_vignette(reps):
    """vignette -> (disagreeing pairs, pairs), pooled over the six actions."""
    out = {}
    vs = set.intersection(*[set(r) for r in reps])
    for v in vs:
        f = n = 0
        for a, b in itertools.combinations(range(len(reps)), 2):
            for g in O.values():
                x, y = g(reps[a][v]), g(reps[b][v])
                if x is None or y is None:
                    continue
                n += 1
                f += x != y
        out[v] = (f, n)
    return out


def rate(pv, vs):
    f = sum(pv[v][0] for v in vs)
    n = sum(pv[v][1] for v in vs)
    return f / n if n else float("nan")


rng = random.Random(42)
B = 5000
res = {}
for mid, name, d in MODELS:
    dflt, dflt5, t0 = per_vignette(load(d)), per_vignette(load(d, 5)), per_vignette(load(d + "_t0"))
    vs = sorted(set(dflt) & set(t0))
    obs = {"default_R10": rate(dflt, vs), "default_first5": rate(dflt5, vs), "temp0_R5": rate(t0, vs)}
    boots = {"default_R10": [], "temp0_R5": [], "reduction": []}
    for _ in range(B):
        s = [rng.choice(vs) for _ in vs]
        a, b = rate(dflt, s), rate(t0, s)
        boots["default_R10"].append(a)
        boots["temp0_R5"].append(b)
        boots["reduction"].append(1 - b / a if a > 0 else float("nan"))
    ci = {}
    for k, xs in boots.items():
        xs = sorted(x for x in xs if x == x)
        ci[k] = [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]]
    retried = failed = calls = 0
    for p in glob.glob(os.path.join(EXP, "_scratch_t0_%s" % d.replace("floor16_", ""), "*_ans.json")):
        pr = json.load(open(p, encoding="utf-8")).get("provenance", {})
        retried += len(pr.get("retried_ids", []))
        failed += len(pr.get("failed_ids", []))
        calls += len(json.load(open(p, encoding="utf-8")).get("answers", [])) + len(pr.get("failed_ids", []))
    res[mid] = {"model": name, "observed": obs, "ci_B5000": ci,
                "reduction_observed": 1 - obs["temp0_R5"] / obs["default_R10"],
                "t0_calls": calls, "t0_retried": retried, "t0_failed": failed, "n_vignettes": len(vs)}
    print("%s %-12s default %.3f [%.3f,%.3f] (first5 %.3f)  temp0 %.3f [%.3f,%.3f]  reduction %.2f [%.2f,%.2f]  retried %d/%d failed %d"
          % (mid, name, obs["default_R10"], *ci["default_R10"], obs["default_first5"], obs["temp0_R5"], *ci["temp0_R5"],
             res[mid]["reduction_observed"], *ci["reduction"], retried, calls, failed))
# Hosted endpoint (Groq, openai/gpt-oss-20b) at temperature 0, five replicates. The planned
# temperature-1.0 arm stalled on the provider's free-tier daily limit after one replicate and
# is not reported; the temperature-0 arm alone tests whether pinning removes the floor there.
hosted = {}
if len(glob.glob(os.path.join(EXP, "floor16_groq_t0", "rep*", "trajectories.json"))) == 5:
    t0 = per_vignette(load("floor16_groq_t0"))
    vs = sorted(t0)
    f_ = sum(t0[v][0] for v in vs)
    n_ = sum(t0[v][1] for v in vs)
    bs = []
    for _ in range(B):
        s = [rng.choice(vs) for _ in vs]
        bs.append(rate(t0, s))
    bs.sort()
    fps, calls, retried, failed = set(), 0, 0, 0
    for p in glob.glob(os.path.join(EXP, "_scratch_groq_t0", "*_ans.json")):
        j = json.load(open(p, encoding="utf-8"))
        pr = j.get("provenance", {})
        fps.update(pr.get("system_fingerprints", []))
        retried += len(pr.get("retried_ids", []))
        failed += len(pr.get("failed_ids", []))
        calls += len(j.get("answers", [])) + len(pr.get("failed_ids", []))
    hosted = {"provider": "groq", "model": "openai/gpt-oss-20b", "reasoning_effort": "low",
              "temperature": 0.0, "replicates": 5, "n_vignettes": len(vs),
              "disagreeing": f_, "comparisons": n_, "floor": f_ / n_,
              "ci_B5000": [bs[int(0.025 * B)], bs[int(0.975 * B) - 1]],
              "calls": calls, "retried": retried, "failed": failed,
              "distinct_system_fingerprints": len(fps)}
    print("HOSTED groq gpt-oss-20b temp0: %d/%d = %.3f [%.3f, %.3f]; calls %d retried %d failed %d; fingerprints %d"
          % (f_, n_, f_ / n_, hosted["ci_B5000"][0], hosted["ci_B5000"][1], calls, retried, failed, len(fps)))
if False and all(len(glob.glob(os.path.join(EXP, "floor16_groq_%s" % t, "rep*", "trajectories.json"))) == 5 for t in ("t1", "t0")):
    t1, t0 = per_vignette(load("floor16_groq_t1")), per_vignette(load("floor16_groq_t0"))
    vs = sorted(set(t1) & set(t0))
    obs = {"temp1_R5": rate(t1, vs), "temp0_R5": rate(t0, vs)}
    b1, b0, br = [], [], []
    for _ in range(B):
        s = [rng.choice(vs) for _ in vs]
        a, b = rate(t1, s), rate(t0, s)
        b1.append(a); b0.append(b); br.append(1 - b / a if a > 0 else float("nan"))
    ci = {}
    for k, xs in (("temp1_R5", b1), ("temp0_R5", b0), ("reduction", br)):
        xs = sorted(x for x in xs if x == x)
        ci[k] = [xs[int(0.025 * len(xs))], xs[int(0.975 * len(xs)) - 1]] if xs else [None, None]
    prov = {"temp1": {"retried": 0, "failed": 0, "calls": 0, "fingerprints": set()},
            "temp0": {"retried": 0, "failed": 0, "calls": 0, "fingerprints": set()}}
    for tag, key in (("t1", "temp1"), ("t0", "temp0")):
        for p in glob.glob(os.path.join(EXP, "_scratch_groq_%s" % tag, "*_ans.json")):
            j = json.load(open(p, encoding="utf-8"))
            pr = j.get("provenance", {})
            prov[key]["retried"] += len(pr.get("retried_ids", []))
            prov[key]["failed"] += len(pr.get("failed_ids", []))
            prov[key]["calls"] += len(j.get("answers", [])) + len(pr.get("failed_ids", []))
            prov[key]["fingerprints"].update(pr.get("system_fingerprints", []))
    for key in prov:
        prov[key]["fingerprints"] = sorted(prov[key]["fingerprints"])
    hosted = {"provider": "groq", "model": "openai/gpt-oss-20b", "reasoning_effort": "low",
              "observed": obs, "ci_B5000": ci,
              "reduction_observed": (1 - obs["temp0_R5"] / obs["temp1_R5"]) if obs["temp1_R5"] else None,
              "provenance": prov, "n_vignettes": len(vs)}
    print("HOSTED groq gpt-oss-20b  temp1 %.3f [%.3f,%.3f]  temp0 %.3f [%.3f,%.3f]  reduction %s  n_vign %d  fps %s/%s"
          % (obs["temp1_R5"], *ci["temp1_R5"], obs["temp0_R5"], *ci["temp0_R5"],
             hosted["reduction_observed"], len(vs), len(prov["temp1"]["fingerprints"]), len(prov["temp0"]["fingerprints"])))
json.dump({"B": B, "seed": 42, "models": res, "hosted": hosted},
          open(os.path.join(EXP, "temperature_compare.json"), "w"), indent=1)
