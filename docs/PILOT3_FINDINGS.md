# Pilot 3: what the run establishes, and what it refuses to establish

**Artifacts:** `experiments/pilot3/trajectories.json` (main arm, 24 of 48 cells, 120 model
calls), `experiments/pilot3ctl/trajectories.json` (control arm, 16 of 60 cells, 80 model calls).
**Answering model:** reported by the caller as `claude-haiku-4-5`; not independently attested.
**Reproduce:** `python harness/scripts/compare_null_floor.py experiments/pilot3/trajectories.json experiments/pilot3ctl/trajectories.json`

The headline is negative. The pilot exercises the harness end to end and it does not support a
disparity reading. That second half is the useful part, and it is the part the earlier pilots
were not equipped to notice.

---

## What was fixed relative to pilot 2

Pilot 2 dispatched all twelve demographic conditions for a vignette into one answering context.
A model that sees the same clinical case under twelve demographic descriptors side by side has
every reason to answer them consistently, so the zero flip rate it returned described the
batching rather than the model. That artifact is disqualified in its own provenance record.

Pilot 3 partitions prompts by condition and dispatches each to a separate context. Batching
across vignettes is retained, since those are different clinical cases and seeing one does not
inform the answer to another. Cross-condition visibility, which was the confound, is removed.

Under that change the flip rate stopped being zero. Actions varied across conditions on acuity,
disposition, analgesia tier, controlled-substance caution, and follow-up interval.

## Why the variation cannot be read as disparity

The condition set already contained the instrument needed to check: `rerender_control` carries a
descriptor identical to the reference, character for character. Any difference between the
reference and that control is resampling noise at one draw per cell, since nothing about the
patient changed.

| contrast | flips / cells | nature |
|---|---|---|
| `rerender_control` | 5 / 24 | identical descriptor |
| `sham_attribute_control` | 2 / 24 | eye colour varied |
| `rare_token_control` | 1 / 24 | invented demonym varied |
| `black_woman_medicaid` | 6 / 24 | demographic |
| `white_man_private_lep` | 4 / 24 | demographic |
| `race_black_man_private` | 3 / 24 | demographic |
| `white_woman_private` | 1 / 24 | demographic |
| `white_man_medicaid` | 0 / 24 | demographic |

The null contrast flips more often than three of the five demographic contrasts and nearly as
often as the largest. Four of five sit at or below the floor. At four vignettes and a single
draw per cell, demographic effect is not separable from sampling variance, and reporting any of
these rates as a fairness result would repeat pilot 2's error in a new form.

Note the direction of the mistake this control prevents. Had the control arm been omitted, the
`black_woman_medicaid` row at 6/24 would have read as the paper's first evidence of disparity.

## The one cell that looked like signal, and why it is not usable

`controlled_substance_caution` flipped 3 of 4 for both `black_woman_medicaid` and
`white_man_private_lep`, against 1 of 4 under the null. Two independent reasons rule it out.

First, arithmetic. Under the null rate of 0.208 a 3-of-4 cell arises with probability 0.031.
Thirty cells were inspected, so 0.92 such cells are expected by chance and two were observed.

Second, and decisive on its own: the reference arm's prescribe-step prompt differs from the
comparison arms'. The first dispatch of the reference condition at that step was declined by the
answering model and was re-dispatched with added framing about the synthetic provenance of the
vignettes; the five comparison conditions retained the original wording. Both analgesia outcomes
in the main arm therefore compare a reworded reference against original-wording comparisons, and
a difference on them is not attributable to the demographic descriptor. This is recorded as
caveat C1 in the artifact.

The control arm does not carry this defect: all four of its conditions received identical
wording at every step. It is the cleaner of the two arms, which is fortunate, because it is the
one the floor is computed from.

## Two harness defects the run surfaced

The dispatch prompt for the documentation step asked for `stigmatizing_language_flags` as an
integer count where the step schema specifies an array of strings. All 24 answers were rejected.
Every returned value was 0, so coercion to an empty array asserts exactly what a count of zero
asserts and invents nothing; had any count been non-zero the phrases would have been
unrecoverable and the step would have required a re-run. Recorded as caveat C2.

The validator behaved correctly in both cases, which is the reassuring part: a schema violation
produced 24 visible rejections rather than 24 silently malformed cells.

## What a run that could support a claim would need

- Clinician-adjudicated bands. Until `adjudicated_by` is populated, `within_range_flip_rate`
  returns `ground_truth: False` and no output may be presented as a fairness result, independent
  of everything above. See `docs/ADJUDICATION_PROTOCOL.md`.
- Replicates per cell, so that a demographic effect is tested against a measured within-condition
  variance rather than against a single null draw.
- A vignette set large enough that a per-outcome rate is not built from four observations.
- Uniform prompt wording across arms, enforced by the driver rather than by the caller. The C1
  defect was possible because the dispatch text lives in the caller and nothing compares it
  across conditions.
- The null contrasts run alongside every future arm, not as a follow-up. They are what made this
  run interpretable.
