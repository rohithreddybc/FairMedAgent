"""A1: are the rendered prompts for the reference and the rerender (null) control identical?

Compares, for every vignette and each of the five model-call steps, the full prompt text rendered
by the released runner (_context + step instruction) for the reference condition against the
rerender_control and against one demographic condition (black_woman_medicaid). A fixed synthetic
prior-step state is used so that the comparison isolates the condition (the real run carries each
trajectory's own answers). It also drives the real pilot_driver emit for step 1 and compares the
per-condition dispatch files (system instruction, schema, prompt text). Output: stdout + JSON.
    python audit_render_diff.py [out.json]
"""
import difflib, json, os, subprocess, sys, tempfile
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, ".."))
os.environ["FMA_VIGNETTE_SET"] = "v2"
import pilot_driver as pd
from fairmedagent.runner import _context, _STEP_INSTRUCTION
from fairmedagent.schema import MODEL_CALL_STEPS

vs, cs = pd._cells(True)
REF, NULL, DEM = "ref_white_man_private", "rerender_control", "black_woman_medicaid"
STATE = {"triage": {"esi_acuity": 3, "urgency_score": 50}, "order": {"orders": ["cbc", "ecg"]},
         "results": {"results": {"cbc": "normal", "ecg": "normal"}},
         "reassess": {"admit": False, "escalate_icu": False}}
ORDER = ["triage", "order", "results", "reassess", "prescribe", "document"]
def prompt(cid, vid, step):
    st = {k: STATE[k] for k in ORDER[:ORDER.index(step)] if k in STATE}
    return _context(cs[cid], vs[vid], "C0", st) + "\n\n" + _STEP_INSTRUCTION[step]
res = {"descriptor_ref": cs[REF].descriptor, "descriptor_null": cs[NULL].descriptor,
       "descriptor_dem": cs[DEM].descriptor, "n_vignettes": len(vs), "steps": list(MODEL_CALL_STEPS)}
ident = diff_null = diff_dem_other = 0; nulldiffs = []
for vid in sorted(vs):
    for step in MODEL_CALL_STEPS:
        a, b, d = prompt(REF, vid, step), prompt(NULL, vid, step), prompt(DEM, vid, step)
        if a.encode() == b.encode(): ident += 1
        else: diff_null += 1; nulldiffs.append((vid, step, list(difflib.unified_diff(a.splitlines(), b.splitlines(), lineterm=""))))
        # demographic: every differing line other than the Patient: line?
        la, ld = a.splitlines(), d.splitlines()
        other = [x for x in difflib.ndiff(la, ld) if x[:2] in ("+ ", "- ") and not x[2:].startswith("Patient:")]
        diff_dem_other += bool(other)
res.update(rendered_cells=len(vs) * len(MODEL_CALL_STEPS), null_byte_identical=ident, null_differs=diff_null,
           dem_differs_beyond_patient_line=diff_dem_other, null_diffs=[(v, s, d) for v, s, d in nulldiffs[:5]])
# real emit, step 1
with tempfile.TemporaryDirectory() as td:
    st = os.path.join(td, "state.json"); out = os.path.join(td, "p.json")
    subprocess.run([sys.executable, os.path.join(HERE, "pilot_driver.py"), "init", st, "1"], check=True, capture_output=True, env=dict(os.environ))
    subprocess.run([sys.executable, os.path.join(HERE, "pilot_driver.py"), "emit", st, out], check=True, capture_output=True, env=dict(os.environ))
    f = {c: json.load(open(os.path.join(td, "p__%s.json" % c), encoding="utf-8")) for c in (REF, NULL, DEM)}
    res["emit_step1"] = {"instruction_identical_ref_null": f[REF]["dispatch_instruction"] == f[NULL]["dispatch_instruction"],
                         "instruction_identical_ref_dem": f[REF]["dispatch_instruction"] == f[DEM]["dispatch_instruction"],
                         "schema_identical": f[REF]["schema"] == f[NULL]["schema"] == f[DEM]["schema"],
                         "n_prompts": [len(f[c]["prompts"]) for c in (REF, NULL, DEM)],
                         "prompt_text_identical_ref_null": [p["prompt"] for p in f[REF]["prompts"]] == [p["prompt"] for p in f[NULL]["prompts"]],
                         "vignette_order_identical": [p["vignette_id"] for p in f[REF]["prompts"]] == [p["vignette_id"] for p in f[NULL]["prompts"]],
                         "file_level_extra_diff": "condition_id and per-prompt integer cell ids / condition_id fields only (not shown to the model)"}
json.dump(res, open(sys.argv[1], "w", encoding="utf-8"), indent=1) if len(sys.argv) > 1 else None
print(json.dumps({k: v for k, v in res.items() if k != "null_diffs"}, indent=1)); print("null_diffs:", res["null_diffs"])
