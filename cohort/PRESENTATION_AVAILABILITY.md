# What Synthea can and cannot supply for this benchmark

Surveyed against Synthea v4.0.0, seed `20260827`, 458 generated patients
(29,340 encounters, 16,406 condition records, 359,339 observations), and cross-checked against
the 536 disease modules shipped inside the JAR so that the conclusions do not rest on one
sample.

In summary, Synthea solves the provenance problem and the authoring problem only slightly: it
gives a starting distribution, not finished cases.

## Presentations, against the four draft vignettes

| vignette | presentation required | module | verdict |
|---|---|---|---|
| `draft_ordering_01` | RLQ pain, suspected appendicitis | `appendicitis` | available |
| `draft_triage_01` | undifferentiated chest pain at triage | `myocardial_infarction` | partial |
| `draft_medication_01` | renal colic, obstructing ureteric stone | none | **absent** |
| `draft_documentation_01` | resolving mild DKA | none | **absent** |

Three findings behind that table.

**No urolithiasis module exists.** Searching all 536 module names for colic, calculus, stone,
urolith and related terms returns `gallstones` and nothing renal; the condition export contains
`Gallbladder calculus` and no ureteric or kidney stone at any frequency. This is the costly one,
because `draft_medication_01` is the construct-validity anchor for pain-treatment
disparity. The anchor cannot be built from Synthea as the vignette is currently written.

**No ketoacidosis module exists.** Synthea models type 2 diabetes richly, and the survey
returned 362 diabetes-related condition rows covering retinopathy, nephropathy, neuropathy and
proteinuria. All of it is chronic course. Acute hyperglycaemic crisis is not simulated, so
`draft_documentation_01` has no substrate either.

**Synthea emits diagnoses, not presentations.** This is the structural point and it outlasts any
particular module. `conditions.csv` records `Myocardial infarction (disorder)`; it does not
record "chest pressure with radiation to the left arm, mild diaphoresis, ECG pending." The
benchmark measures the decision taken *before* the diagnosis is known, which is precisely the
information Synthea's export has already resolved away. Even where a module exists, the
pre-diagnosis presentation has to be authored.

## What Synthea does supply, and it is not nothing

- **Fixture value distributions.** Heart rate (n=6,237), respiratory rate (6,237), blood
  pressure (6,400), temperature (483), leukocytes (1,343 by automated count), troponin (228),
  CBC and BMP panels. Enough to check a hand-chosen fixture against a generated distribution
  instead of against intuition. `tools/fixture_distributions.py` does this.
- **Real code systems.** SNOMED-CT, LOINC, RxNorm throughout, so vignettes and the FHIR fixture
  layer speak the vocabulary a clinical reviewer expects.
- **Plausible comorbidity and medication co-occurrence** for background history.
- **Clean provenance.** No real patient lineage, Apache 2.0, no redistribution permission needed
  from anyone. This was the reason for the switch and it holds completely.

Absent: lipase, urinalysis. Lactate is present but thin (n=43).

## Options

The survey bears on how the work is divided between Synthea and authored vignettes. Two options exist.

1. **Keep the four presentations, use Synthea for substrate only.** Vignettes stay
   author-written and clinician-adjudicated; Synthea supplies value distributions, code systems
   and background history. The clinical authoring burden is unchanged.

2. **Re-choose presentations toward what Synthea models.** Appendicitis stays. Biliary colic
   from `gallstones` could replace renal colic as the analgesia anchor: it is a genuine acute
   severe pain presentation where the NSAID-versus-opioid tiering decision is live, and the
   pain-treatment disparity literature the paper cites is about analgesia broadly rather than
   about stones specifically. This would change the construct-validity anchor, which is a
   substantive change to the instrument and needs clinical review.

Option 1 changes no design commitment. Option 2 is cheaper in authoring and more expensive in
review.

## Caveat on the distribution check

`tools/fixture_distributions.py` compares a proposed value against every generated encounter,
and those are predominantly wellness and ambulatory visits. A vignette sits at a decision
threshold by construction, so a high percentile there is expected and is not evidence of
implausibility. The tool prints this on every run. It establishes that a value lies on the
generator's scale; it does not establish an emergency-department reference range, and Synthea
cannot provide one.
