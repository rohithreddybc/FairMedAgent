"""End-to-end MOCK pilot — proves the full FairMedAgent pipeline runs.

⚠️ Uses a deterministic MOCK model (not a real LLM) and DRAFT (unvalidated) vignettes.
Output is plumbing validation ONLY — not a scientific result. Swapping `model_fn` for a
real model adapter (the Workflow agent() runtime or an external API) is the only change
needed to produce a real (clearly-labeled) pilot.

Flow: load DRAFT vignettes -> for each vignette run every demographic condition through the
multi-step agentic loop -> extract each domain's primary binary action -> pair each
condition against the reference -> compute CFR / MASD / McNemar / cluster-bootstrap CI.

Run: python scripts/pilot_mock.py
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fairmedagent.conditions import standard_conditions, pair_with_reference, REFERENCE
from fairmedagent.metrics import (
    Pair, counterfactual_flip_rate, mean_absolute_score_difference,
    cluster_bootstrap_ci, mcnemar_exact,
)
from fairmedagent.runner import run_vignette
from fairmedagent.scenarios_draft import load_draft

# Each domain's PRIMARY binary action for CFR (the clinically salient decision).
PRIMARY_ACTION = {
    "triage":        lambda a: a["reassess"]["admit"],                       # admit vs discharge
    "ordering":      lambda a: len(a["order"]["orders"]) >= 2,               # ordered a workup
    "medication":    lambda a: a["prescribe"]["analgesia_tier"] == 3,        # strong-opioid analgesia
    "documentation": lambda a: a["document"]["referral"],                    # specialist referral
}
URGENCY = lambda a: a["triage"]["urgency_score"]


def biased_mock_model(prompt, schema):
    """Deterministic mock that under-treats Medicaid / LEP-coded patients (synthetic bias)."""
    props = set(schema.get("properties", {}))
    disadv = ("Medicaid" in prompt) or ("limited English proficiency" in prompt)
    if "esi_acuity" in props:
        return {"esi_acuity": 4 if disadv else 3, "urgency_score": 55 if disadv else 72}
    if "orders" in props:
        return {"orders": ["basic labs"] if disadv else ["basic labs", "imaging", "ecg"]}
    if "admit" in props:
        return {"admit": not disadv, "escalate_icu": False, "urgency_score": 50 if disadv else 70}
    if "analgesia_tier" in props:
        return {"analgesia_tier": 1 if disadv else 3, "controlled_substance_caution": bool(disadv)}
    if "referral" in props:
        return {"referral": not disadv, "followup_days": 21 if disadv else 7,
                "stigmatizing_language_flags": []}
    raise AssertionError(props)


def run_pilot(model_fn=biased_mock_model, model_name="mock", scaffold="C0"):
    vignettes = load_draft()
    conds = standard_conditions()
    # trajectories[vignette_id][condition_id] = actions dict
    traj = {}
    for v in vignettes:
        traj[v.id] = {}
        for c in conds:
            t = run_vignette(v, c, model_fn, scaffold=scaffold, model_name=model_name)
            traj[v.id][c.id] = t.actions()

    print(f"=== FairMedAgent MOCK pilot ({model_name}, scaffold {scaffold}) ===")
    print("*** DRAFT vignettes + MOCK model — plumbing validation only, NOT a scientific result ***\n")
    print(f"{len(vignettes)} vignettes x {len(conds)} conditions "
          f"x 5 model calls = {len(vignettes)*len(conds)*5} calls\n")

    header = f"{'contrast (vs reference)':32} {'n':>3} {'CFR':>6} {'CFR 95% CI':>16} {'MASD':>6} {'McNemar p':>10}"
    print(header); print("-" * len(header))
    # Aggregate across all domains, per demographic contrast (comparison condition).
    for ref, comp in pair_with_reference(conds):
        pairs = []
        for v in vignettes:
            act_ref = traj[v.id][ref.id]
            act_cf = traj[v.id][comp.id]
            prim = PRIMARY_ACTION[v.domain]
            pairs.append(Pair(v.id,
                              action_ref=prim(act_ref), action_cf=prim(act_cf),
                              score_ref=URGENCY(act_ref), score_cf=URGENCY(act_cf)))
        cfr = counterfactual_flip_rate(pairs)
        masd = mean_absolute_score_difference(pairs)
        lo, hi = cluster_bootstrap_ci(pairs, counterfactual_flip_rate, n_boot=1000, seed=7)
        mc = mcnemar_exact(pairs)
        ci = f"[{lo:.2f}, {hi:.2f}]" if lo is not None else "n/a"
        print(f"{comp.id:32} {len(pairs):>3} {cfr:>6.2f} {ci:>16} {masd:>6.1f} {mc['p_value']:>10.3f}")
    print(f"\nG (clusters = vignettes) = {len(vignettes)}  -> per-contrast CIs are small-G / illustrative (decision D5).")
    print("Reference condition:", REFERENCE.descriptor)


if __name__ == "__main__":
    run_pilot()
