"""Default-sampling versus temperature-0 floors on the four locally served models.

Floors use all replicate pairs within each run (an unbiased estimate of 2p(1-p) per cell
whatever the replicate count), so the ten-replicate default runs and the five-replicate
temperature-0 runs are comparable; a sensitivity row restricts the default runs to their
first five replicates. Intervals are vignette-paired percentile bootstraps (B=5000, seed 42):
each resample draws one vignette multiset and applies it to both runs.

    python temperature_compare.py

Call counts, retry counts and system fingerprints of the hosted (Groq) runs come from the
per-call attempt logs (experiments/_scratch_groq_t0, _scratch_groq_t1), which are not part of
this release. When those logs are absent the script keeps the corresponding fields of the
existing experiments/temperature_compare_v3.json and prints a note, so that running it does not
overwrite them.
"""
import glob
import itertools
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import panel_config as pc  

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
MODELS = [("C", "llama3.1:8b", pc.local_dir("C")), ("D", "mistral:7b", pc.local_dir("D")),
          ("E", "qwen3:4b", pc.local_dir("E")), ("F", "phi3:mini", pc.local_dir("F"))]


OUT_PATH = os.environ.get("FMA_TEMPERATURE_OUT") or pc.out_path("temperature_compare", "json")
try:
    PREV = json.load(open(OUT_PATH, encoding="utf-8"))
except (OSError, ValueError):
    PREV = {}


def scratch_stats(tag):
    """Call, retry and failure counts and system fingerprints from experiments/_scratch_groq_<tag>.

    Returns None when the attempt logs are not present.
    """
    files = glob.glob(os.path.join(EXP, "_scratch_groq_%s" % tag, "*_ans.json"))
    if not files:
        return None
    out = {"retried": 0, "failed": 0, "calls": 0, "fingerprints": set()}
    for p in files:
        j = json.load(open(p, encoding="utf-8"))
        pr = j.get("provenance", {})
        out["retried"] += len(pr.get("retried_ids", []))
        out["failed"] += len(pr.get("failed_ids", []))
        out["calls"] += len(j.get("answers", [])) + len(pr.get("failed_ids", []))
        out["fingerprints"].update(pr.get("system_fingerprints", []))
    return out


def arm_attempts(d):
    """(prompts, first_attempt_failures, retries, final_failures) for one arm.

    The reruns carry attempt_summary.json; any other arm is read from the per-step provenance
    in its _scratch directory when present.
    """
    p = os.path.join(EXP, d, "attempt_summary.json")
    if os.path.exists(p):
        s = json.load(open(p, encoding="utf-8"))
        return {"calls": s["prompts"], "first_attempt_failures": s["first_attempt_failures"],
                "retried": s["retries"], "failed": s["final_failures"], "source": "attempt_summary.json"}
    if not d.endswith("_t0"):
        return {"calls": None, "first_attempt_failures": None, "retried": None, "failed": None,
                "source": "not logged for the old default arm"}
    retried = failed = calls = 0
    for q in glob.glob(os.path.join(EXP, "_scratch_t0_%s" % d.replace("floor16_", "").replace("_t0", ""), "*_ans.json")):
        pr = json.load(open(q, encoding="utf-8")).get("provenance", {})
        retried += len(pr.get("retried_ids", []))
        failed += len(pr.get("failed_ids", []))
        calls += len(json.load(open(q, encoding="utf-8")).get("answers", [])) + len(pr.get("failed_ids", []))
    return {"calls": calls, "first_attempt_failures": None, "retried": retried, "failed": failed,
            "source": "_scratch provenance"}


def load(d, first=None):
    reps = []
    for p in sorted(glob.glob(os.path.join(EXP, d, "rep*", "trajectories.json")))[:first]:
        reps.append({t["vignette_id"]: t["actions"] for t in json.load(open(p, encoding="utf-8"))["trajectories"]
                     if t["complete"] and t["condition_id"] == REF})
    return reps


FIVE = [k for k in O if k != "cs_caution"]


def per_vignette(reps, keys=None):
    """vignette -> (disagreeing pairs, pairs), pooled over the six outputs (or over `keys`)."""
    gs = [O[k] for k in keys] if keys else list(O.values())
    out = {}
    vs = set.intersection(*[set(r) for r in reps])
    for v in vs:
        f = n = 0
        for a, b in itertools.combinations(range(len(reps)), 2):
            for g in gs:
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
    vs = sorted(set(dflt) & set(t0))  # vignettes complete in every replicate of both arms
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
    at0 = arm_attempts(d + "_t0")
    adf = arm_attempts(d)
    retried, failed, calls = at0["retried"], at0["failed"], at0["calls"]
    res[mid] = {"model": name, "observed": obs, "ci_B5000": ci,
                "reduction_observed": 1 - obs["temp0_R5"] / obs["default_R10"],
                "t0_calls": calls, "t0_retried": retried, "t0_failed": failed, "n_vignettes": len(vs),
                "vignettes_default_complete": len(dflt), "vignettes_t0_complete": len(t0),
                "attempts_default": adf, "attempts_t0": at0}
    print("%s %-12s default %.3f [%.3f,%.3f] (first5 %.3f)  temp0 %.3f [%.3f,%.3f]  reduction %.2f [%.2f,%.2f]  retried %d/%d failed %d"
          % (mid, name, obs["default_R10"], *ci["default_R10"], obs["default_first5"], obs["temp0_R5"], *ci["temp0_R5"],
             res[mid]["reduction_observed"], *ci["reduction"], retried, calls, failed))
# Hosted endpoint (Groq, openai/gpt-oss-20b) at temperature 0, five replicates. The planned
# temperature-1.0 arm stalled on the provider's free-tier daily limit after one replicate and
# was completed overnight once the limit reset; the paired block below compares the two arms on
# the vignettes complete in every replicate of both.
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
    st0 = scratch_stats("t0")
    if st0 is not None:
        fps, calls, retried, failed = st0["fingerprints"], st0["calls"], st0["retried"], st0["failed"]
        nfp = len(fps)
    else:
        ph = PREV.get("hosted", {})
        calls, retried, failed = ph.get("calls"), ph.get("retried"), ph.get("failed")
        nfp = ph.get("distinct_system_fingerprints")
        print("NOTE: experiments/_scratch_groq_t0 not found; call counts and system fingerprints "
              "carried over from the existing %s" % os.path.basename(OUT_PATH))
    hosted = {"provider": "groq", "model": "openai/gpt-oss-20b", "reasoning_effort": "low",
              "temperature": 0.0, "replicates": 5, "n_vignettes": len(vs),
              "disagreeing": f_, "comparisons": n_, "floor": f_ / n_,
              "ci_B5000": [bs[int(0.025 * B)], bs[int(0.975 * B) - 1]],
              "calls": calls, "retried": retried, "failed": failed,
              "distinct_system_fingerprints": nfp}
    d5 = per_vignette(load("floor16_groq_t0"), FIVE)
    f5 = sum(d5[v][0] for v in vs)
    n5 = sum(d5[v][1] for v in vs)
    print("HOSTED groq gpt-oss-20b temp0, five actions: %d/%d = %.3f" % (f5, n5, f5 / n5))
    print("  (six-output pool: %d/%d = %.3f [%.3f, %.3f]; calls %s retried %s failed %s; fingerprints %s)"
          % (f_, n_, f_ / n_, hosted["ci_B5000"][0], hosted["ci_B5000"][1], calls, retried, failed, nfp))
if hosted and all(len(glob.glob(os.path.join(EXP, "floor16_groq_%s" % t, "rep*", "trajectories.json"))) == 5 for t in ("t1", "t0")):
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
    prov = {}
    for tag, key in (("t1", "temp1"), ("t0", "temp0")):
        st = scratch_stats(tag)
        if st is not None:
            st["fingerprints"] = sorted(st["fingerprints"])
            prov[key] = st
        else:
            prov[key] = (PREV.get("hosted", {}).get("paired", {}).get("provenance", {}).get(key, {}))
            print("NOTE: experiments/_scratch_groq_%s not found; its call counts and system "
                  "fingerprints carried over from the existing %s" % (tag, os.path.basename(OUT_PATH)))
    hosted["paired"] = {"observed": obs, "ci_B5000": ci,
              "reduction_observed": (1 - obs["temp0_R5"] / obs["temp1_R5"]) if obs["temp1_R5"] else None,
              "provenance": prov, "n_vignettes": len(vs)}
    p1, p0 = per_vignette(load("floor16_groq_t1"), FIVE), per_vignette(load("floor16_groq_t0"), FIVE)
    r1, r0 = rate(p1, vs), rate(p0, vs)
    print("HOSTED groq gpt-oss-20b paired, five actions (%d vignettes): temp1 %.3f, temp0 %.3f, reduction %.0f percent"
          % (len(vs), r1, r0, 100 * (1 - r0 / r1)))
    print("  (six-output pool: temp1 %.3f [%.3f,%.3f]  temp0 %.3f [%.3f,%.3f]  reduction %.0f percent; fingerprints %s/%s)"
          % (obs["temp1_R5"], *ci["temp1_R5"], obs["temp0_R5"], *ci["temp0_R5"],
             100 * hosted["paired"]["reduction_observed"],
             len(prov["temp1"].get("fingerprints", [])), len(prov["temp0"].get("fingerprints", []))))
json.dump({"B": B, "seed": 42, "models": res, "hosted": hosted},
          open(OUT_PATH, "w"), indent=1)
