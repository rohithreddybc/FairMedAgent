# Where the acceptable-action band comes from

**Decision date:** 2026-08-22
**Question:** can FairMedAgent produce a defensible `A(v)` without recruiting a clinician panel?
**Answer:** yes, by changing the band's *source* rather than removing it.

---

## The problem this solves

WCFR conditions on both demographic variants falling inside `A(v)`, the set of clinically
acceptable actions. The protocol as written required at least two blinded clinicians to
generate that set. None have been recruited, every draft vignette carries `acceptable = {}`,
and so WCFR returns NA with denominator 0 on every contrast. That single dependency blocks
Section V, blocks submission, and blocks papers 13 and 14 downstream.

The dependency was never on clinicians as such. It was on the band being *defensible*.

## Three routes, and why one wins

**Guideline-derived bands — adopted.** `A(v)` is derived from published, citable decision
rules, and the derivation is recorded per band. ESI Handbook v4 for acuity. WHO analgesic
ladder and ACEP pain guidance for analgesia tier. Established workup pathways for ordering.
Discharge guidance for follow-up interval. The band becomes "the actions this published rule
admits for this presentation," which is a claim a reviewer can check against a document
rather than take on trust.

This is not a weaker substitute for clinician judgment. On the specific axis reviewers
attacked hardest it is stronger: the second-round scrutiny flagged band width as an
unconstrained researcher degree of freedom, and a guideline fixes the width by reference to
something outside the study. It also removes the circularity worry, since the rule was written
without reference to this benchmark.

Its real cost, stated plainly: published guidelines do not cover every action in the trajectory,
and mapping a vignette to a band still takes judgment. The difference is that the judgment is
written down, attributed to a source, and contestable.

**Model-panel bands — rejected.** Using an LLM panel to define the band for a benchmark that
measures LLM bias is circular in a way no amount of methodology can repair, and one sentence
in a review would end it.

**Dropping WCFR — rejected.** It is the paper's contribution under the framing already settled.
Removing it leaves a fixed-trajectory harness and a flip rate, which is a smaller paper than
this work deserves.

## The adopted model: derive, then adjudicate

1. **Derive** each band from a named guideline, recording the source, the clause, and the
   reasoning as structured fields alongside the band itself.
2. **Adjudicate** with the one clinical co-author who exists. Their role is to review and
   sign off on the guideline-to-band mapping and to flag anything clinically wrong, not to
   generate bands from scratch. That is hours of their time rather than weeks of recruitment,
   and it is a real contribution rather than a courtesy authorship.
3. **Report honestly.** Inter-rater agreement is reported only where two or more raters
   actually rated. Where there is one adjudicator, say so. Where a band has no guideline
   support and rests on the adjudicator's judgment alone, mark it and report how many bands
   are in that category.

## What this changes in the manuscript

- The band is described as guideline-derived and clinician-adjudicated, not clinician-generated.
- "Clinician-validated" as a blanket descriptor goes. It was already the subject of a review
  finding for being asserted in the present tense.
- Krippendorff's alpha is reported for the subset with two or more raters, and the subset size
  is printed next to it. If that subset is empty, alpha is not reported at all rather than
  reported as unavailable.
- The band-width sensitivity analysis gains a natural third arm: guideline-strict, guideline-
  literal, and adjudicator-widened.

## Venue consequence, stated without spin

At an ML or FAccT-type venue this is unambiguously fine and arguably preferable, because
reproducibility beats panel provenance there.

At a clinical venue it is a named limitation. A reviewer may still want a multi-clinician
panel, and the honest response is that the band derivation is documented and auditable, one
clinician adjudicated it, and a larger panel is the obvious next step. That is a defensible
position. It is not the same as claiming a panel that does not exist.

## Status

The mechanism is implemented in the harness (`schema.Band`, `bands.py`). The four draft
vignettes carry provisional bands marked `provenance="author-derived"` and
`adjudicated=False`; they are for exercising the code path and must not be reported as
clinical ground truth. Nothing in Section V may cite them as validated until the adjudication
step has actually happened.


---

## Source verification, 2026-08-22 — all three provisional bands were wrong

The provisional bands were first written from recall, flagged as such, and then checked
against the literature. Every one of them needed correction, which is the strongest possible
argument for the `provenance` field existing at all.

**Analgesia (the construct-validity anchor).** The band admitted tier 3, a strong opioid, as
an acceptable initial choice for renal colic. Current emergency-medicine guidance is
multimodal non-opioid first line — oral acetaminophen, IV ketorolac absent contraindication,
fluid bolus — with opioids held as rescue when first- and second-line therapy fail. The
vignette documents no such failure. Corrected to {1, 2}. Had this shipped, a demographic
flip that escalated a patient straight to a strong opioid would have been scored as
guideline-concordant.

**Follow-up interval.** The band capped at 14 days on the reasoning that a longer interval is
the documented harm direction. The diabetes standards advise outpatient follow-up within one
month of discharge, so a 30-day interval is concordant. Corrected to {min 1, max 30}. The old
band would have scored guideline-concordant care as a clinical error and dropped that vignette
out of the WCFR denominator entirely. A tighter band may still be right for a patient with
recurrent presentations, but that is an adjudicator's judgement and not a reading of the text.

**ESI citation.** Named edition 4 when the handbook is now in its fifth. The criterion relied
on carries forward, so the band itself stands; the citation was updated.

The lesson is in the code: `provenance` starts at `author-derived` and only becomes
`guideline-derived` once someone has actually opened the guideline. Two of these three errors
would have biased the headline estimand, and neither would have been visible in a passing test
suite.
