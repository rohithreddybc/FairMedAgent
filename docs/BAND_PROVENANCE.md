# Where the acceptable-action band comes from

The within-range counterfactual flip rate conditions on both demographic variants falling
inside `A(v)`, the set of clinically acceptable actions for vignette `v`. This document
records how each band is sourced.

## Sources considered

**Guideline-derived bands (adopted).** `A(v)` is derived from published, citable decision
rules, and the derivation is recorded per band: ESI Handbook for acuity, the WHO analgesic
ladder and ACEP pain guidance for analgesia tier, established workup pathways for ordering,
and discharge guidance for follow-up interval. The band is then the set of actions the
published rule admits for the presentation, which can be checked against a document. The
width of the band is fixed by reference to something outside the study. Published guidelines
do not cover every action in a trajectory, and mapping a vignette to a band still requires
judgment. That judgment is written down, attributed to a source and open to challenge.

**Model-panel bands (rejected).** Using an LLM panel to define the band for a benchmark that
measures LLM bias is circular.

**Dropping the within-range condition (rejected).** Without it the harness reduces to a fixed
trajectory and an unconditioned flip rate.

## Procedure: derive, then adjudicate

1. Derive each band from a named guideline, recording the source, the clause and the reasoning
   as structured fields alongside the band.
2. Adjudicate: a licensed clinician reviews the guideline-to-band mapping and flags anything
   clinically wrong (see `ADJUDICATION_PROTOCOL.md`).
3. Report agreement honestly. Inter-rater agreement is reported only where two or more raters
   rated. Where there is one adjudicator, the report says so. Where a band has no guideline
   support and rests on the adjudicator's judgment alone, it is marked and counted.

The adjudicator's later verdicts, including amendments to these sets, are in
`BAND_ADJUDICATION_RECORD.md`.

Bands are described as guideline-derived and clinician-adjudicated, not clinician-generated.
The band-width sensitivity analysis has three arms: guideline-strict, guideline-literal and
adjudicator-widened.

## Implementation status

The mechanism is implemented in the harness (`schema.Band`, `bands.py`). The four draft
vignettes carry provisional bands marked `provenance="author-derived"` and
`adjudicated=False`. They exercise the code path and must not be reported as clinical ground
truth.

## Source verification of the provisional bands

The provisional bands were first written from recall and then checked against the literature.
All three required correction.

**Analgesia.** The band admitted tier 3, a strong opioid, as an acceptable initial choice for
renal colic. Current emergency-medicine guidance is multimodal non-opioid first line (oral
acetaminophen, IV ketorolac absent contraindication, fluid bolus), with opioids held as rescue
when first- and second-line therapy fail. The vignette documents no such failure. Corrected to
{1, 2}. With the earlier band, a demographic flip that escalated a patient directly to a strong
opioid would have been scored as guideline-concordant.

**Follow-up interval.** The band capped at 14 days on the reasoning that a longer interval is
the documented harm direction. The diabetes standards advise outpatient follow-up within one
month of discharge, so a 30-day interval is concordant. Corrected to {min 1, max 30}. With the
earlier band, guideline-concordant care would have been scored as a clinical error and the
vignette dropped from the denominator. A tighter band may be appropriate for a patient with
recurrent presentations, but that is an adjudicator's judgment rather than a reading of the
text.

**ESI citation.** The citation named edition 4 where the handbook is now in its fifth. The
criterion relied on carries forward, so the band stands; the citation was updated.

The `provenance` field starts at `author-derived` and becomes `guideline-derived` only after
the guideline has been consulted.
