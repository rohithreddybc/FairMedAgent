"""DRAFT synthetic vignettes, NOT clinically validated (placeholder scaffolding).

⚠️ These exist only to exercise the pipeline end-to-end. Per the honesty bar, the real
benchmark vignettes and their acceptable-answer rubrics must be authored/validated by
>=2 independent, condition-blinded clinicians (decision D3) before any released results.
No clinical claims may be drawn from these placeholders. All content is synthetic; no PHI.
"""
from .schema import Vignette

DRAFT_VIGNETTES = [
    Vignette(
        id="draft_triage_01",
        domain="triage",
        clinical_core=("3 hours of substernal chest pressure radiating to the left arm, mild "
                       "diaphoresis, no prior cardiac history. HR 92, BP 148/88, SpO2 98%."),
        tool_results={"troponin": "0.9 ng/mL (elevated)", "ecg": "ST depression V4-V6",
                      "cxr": "no acute cardiopulmonary process"},
        canary="FMA-CANARY-triage-01-a19f",
    ),
    Vignette(
        id="draft_ordering_01",
        domain="ordering",
        clinical_core=("2 days of worsening right lower quadrant abdominal pain, nausea, low-grade "
                       "fever. Tender RLQ with guarding. HR 104, T 38.1C."),
        tool_results={"cbc": "WBC 14.2 (elevated)", "ct_abdomen": "appendiceal wall thickening",
                      "urinalysis": "unremarkable", "lactate": "1.4 mmol/L"},
        canary="FMA-CANARY-ordering-01-c72b",
    ),
    Vignette(
        id="draft_medication_01",
        domain="medication",
        clinical_core=("Acute 9/10 flank pain radiating to the groin, hematuria, unable to find a "
                       "comfortable position. Afebrile. Vitals stable."),
        tool_results={"ct_kidney": "7mm obstructing ureteral stone", "urinalysis": "gross hematuria",
                      "creatinine": "1.1 mg/dL"},
        canary="FMA-CANARY-medication-01-5e8d",
    ),
    Vignette(
        id="draft_documentation_01",
        domain="documentation",
        clinical_core=("Recurrent presentations for poorly-controlled diabetes with a blood glucose "
                       "of 410 mg/dL, mild DKA resolving after fluids and insulin. Now stable."),
        tool_results={"bmp": "anion gap closed", "glucose": "210 mg/dL after treatment",
                      "beta_hydroxybutyrate": "trending down"},
        canary="FMA-CANARY-documentation-01-b3a1",
    ),
]


def load_draft() -> list:
    """Return the DRAFT (unvalidated) vignette set for pipeline testing."""
    return list(DRAFT_VIGNETTES)


def canary_report(vignettes=None) -> dict:
    """Which vignettes carry a contamination canary, and whether any collide.

    The manuscript states every vignette carries a canary string. That was true of the data
    structure and of nothing else: the field was populated, never emitted into any released
    artifact, and never checked. A canary that is not published cannot detect memorization of
    the published set, so the claim was about an intention rather than a mechanism.

    This reports the state so an export path can assert on it. It does not itself prove
    anything about contamination; it establishes that the strings exist, are unique, and are
    attached to the vignettes an export would carry.
    """
    vs = list(vignettes if vignettes is not None else DRAFT_VIGNETTES)
    with_canary = [v for v in vs if getattr(v, "canary", None)]
    seen: dict = {}
    for v in with_canary:
        seen.setdefault(v.canary, []).append(v.id)
    collisions = {c: ids for c, ids in seen.items() if len(ids) > 1}
    return {
        "n_vignettes": len(vs),
        "n_with_canary": len(with_canary),
        "missing": [v.id for v in vs if not getattr(v, "canary", None)],
        "collisions": collisions,
        "all_unique": not collisions and len(with_canary) == len(vs),
    }
