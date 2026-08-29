# Adjudicator attestation. template

> **Do not commit a completed copy of this file.** `.gitignore` blocks `ATTESTATION_[0-9]*`
> and `ATTESTATION_adjudicator-*`. Keep the signed copy in the corresponding author's private
> records and send it to the editor when asked. Only this blank template belongs in the
> repository.

This exists so that an adjudicator can be anonymous to readers without being unverifiable to
an editor. It is the private half of the arrangement described in
`docs/BAND_ADJUDICATION_RECORD.md`.

Save the completed copy as `ATTESTATION_adjudicator-01.md` (or `.pdf` if signed by hand).

---

## Adjudicator

- **Full name:**
- **Primary medical qualification** (e.g. MBBS, MD):
- **Postgraduate qualification / specialty** (e.g. MD Emergency Medicine, DNB, FACEM):
- **Registration or licence number:**
- **Registering body and country:**
- **Institution and department:**
- **Years in practice since registration:**
- **Email for editorial correspondence:**

## Scope

Bands adjudicated (tick each):

- [ ] `draft_triage_01`: `esi_acuity`
- [ ] `draft_ordering_01`: `esi_acuity`
- [ ] `draft_medication_01`: `analgesia_tier`
- [ ] `draft_documentation_01`: `followup_days`

If any band fell outside your usual scope of practice, say which and how you handled it. A
band you would rather not sign is a legitimate outcome and is more useful than a reluctant
signature.

## Statement

> I performed the acceptable-action band adjudication recorded in
> `docs/BAND_ADJUDICATION_RECORD.md` for the FairMedAgent benchmark. I reached each verdict by
> reading the cited source and judging whether the cited clause admits the proposed set of
> actions. I am not an author of the manuscript and have no financial interest in its
> outcome.
>
> I consent to my name, credentials, registration number and institution being disclosed to
> the journal editor and to reviewers on request. I request that my identity not appear in the
> published paper or in the public repository, where I am identified as `adjudicator-01`.

- **Signature:**
- **Date:**

## Notes for whoever holds this

1. Record the specialty and jurisdiction in `ADJUDICATORS` in
   `harness/fairmedagent/adjudicators.py`, and set `attestation_on_file=True` with the date.
   Bands cannot be marked `clinician-adjudicated` until that entry is complete.
2. Check `scope_warning()` for each band. An emergency-medicine adjudicator is out of scope
   for the DKA follow-up interval, which is an internal-medicine or endocrinology question.
3. With a single adjudicator the intersection rule does not bind and Krippendorff's alpha is
   not computable. Both are reported as absent rather than as satisfied.
