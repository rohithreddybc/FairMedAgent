# Cohort provenance: resolving the MedAgentBench blocker

**Decision date:** 2026-08-22
**Supersedes:** the provenance permission in `ResearchPaper17-DatasetDescriptor/KEYSTONE-CONSTRAINT.md`
**Authority:** `STOP-BLOCKER-2026-07-18.md` (identical copies in papers 15, 16 and 17)

---

## The finding, restated

MedAgentBench's examples are "real patient cases that were deidentified and jittered," drawn
from Stanford's STARR clinical data warehouse. Its MIT licence covers the code, not the data,
and the paper states no IRB, HIPAA, consent, or data-use terms. Any cohort built from those
patient profiles is therefore not synthetic, and describing it as "synthetic, zero-PHI" would
be a misstatement in a manuscript, a deposit, and an outreach email simultaneously.

The blocker has been open since 2026-07-18 and its recommended resolution is unexecuted.

## Where paper 11 actually stands, verified

Direct inspection of the repository on 2026-08-22: **no MedAgentBench, FHIR, or STARR code or
data exists anywhere in it.** The four draft vignettes in `scenarios_draft.py` are hand-written
synthetic cases. `jiang2025medagentbench` appears in the bibliography as a related-work
citation only.

The manuscript makes four provenance claims: `entirely synthetic`, `zero-PHI`, and
`no protected health information` twice. **Every one of them is true today.** The exposure is
entirely prospective, and it materialises the moment the real vignette set is built from
MedAgentBench patient profiles.

This is the cheapest possible moment to decide, because nothing has to be undone.

## Decision: build the cohort with Synthea, cite MedAgentBench for schema only

This is option 3 in the stop-blocker's own resolution list, and it is chosen over the
alternatives for reasons that are practical rather than merely cautious.

Requesting redistribution terms from Stanford ML Group and STARR (option 2) means an
indefinite wait on a party with no obligation to answer, followed by an IRB determination, and
a rewrite of every "synthetic" claim across four papers even if it succeeds. Continuing while
the question is open (option 1 by default) is the worst of both: it accumulates text and
outreach material against a provenance that may not hold.

Synthea is an open-source synthetic patient generator producing FHIR-format records with no
real patient lineage. Using it means:

- The zero-PHI claim becomes true by construction rather than by inheritance, and stays true.
- No redistribution permission is needed from anyone, so the dataset deposit unblocks.
- MedAgentBench is cited for what it legitimately provides — task templates, action schema,
  the FHIR interaction pattern — which is a normal and uncontroversial citation.
- The frictionless pilot ask survives: sites can be told truthfully that no BAA or data-use
  agreement is required.

The cost is honest and small: Synthea output needs curating into clinically coherent vignettes,
which is work the benchmark needed anyway because its vignettes must be counterfactually
frozen and band-annotated. Synthea gives a starting distribution, not finished cases.

## Sequence

1. **Now.** Amend the paper 17 keystone constraint so it no longer authorises the synthetic
   claim over MedAgentBench lineage. *Done 2026-08-22.*
2. **Before any FHIR code is written.** Record the Synthea decision in the harness so the
   choice is visible at the point where it would otherwise be made by accident.
3. **When the cohort is built.** Generate with Synthea, curate into frozen clinical cores,
   annotate bands per `BAND_PROVENANCE.md`, and record the generator version and seed.
4. **Then, and only then.** Lift the deposit suspension for papers 16 and 17, and release
   outreach material describing the data as synthetic.

## What stays suspended until step 3 completes

Per the stop-blocker, unchanged: no public dataset deposit, no toolkit or cohort repository
publication, no pilot or outreach material describing the data as synthetic or claiming no
IRB/BAA is needed, and no manuscript text asserting synthetic provenance for a
MedAgentBench-derived cohort.

Paper 11's current text is exempt from that last item, because its present claims describe its
own hand-written vignettes and are accurate. It stops being exempt the moment the cohort
changes, which is why the decision is being recorded before the code is written rather than
after.

## Still open

The stop-blocker's item 4 is unresolved: the NEJM AI published version of MedAgentBench has
not been checked for an ethics or data-availability statement, because the publisher page
returned HTTP 403. That check does not gate the Synthea decision. It only matters if someone
later argues the profiles were licensed for reuse after all.

---

## Amendment, 2026-08-27: what the Synthea survey actually found

Step 3 of the sequence above assumed Synthea would supply the vignettes' clinical presentations
and that curation would be a shaping step. A survey against Synthea v4.0.0 shows that assumption
is wrong for three of the four draft vignettes, and the full record is in
`cohort/PRESENTATION_AVAILABILITY.md`.

No urolithiasis module exists, so the renal-colic vignette that serves as the paper's
construct-validity anchor has no substrate. No ketoacidosis module exists, so the DKA
documentation vignette has none either. More durably than either: Synthea exports resolved
diagnoses, while this benchmark measures the decision taken before the diagnosis is known, so
even where a module exists the pre-diagnosis presentation must be authored.

Only `appendicitis` maps cleanly to a draft vignette.

**The provenance rationale is unaffected and the decision stands.** Every reason for choosing
Synthea over MedAgentBench-derived profiles was about lineage, licensing and the truth of the
zero-PHI claim, and all of them hold. What changes is the expected saving: Synthea supplies
value distributions, code systems and background history, not finished cases, and the clinical
authoring burden is essentially unchanged from before the switch.

The plan's own sentence -- "Synthea gives a starting distribution, not finished cases" -- was
accurate. It should be read as the operative description of what this route buys, rather than as
a caveat on a larger claim.

Step 3 is therefore restated: generate with Synthea and record version and seed; author the
clinical presentations; use `cohort/tools/fixture_distributions.py` to ground fixture values in
generated distributions rather than intuition; annotate bands per `BAND_PROVENANCE.md`.
