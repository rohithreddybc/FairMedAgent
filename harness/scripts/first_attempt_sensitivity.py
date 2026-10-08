"""First-attempt-only sensitivity of the pooled floor for the v3 local arms.

The full-harness floor uses the answer the harness finally accepted, so a prompt whose first
attempt failed to parse and whose retry succeeded contributes the retry's answer. This script
asks how much that matters: for every prompt whose first attempt failed, the outcomes that
prompt feeds are treated as missing (not imputed), and the pooled floor is recomputed with the
same pairwise-counting rule and the same vignette-cluster bootstrap (B=5000, seed 42) as
panel_summary.py.

Step-to-outcome map (the harness advances s1..s5 in this order):
    s1 triage    -> high_acuity
    s2 orders    -> (not a scored outcome)
    s3 reassess  -> admit, escalate_icu
    s4 prescribe -> any_opioid, cs_caution
    s5 document  -> referral

Prompt ids are mapped to vignettes by rank: within a step file the ids ascend with the order
of the reference-condition trajectories in trajectories.json. The mapping is verified against
the final answers before any masking is trusted (see "mapping_check" in the output).

    python first_attempt_sensitivity.py        -> experiments/first_attempt_v3.json
"""
from __future__ import annotations

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import panel_config as pc  # noqa: E402
import panel_summary as ps  # noqa: E402

EXP = pc.EXP
REF = ps.REFERENCE
STAGE_KEY = {1: "triage", 3: "reassess", 4: "prescribe", 5: "document"}
# (step, final-answer key, trajectory section) used to verify the id -> vignette mapping.
CHECK = {1: ("esi_acuity", "triage"), 3: ("admit", "reassess"),
         4: ("analgesia_tier", "prescribe"), 5: ("referral", "document")}
B = 5000
SEED = 42


def load_arm(d: str):
    """Return (full_reps, masked_reps, stats) for one arm directory."""
    root = os.path.join(EXP, d)
    full, masked = [], []
    n_prompts = n_first_fail = n_cells_masked = mismatches = checked = 0
    for name in sorted(os.listdir(root)):
        tp = os.path.join(root, name, "trajectories.json")
        if not os.path.exists(tp):
            continue
        traj = [t for t in json.load(open(tp, encoding="utf-8"))["trajectories"]
                if t["condition_id"] == REF]
        order = [t["vignette_id"] for t in traj]
        acts = {t["vignette_id"]: t["actions"] for t in traj if t["complete"]}
        if not acts:
            continue
        mask = set()  # (vignette, step)
        for step in range(1, 6):
            ap = os.path.join(root, name, "answers", "s%d.json" % step)
            if not os.path.exists(ap):
                continue
            dd = json.load(open(ap, encoding="utf-8"))
            ids = sorted(rec["id"] for rec in dd["attempts"])
            final = {a["id"]: a["action"] for a in dd["answers"]}
            if len(ids) != len(order):
                raise SystemExit("%s/%s s%d: %d prompts but %d reference trajectories"
                                 % (d, name, step, len(ids), len(order)))
            vig = dict(zip(ids, order))
            for rec in dd["attempts"]:
                n_prompts += 1
                v = vig[rec["id"]]
                if not rec["attempts"][0]["parsed"]:
                    n_first_fail += 1
                    mask.add((v, step))
                if step in CHECK and rec["id"] in final and v in acts:
                    key, sec = CHECK[step]
                    checked += 1
                    if (acts[v].get(sec) or {}).get(key) != final[rec["id"]].get(key):
                        mismatches += 1
        full.append(acts)
        mrep = {}
        for v, a in acts.items():
            a2 = dict(a)
            for step, sec in STAGE_KEY.items():
                if (v, step) in mask:
                    a2[sec] = None
                    n_cells_masked += 1
            mrep[v] = a2
        masked.append(mrep)
    stats = {"prompts": n_prompts, "first_attempt_failures": n_first_fail,
             "step_cells_masked_in_complete_trajectories": n_cells_masked,
             "mapping_check": {"answers_compared": checked, "mismatches": mismatches}}
    return full, masked, stats


def pooled(reps, vs):
    per = ps.counts(reps, vs)
    num = sum(per[k][0] for k in ps.KEYS)
    den = sum(per[k][1] for k in ps.KEYS)
    return num, den


def boot_ci(reps, vs):
    rng = random.Random(SEED)
    draws = []
    for _ in range(B):
        samp = [rng.choice(vs) for _ in vs]
        c = ps.counts(reps, samp)
        n = sum(c[k][1] for k in ps.KEYS)
        if n:
            draws.append(sum(c[k][0] for k in ps.KEYS) / n)
    draws.sort()
    return [draws[int(0.025 * len(draws))], draws[min(len(draws) - 1, int(0.975 * len(draws)))]]


def main() -> int:
    out = {"B": B, "seed": SEED, "arms": {}}
    arms = [(lab, pc.NEW_LOCAL[lab], False) for lab in "CDEF"] + \
           [(lab, pc.NEW_LOCAL[lab], True) for lab in "CDEF"]
    print("%-3s %-4s %-18s %7s %9s %9s  %-16s %s"
          % ("id", "arm", "dir", "prompts", "1st-fail", "masked", "full floor [CI]", "first-attempt floor [CI]"))
    for lab, base, t0 in arms:
        d = base + ("_t0" if t0 else "")
        full, masked, st = load_arm(d)
        vs = sorted(set.intersection(*[set(r) for r in full]))
        fn, fd = pooled(full, vs)
        mn, md = pooled(masked, vs)
        e = {"dir": d, "R": len(full), "n_vignettes": len(vs), **st,
             "full": {"num": fn, "den": fd, "floor": fn / fd},
             "first_attempt_only": {"num": mn, "den": md, "floor": mn / md},
             "comparisons_lost": fd - md}
        if not t0:
            e["full"]["ci_B5000"] = boot_ci(full, vs)
            e["first_attempt_only"]["ci_B5000"] = (boot_ci(masked, vs) if fd != md
                                                    else e["full"]["ci_B5000"])
            e["first_attempt_only"]["ci_note"] = (
                "identical to full: no comparison was lost" if fd == md else "separate bootstrap")
        e["difference_first_minus_full"] = e["first_attempt_only"]["floor"] - e["full"]["floor"]
        out["arms"]["%s%s" % (lab, "_t0" if t0 else "")] = e
        ci_f = ("[%.3f, %.3f]" % tuple(e["full"]["ci_B5000"])) if "ci_B5000" in e["full"] else "-"
        ci_m = ("[%.3f, %.3f]" % tuple(e["first_attempt_only"]["ci_B5000"])
                if "ci_B5000" in e["first_attempt_only"] else "-")
        print("%-3s %-4s %-18s %7d %9d %9d  %.4f %-12s %.4f %s  (lost %d comparisons; mapping mismatches %d/%d)"
              % (lab, "t0" if t0 else "dflt", d, st["prompts"], st["first_attempt_failures"],
                 st["step_cells_masked_in_complete_trajectories"], e["full"]["floor"], ci_f,
                 e["first_attempt_only"]["floor"], ci_m, fd - md,
                 st["mapping_check"]["mismatches"], st["mapping_check"]["answers_compared"]))
    json.dump(out, open(os.path.join(EXP, "first_attempt_v3.json"), "w", encoding="utf-8"), indent=1)
    print("wrote", os.path.join(EXP, "first_attempt_v3.json"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
