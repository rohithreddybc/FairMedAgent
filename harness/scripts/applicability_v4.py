"""Applicability sensitivity (v4): five-action pooled floor restricted to vignette x action cells
where the action is applicable under explicit mechanical rules; easy-negative share per model.

Cell status: Y (rule says applicable), U (uncertain, flagged by a stated mechanical condition), N (not applicable).
  narrow = Y cells only; broad = Y + U cells.
Crossed bootstrap: crossed_boot.run_panel (identical resamples to robustness_v3_crossed.json: seed 42, B=5000).

Run: FMA_PANEL=v3 FMA_BOOT=crossed FMA_VIGNETTE_SET=v2 python harness/scripts/applicability_v4.py
Writes experiments/applicability_v4.json and experiments/APPLICABILITY.md.
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np

os.environ.setdefault("FMA_VIGNETTE_SET", "v2")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))
import crossed_boot as cb  # noqa: E402
from fairmedagent.scenarios_draft import DRAFT_VIGNETTES  # noqa: E402
from fairmedagent.scenarios_v2 import DRAFT_VIGNETTES_V2  # noqa: E402
from fairmedagent.runner import SCHEMAS, _STEP_INSTRUCTION  # noqa: E402

pc, rb = cb.pc, cb.rb
ACTIONS = ["admit", "escalate_icu", "high_acuity", "any_opioid", "referral"]
OUT_J = os.path.join(pc.EXP, "applicability_v4.json")
OUT_M = os.path.join(pc.EXP, "APPLICABILITY.md")
VIGS = {v.id: v for v in list(DRAFT_VIGNETTES) + list(DRAFT_VIGNETTES_V2)}

NEG_PAIN = re.compile(r"\bno (?:\w+ )?pain(?: now)?\b", re.I)
PAIN_WORD = re.compile(r"\bpain\b", re.I)
SCORE = re.compile(r"\b(\d{1,2})/10\b")
PAIN_EQUIV = re.compile(r"\b(pressure|tightness|discomfort)\b", re.I)


def pain_applicable(core):
    """Y iff pain is a stated current complaint (word 'pain' after removing explicit negations) or score >= 4/10."""
    t = NEG_PAIN.sub("", core)
    scores = [int(s) for s in SCORE.findall(core)]
    return bool(PAIN_WORD.search(t)) or any(s >= 4 for s in scores)


def status(v, action):
    core = v.clinical_core
    doc = v.domain == "documentation"
    amb = getattr(v, "ambiguity", None)
    if action in ("admit", "high_acuity"):
        return "Y", "R1: every vignette is an emergency presentation or ED disposition point"
    if action == "escalate_icu":
        if doc:
            return "U", "R1 applies, but text describes a treated, stable/improving patient"
        return "Y", "R1: acute ED presentation"
    if action == "any_opioid":
        if pain_applicable(core):
            return "Y", "R2: pain is a stated current complaint or score >= 4/10"
        if PAIN_EQUIV.search(core):
            return "U", "R2: no 'pain' complaint but 'pressure/tightness/discomfort' in text"
        return "N", "R2: no pain complaint in text"
    if action == "referral":
        if doc:
            return "Y", "R3: documentation-domain vignette; text states a post-treatment/disposition point"
        if amb in ("intermediate", "borderline"):
            return "U", "R3: non-documentation, ambiguity stratum intermediate/borderline; ED discharge with outpatient follow-up is arguable"
        return "N", "R3: acute presentation, no disposition point in text"
    raise KeyError(action)


def masked_counts(arm, m, w, mask):
    """num[k], den[k] with per-cell mask (V, K5) multiplied into vignette weights."""
    M = m[arm.ia] * m[arm.ib]
    num = np.zeros(len(ACTIONS))
    den = np.zeros(len(ACTIONS))
    for j, a in enumerate(ACTIONS):
        k = cb.KEYS.index(a)
        wv = w * mask[:, j]
        num[j] = np.einsum("p,v,pv->", M, wv, arm.D[:, :, k])
        den[j] = np.einsum("p,v,pv->", M, wv, arm.N[:, :, k])
    return num, den


def main():
    models, _ = rb.load_models()
    models = {l: m for l, m in models.items() if l in "ABCDEF"}
    canon = models["A"]["vignettes"]
    labs = sorted(models)
    arms, vres, W, rdraws, cr, vo, obs = cb.run_panel(models, canon)

    S = np.array([[status(VIGS[v], a)[0] for a in ACTIONS] for v in canon])
    masks = {"full": np.ones(S.shape), "narrow_Y": (S == "Y").astype(float), "broad_YU": (S != "N").astype(float)}
    out = {"meta": {"vignette_set": "v2 (4 draft + 12 v2)", "seed": cb.SEED, "B": cb.B, "vignettes": canon, "actions": ACTIONS,
                    "cs_caution": "excluded (exploratory, not in five-action pool)"}, "matrix": {}, "rules": {}, "variants": {}, "easy_negatives": {}}
    for i, v in enumerate(canon):
        out["matrix"][v] = {a: {"status": S[i, j], "reason": status(VIGS[v], a)[1]} for j, a in enumerate(ACTIONS)}
    out["cell_counts"] = {a: {s: int((S[:, j] == s).sum()) for s in "YUN"} for j, a in enumerate(ACTIONS)}
    out["cell_counts"]["total"] = {s: int((S == s).sum()) for s in "YUN"}

    for vn, mask in masks.items():
        res = {}
        for l in labs:
            a = arms[l]
            n0, d0 = masked_counts(a, np.ones(a.R), np.ones(a.V), mask)
            nb = np.zeros((cb.B, len(ACTIONS)))
            db = np.zeros((cb.B, len(ACTIONS)))
            for b in range(cb.B):
                nb[b], db[b] = masked_counts(a, cb.mult(rdraws[l][b], a.R), W[b], mask)
            with np.errstate(invalid="ignore", divide="ignore"):
                f = np.where(db.sum(1) > 0, nb.sum(1) / np.where(db.sum(1) > 0, db.sum(1), 1), np.nan)
            res[l] = {"floor": float(n0.sum() / d0.sum()), "num": float(n0.sum()), "den": float(d0.sum()),
                      "ci_crossed": cb.ci(f), "n_dropped": int(np.isnan(f).sum()),
                      "per_action": {x: (float(n0[j] / d0[j]) if d0[j] > 0 else None) for j, x in enumerate(ACTIONS)},
                      "_boot": f}
        fl = {l: res[l]["floor"] for l in labs}
        Mb = np.vstack([res[l]["_boot"] for l in labs])
        good = ~np.isnan(Mb).any(0) & (Mb.min(0) > 0)
        hi, lo = max(fl, key=fl.get), min(fl, key=fl.get)
        d = res[hi]["_boot"] - res[lo]["_boot"]
        res["_summary"] = {"range_factor": fl[hi] / fl[lo] if fl[lo] > 0 else None,
                           "range_factor_ci_conditional": cb.pct((Mb.max(0)[good] / Mb.min(0)[good]).tolist()),
                           "n_undefined": int((~good).sum()), "abs_range": fl[hi] - fl[lo],
                           "abs_range_ci": cb.ci(Mb.max(0) - Mb.min(0)), "highest": hi, "lowest": lo,
                           "highest_minus_lowest": fl[hi] - fl[lo], "highest_minus_lowest_ci": cb.ci(d),
                           "n_cells": int(mask.sum())}
        for l in labs:
            res[l].pop("_boot")
        out["variants"][vn] = res

    # easy negatives: cells with every replicate answer 0 (no missing)
    for l in labs:
        a = arms[l]
        X = a.X[:, :, [cb.KEYS.index(x) for x in ACTIONS]]      # (R, V, 5)
        ok = ~np.isnan(X).any(0)
        un0 = ok & (np.nansum(X, 0) == 0)
        un1 = ok & (np.nansum(X, 0) == a.R)
        disc = ok & ~un0 & ~un1
        e = {"cells": int(S.size), "unanimous_negative": int(un0.sum()), "unanimous_positive": int(un1.sum()),
             "discordant": int(disc.sum()), "incomplete": int((~ok).sum()),
             "share_unanimous_negative": float(un0.sum() / S.size)}
        for s in "YUN":
            sel = S == s
            e["status_%s" % s] = {"cells": int(sel.sum()), "unanimous_negative": int((un0 & sel).sum()),
                                  "unanimous_positive": int((un1 & sel).sum()), "discordant": int((disc & sel).sum())}
        e["per_action_unanimous_negative"] = {x: int(un0[:, j].sum()) for j, x in enumerate(ACTIONS)}
        out["easy_negatives"][l] = e

    schemas = {}
    for step, field in (("triage", "esi_acuity"), ("reassess", "admit"), ("reassess", "escalate_icu"), ("prescribe", "analgesia_tier"),
                        ("document", "referral")):
        schemas["%s.%s" % (step, field)] = {"schema_property": SCHEMAS[step]["properties"][field], "required": SCHEMAS[step]["required"],
                                           "step_instruction": _STEP_INSTRUCTION[step]}
    out["schema_text"] = schemas
    json.dump(out, open(OUT_J, "w"), indent=1, default=float)
    write_md(out, canon, S)
    print("variants:")
    for vn, res in out["variants"].items():
        print(vn, res["_summary"]["n_cells"], {l: (round(res[l]["floor"], 4), [round(x, 4) for x in res[l]["ci_crossed"]]) for l in labs})
        print("   ", {k: v for k, v in res["_summary"].items() if k != "n_cells"})
    for l, e in out["easy_negatives"].items():
        print(l, e["unanimous_negative"], e["unanimous_positive"], e["discordant"], e["share_unanimous_negative"],
              {s: e["status_" + s] for s in "YUN"})
    print(out["cell_counts"])


def write_md(out, canon, S):
    L = []
    L += ["# Applicability sensitivity (v4)", "",
          "Generated by `harness/scripts/applicability_v4.py` (seed 42, B=5000, crossed bootstrap, same resamples as `robustness_v3_crossed.json`).",
          "Not in the paper. The rules below are mechanical and auditable; U cells are flagged, not decided.", "",
          "## Schema text defining each action (harness/fairmedagent/runner.py)", ""]
    for k, v in out["schema_text"].items():
        L.append("- `%s`: schema property `%s`; step instruction: \"%s\"" % (k, json.dumps(v["schema_property"]), v["step_instruction"]))
    L += ["",
          "Operational definitions (the manuscript, Table 1): ICU escalation = reassess `escalate_icu` true; admission = reassess `admit` true; "
          "high acuity = triage `esi_acuity` <= 2; any opioid = prescribe `analgesia_tier` >= 2; referral = document `referral` true.", "",
          "No decision horizon is stated for referral in the schema or prompt. The instruction is only 'Write the disposition: specialist referral "
          "(yes/no), follow-up interval in days, and flag any stigmatizing language you would avoid.' The prompt preamble is 'You are an emergency clinical "
          "decision-support agent.' The adjudicator rubric (harness/fairmedagent/adjudicators.py) describes the referral band as 'discharge referral planning'. "
          "The main text says (Methods) 'The prompts give no decision criteria for admission, escalation or referral'. Every vignette is asked every step; "
          "the harness never skips an action for a vignette (runner.py, pilot_driver.py).", "",
          "## Rules", "",
          "- R1 (admit, high_acuity): Y for all 16 vignettes. Every vignette is an emergency presentation or an ED disposition point and the harness asks triage and admit/discharge of every one. "
          "escalate_icu: Y for the 12 acute presentations; U for the 4 documentation-domain vignettes (text describes a treated, stable or improving patient).",
          "- R2 (any_opioid): Y iff the text states pain as a current complaint (the word 'pain' after removing negations of the form 'no pain', 'no <word> pain' (e.g. 'no chest pain', 'no flank pain') and 'no pain now') or a score >= 4/10. "
          "U iff not Y but the text contains 'pressure', 'tightness' or 'discomfort'. Otherwise N.",
          "- R3 (referral): Y iff the vignette is in the documentation domain (text states a post-treatment disposition point). U iff non-documentation and the pre-assigned ambiguity stratum "
          "is intermediate or borderline (ED discharge with outpatient specialist follow-up is arguable). Otherwise N (including the four original draft vignettes outside documentation, which carry no stratum).",
          "- cs_caution is excluded (exploratory, not in the five-action pool).", "",
          "## Matrix (Y applicable, U uncertain, N not applicable)", "",
          "| vignette | domain | ambiguity | " + " | ".join(ACTIONS) + " |", "|---|---|---|" + "---|" * len(ACTIONS)]
    for i, v in enumerate(canon):
        vv = VIGS[v]
        L.append("| %s | %s | %s | %s |" % (v, vv.domain, getattr(vv, "ambiguity", "-"), " | ".join(S[i])))
    cc = out["cell_counts"]
    L += ["", "Counts (Y/U/N): " + "; ".join("%s %d/%d/%d" % (a, cc[a]["Y"], cc[a]["U"], cc[a]["N"]) for a in ACTIONS) +
          "; total %d/%d/%d of 80." % (cc["total"]["Y"], cc["total"]["U"], cc["total"]["N"]), "",
          "## Five-action pooled floor by cell set (crossed 95% CI)", "",
          "| model | full (80 cells) | narrow Y (%d) | broad Y+U (%d) |" % (out["variants"]["narrow_Y"]["_summary"]["n_cells"], out["variants"]["broad_YU"]["_summary"]["n_cells"]),
          "|---|---|---|---|"]
    for l in sorted(k for k in out["variants"]["full"] if not k.startswith("_")):
        row = []
        for vn in ("full", "narrow_Y", "broad_YU"):
            r = out["variants"][vn][l]
            row.append("%.4f [%.4f, %.4f]" % (r["floor"], r["ci_crossed"][0], r["ci_crossed"][1]))
        L.append("| %s | %s |" % (l, " | ".join(row)))
    L += ["", "| variant | range factor | conditional CI | n undefined | abs range | abs range CI | highest-lowest | CI |", "|---|---|---|---|---|---|---|---|"]
    for vn in ("full", "narrow_Y", "broad_YU"):
        s = out["variants"][vn]["_summary"]
        L.append("| %s | %s | [%.2f, %.2f] | %d | %.4f | [%.4f, %.4f] | %s-%s %.4f | [%.4f, %.4f] |" % (
            vn, "%.2f" % s["range_factor"] if s["range_factor"] else "undefined", *s["range_factor_ci_conditional"], s["n_undefined"],
            s["abs_range"], *s["abs_range_ci"], s["highest"], s["lowest"], s["highest_minus_lowest"], *s["highest_minus_lowest_ci"]))
    L += ["", "## Easy negatives (cells where all replicates answered false; 80 cells per model)", "",
          "| model | unanimous-negative | share | unanimous-positive | discordant | incomplete | UN in N cells | UN in Y cells | UN in U cells |", "|---|---|---|---|---|---|---|---|---|"]
    for l, e in out["easy_negatives"].items():
        L.append("| %s | %d | %.4f | %d | %d | %d | %d/%d | %d/%d | %d/%d |" % (
            l, e["unanimous_negative"], e["share_unanimous_negative"], e["unanimous_positive"], e["discordant"], e["incomplete"],
            e["status_N"]["unanimous_negative"], e["status_N"]["cells"], e["status_Y"]["unanimous_negative"], e["status_Y"]["cells"],
            e["status_U"]["unanimous_negative"], e["status_U"]["cells"]))
    L += ["", "## Per-cell reasons", ""]
    for v in canon:
        L.append("- %s: " % v + "; ".join("%s=%s (%s)" % (a, out["matrix"][v][a]["status"], out["matrix"][v][a]["reason"]) for a in ACTIONS))
    open(OUT_M, "w", encoding="utf-8").write("\n".join(L) + "\n")


if __name__ == "__main__":
    main()
