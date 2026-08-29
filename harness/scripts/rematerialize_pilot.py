"""Re-materialize the preliminary pilot through the RELEASED runner, for provenance.

Why this exists
---------------
The original pilot artifact (``experiments/pilot/haiku_pilot_raw.json``) was produced by an
ad-hoc agent workflow, not by ``fairmedagent.runner.run_vignette``. Its per-trajectory
records therefore carry no ``model`` and no ``scaffold`` field, which the released
``Trajectory`` dataclass requires. That gap means an independent party running the released
harness would not reproduce the shipped pilot, so the reproducibility statement in the paper
could not be substantiated as written.

What this script does -- and does NOT do
----------------------------------------
It replays the *recorded model responses* through the released agentic loop, so the
trajectory objects, the step ordering, and the deterministic environment step are all
produced by the code that ships. The output is schema-conformant and auditable.

It does **NOT** re-query the model. The model outputs are the ones recorded in the original
run. This is a re-materialization for provenance, not an independent replication, and the
emitted artifact says so in its ``provenance`` block. Anything downstream that treats this
as a fresh run is misreading it.

The replay also acts as a differential test between the workflow that produced the pilot and
the harness that was released: any step where the released loop disagrees with the recording
is reported as a divergence rather than silently overwritten.

Usage:  python harness/scripts/rematerialize_pilot.py [in.json] [out.json]
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fairmedagent.runner import run_vignette  # noqa: E402
from fairmedagent.scenarios_draft import DRAFT_VIGNETTES  # noqa: E402
from fairmedagent.schema import MODEL_CALL_STEPS  # noqa: E402
from fairmedagent.conditions import standard_conditions  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_IN = os.path.join(ROOT, "experiments", "pilot", "haiku_pilot_raw.json")
DEFAULT_OUT = os.path.join(ROOT, "experiments", "pilot", "haiku_pilot_trajectories.json")

# The original workflow artifact records this at the top level only, never per trajectory.
MODEL_NAME = "claude-haiku-4-5"
# Not recorded anywhere in the original artifact; asserted from the pilot protocol (direct,
# no chain-of-thought, no deliberation panel). Flagged as asserted, not observed.
SCAFFOLD = "C0"


def replay_fn(recorded_actions: dict):
    """Return a ``model_fn`` that serves the recorded action for each step, in order."""
    def fn(prompt: str, schema: dict) -> dict:
        step = fn._queue.pop(0)
        return recorded_actions.get(step, {})
    fn._queue = list(MODEL_CALL_STEPS)
    return fn


def main(src: str = DEFAULT_IN, dst: str = DEFAULT_OUT) -> int:
    raw = json.load(open(src, encoding="utf-8"))
    result = raw.get("result", raw)
    recorded = result.get("trajectories", [])
    vignettes = {v.id: v for v in DRAFT_VIGNETTES}
    conditions = {c.id: c for c in standard_conditions()}
    # The pilot artifact predates a rename in the released conditions module: it records
    # e.g. "black_man_private" where the shipped standard_conditions() now emits
    # "race_black_man_private". Alias rather than drop, and report the drift.
    id_drift = {}
    for cid in {t["condition_id"] for t in recorded}:
        if cid not in conditions:
            for alias in (f"race_{cid}",):
                if alias in conditions:
                    conditions[cid] = conditions[alias]
                    id_drift[cid] = alias

    out, divergences = [], []
    for rec in recorded:
        vid, cid = rec["vignette_id"], rec["condition_id"]
        v, c = vignettes.get(vid), conditions.get(cid)
        if v is None or c is None:
            divergences.append({"vignette_id": vid, "condition_id": cid,
                                "kind": "unknown_vignette_or_condition"})
            continue

        traj = run_vignette(v, c, replay_fn(rec["actions"]), scaffold=SCAFFOLD,
                            model_name=MODEL_NAME)
        produced = traj.actions()

        # Differential check: the environment step is computed by the released harness from
        # the vignette fixture, while the original workflow resolved ordered items its own
        # way. Report, never silently reconcile.
        rec_results = rec["actions"].get("results") or {}
        new_results = (produced.get("results") or {}).get("results", {})
        if rec_results != new_results:
            resolved_before = sum(1 for x in rec_results.values()
                                  if x != "pending / not resulted")
            resolved_after = sum(1 for x in new_results.values()
                                 if x != "pending / not resulted")
            divergences.append({
                "vignette_id": vid, "condition_id": cid, "kind": "environment_step_mismatch",
                "orderables_resolved_in_original_workflow": resolved_before,
                "orderables_resolved_by_released_harness": resolved_after,
            })

        out.append({
            "vignette_id": traj.vignette_id,
            "condition_id": traj.condition_id,
            "model": traj.model,
            "scaffold": traj.scaffold,
            "domain": rec.get("domain"),
            "is_ref": rec.get("is_ref", False),
            "model_calls": traj.total_model_calls(),
            "actions": produced,
        })

    artifact = {
        "provenance": {
            "kind": "re-materialization",
            "produced_by": "harness/scripts/rematerialize_pilot.py via fairmedagent.runner.run_vignette",
            "source_artifact": os.path.relpath(src, ROOT).replace("\\", "/"),
            "model_responses": "REPLAYED from the original recorded run; the model was NOT re-queried",
            "independent_replication": False,
            "model_name_provenance": "recorded at top level of the source artifact",
            "scaffold_provenance": "NOT recorded in the source artifact; C0 asserted per the pilot protocol",
            "warning": "Preliminary pilot on DRAFT, non-clinician-validated vignettes. Not a scientific result.",
        },
        "counts": {
            "trajectories": len(out),
            "expected_cells": len(vignettes) * len({t["condition_id"] for t in recorded}),
            "model_calls_successful": sum(t["model_calls"] for t in out),
            "model_calls_attempted": (len(vignettes)
                                      * len({t["condition_id"] for t in recorded})
                                      * len(MODEL_CALL_STEPS)),
        },
        "condition_id_drift": id_drift,
        "divergences_from_released_harness": divergences,
        "trajectories": out,
    }
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    with open(dst, "w", encoding="utf-8") as fh:
        json.dump(artifact, fh, indent=1)

    print(f"wrote {os.path.relpath(dst, ROOT)}")
    print(f"  trajectories:            {artifact['counts']['trajectories']} "
          f"(expected {artifact['counts']['expected_cells']})")
    print(f"  model calls successful:  {artifact['counts']['model_calls_successful']} "
          f"of {artifact['counts']['model_calls_attempted']} attempted")
    print(f"  condition-id drift:      {id_drift or 'none'}")
    print(f"  divergences:             {len(divergences)}")
    for d in divergences[:6]:
        print("   -", d)
    return 0


if __name__ == "__main__":
    sys.exit(main(*(sys.argv[1:3] or [DEFAULT_IN, DEFAULT_OUT])))
