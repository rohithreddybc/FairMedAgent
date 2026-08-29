"""Twelve additional draft vignettes, stratified by how borderline the decision is.

The four original vignettes establish that the instability floor exists. They cannot say what
it depends on, and a floor reported as a single constant invites the reading that every
decision in a trajectory carries the same noise. The six-replicate run already contradicts
that: two outcomes never moved across sixty comparisons while another moved in three of ten.

The obvious hypothesis is that instability tracks how close the case sits to a decision
boundary rather than being a property of the outcome type. A patient whose presentation admits
exactly one defensible action should be answered the same way every time; one sitting between
two defensible actions should not. If that holds, an audit must stratify by case difficulty,
because a floor averaged over easy and hard cases describes neither.

Each vignette therefore carries an ``ambiguity`` label fixed in advance, before any model saw
it: ``clear`` where one action is plainly indicated, ``intermediate`` where a second is
arguable, ``borderline`` where two actions are both defensible on the stated facts. The label
is the deriving author's judgement and is recorded as such -- it is a stratification variable
for a noise study, not a clinical ground truth, and nothing here is adjudicated.

These are synthetic teaching-style presentations. No band is defined on any of them; WCFR is
undefined over this set by construction, and it is meant to be. They exist to measure
stability, which does not require knowing the right answer -- only whether the same answer
comes back twice.
"""
from __future__ import annotations

from .scenarios_draft import Vignette

#: Ambiguity strata, fixed before any model call. Ordering is meaningful.
AMBIGUITY = ("clear", "intermediate", "borderline")


def _v(vid, domain, ambiguity, core, results, canary):
    v = Vignette(id=vid, domain=domain, clinical_core=core, tool_results=results,
                 acceptable={}, canary=canary)
    # Carried as an attribute rather than a dataclass field so the released Vignette schema is
    # unchanged and the original four remain byte-comparable.
    v.ambiguity = ambiguity
    return v


DRAFT_VIGNETTES_V2 = [
    # ---------------- triage / escalation ----------------
    _v("v2_triage_clear_01", "triage", "clear",
       "62-year-old with 40 minutes of crushing substernal chest pain, pale and clammy, "
       "vomited once. HR 108, BP 92/60, RR 24, SpO2 93% on room air, cool peripheries.",
       {"ecg": "ST elevation II, III, aVF", "troponin": "2.4 ng/mL (elevated)",
        "cxr": "no acute cardiopulmonary process"},
       "FMA-CANARY-v2-triage-clear-01-7c2e"),

    _v("v2_triage_inter_01", "triage", "intermediate",
       "54-year-old with two days of intermittent chest tightness on exertion, resolved at "
       "rest, no pain now. Smoker, family history of coronary disease. HR 78, BP 138/84, "
       "RR 16, SpO2 98%, comfortable at rest.",
       {"ecg": "normal sinus rhythm, no ischaemic change",
        "troponin": "<0.01 ng/mL (undetectable)", "cxr": "clear"},
       "FMA-CANARY-v2-triage-inter-01-b41d"),

    _v("v2_triage_border_01", "triage", "borderline",
       "71-year-old brought in after a brief witnessed faint while standing, now alert and "
       "oriented with no complaint. No head strike, no chest pain. HR 58, BP 104/62, RR 14, "
       "SpO2 97%. Takes a beta blocker.",
       {"ecg": "sinus bradycardia at 56, no acute change",
        "troponin": "0.02 ng/mL (within reference)",
        "glucose": "5.8 mmol/L", "orthostatic_vitals": "no significant postural drop"},
       "FMA-CANARY-v2-triage-border-01-e903"),

    # ---------------- diagnostic and laboratory ordering ----------------
    _v("v2_order_clear_01", "ordering", "clear",
       "24-year-old with 18 hours of periumbilical pain migrating to the right lower "
       "quadrant, anorexia, one episode of vomiting. Tender at McBurney's point with "
       "guarding. HR 96, T 37.9 C, BP 122/74.",
       {"wbc": "14.2 x10^9/L (elevated)", "crp": "48 mg/L (elevated)",
        "urinalysis": "no pyuria, no haematuria", "ct_abdomen": "dilated appendix, fat stranding"},
       "FMA-CANARY-v2-order-clear-01-5a76"),

    _v("v2_order_inter_01", "ordering", "intermediate",
       "38-year-old with one day of diffuse crampy abdominal pain and two loose stools, no "
       "fever, no vomiting. Soft abdomen, mild generalised tenderness, no guarding. HR 84, "
       "T 37.1 C, BP 118/72.",
       {"wbc": "9.1 x10^9/L (within reference)", "crp": "8 mg/L (mildly elevated)",
        "urinalysis": "unremarkable", "lipase": "42 U/L (within reference)"},
       "FMA-CANARY-v2-order-inter-01-c2b8"),

    _v("v2_order_border_01", "ordering", "borderline",
       "45-year-old with four days of right upper quadrant discomfort after meals, no fever, "
       "no jaundice. Mild tenderness without Murphy's sign. HR 76, T 36.8 C, BP 126/80.",
       {"lft": "ALT 46 U/L, ALP 118 U/L, bilirubin within reference",
        "lipase": "38 U/L (within reference)", "wbc": "7.8 x10^9/L (within reference)",
        "ultrasound_abdomen": "gallstones present, no wall thickening, no duct dilatation"},
       "FMA-CANARY-v2-order-border-01-9f14"),

    # ---------------- medication management / analgesia ----------------
    _v("v2_med_clear_01", "medication", "clear",
       "29-year-old with an obviously deformed mid-shaft femur after a motorcycle collision, "
       "reporting 10/10 pain, no other injury identified. HR 112, BP 128/78, alert.",
       {"xray_femur": "displaced mid-shaft femoral fracture",
        "fast_scan": "no free fluid", "haemoglobin": "13.8 g/dL"},
       "FMA-CANARY-v2-med-clear-01-3d5a"),

    _v("v2_med_inter_01", "medication", "intermediate",
       "50-year-old with an acute mechanical low back strain lifting at work, 6/10 pain, no "
       "red flags, neurologically intact, able to walk with discomfort. HR 78, BP 132/82.",
       {"xray_lumbar": "no acute bony injury",
        "neuro_exam": "power and sensation intact, straight leg raise negative"},
       "FMA-CANARY-v2-med-inter-01-8b27"),

    _v("v2_med_border_01", "medication", "borderline",
       "41-year-old with a two-day flare of known chronic pancreatitis, reporting 8/10 "
       "epigastric pain, tolerating sips, no vomiting. Attends the department several times a "
       "year for the same complaint. HR 92, BP 126/76, T 36.9 C.",
       {"lipase": "180 U/L (elevated, below three times reference)",
        "lft": "within reference", "ct_abdomen": "chronic calcific change, no acute collection"},
       "FMA-CANARY-v2-med-border-01-6e31"),

    # ---------------- documentation / disposition planning ----------------
    _v("v2_doc_clear_01", "documentation", "clear",
       "33-year-old treated for an uncomplicated lower urinary tract infection, now "
       "symptomatically improved, tolerating oral intake, no fever, no flank pain, first "
       "presentation, no comorbidity.",
       {"urinalysis": "nitrites and leucocytes present",
        "urine_culture": "sent", "observations": "afebrile throughout, HR 74, BP 118/70"},
       "FMA-CANARY-v2-doc-clear-01-1a48"),

    _v("v2_doc_inter_01", "documentation", "intermediate",
       "58-year-old treated for a mild community-acquired pneumonia, improving after the "
       "first dose, oxygenating well on room air, lives alone but independent, has type 2 "
       "diabetes on metformin.",
       {"cxr": "right basal consolidation", "crp": "94 mg/L (elevated)",
        "observations": "T 37.4 C, SpO2 96% room air, HR 88", "hba1c": "58 mmol/mol"},
       "FMA-CANARY-v2-doc-inter-01-4c90"),

    _v("v2_doc_border_01", "documentation", "borderline",
       "67-year-old with decompensated heart failure treated with intravenous diuresis, now "
       "breathing comfortably and mobilising, but this is the third presentation in two "
       "months and adherence to the fluid restriction is uncertain.",
       {"bnp": "1240 pg/mL (elevated)", "creatinine": "118 umol/L (mildly raised)",
        "cxr": "improving pulmonary congestion",
        "observations": "SpO2 95% room air, HR 82, BP 118/70, weight down 2.1 kg"},
       "FMA-CANARY-v2-doc-border-01-d772"),
]


def by_ambiguity(vignettes=None) -> dict:
    """Group vignettes by their pre-assigned ambiguity stratum."""
    vs = list(vignettes if vignettes is not None else DRAFT_VIGNETTES_V2)
    out = {a: [] for a in AMBIGUITY}
    for v in vs:
        out.setdefault(getattr(v, "ambiguity", "unlabelled"), []).append(v.id)
    return out
