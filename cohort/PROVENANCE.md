# Cohort provenance

This directory holds the generator and the record of how the vignette substrate was produced.
It exists so that the manuscript's synthetic-provenance claims are true by construction and
checkable by a third party, rather than inherited from another dataset's licence.

## Generator

| | |
|---|---|
| Tool | Synthea, MITRE |
| Release | v4.0.0 |
| Artifact | `synthea-with-dependencies.jar` |
| Source | `https://github.com/synthetichealth/synthea/releases/download/v4.0.0/synthea-with-dependencies.jar` |
| Size | 201,164,144 bytes |
| SHA-256 | `ed43c20ad40ba5c3bc724503a5af032715fe3c491620b766148e7c2361e6ecc1` |
| Licence | Apache License 2.0 |
| Retrieved | 2026-08-27 |
| Runtime | Java 21.0.2 LTS |

The JAR is not committed. Re-obtain it from the URL above and check the digest before use; a
digest mismatch means the artifact is not the one these records describe, and the cohort must
not be regenerated from it without updating this file.

## Why generated rather than downloaded

MITRE also publishes a fixed sample of roughly a thousand patients. That sample was retrieved
and then discarded in favour of local generation, for one reason: a published sample can be
identified by URL and checksum, but its seed belongs to MITRE. `COHORT_PROVENANCE_PLAN.md`
requires recording the generator version *and seed*, which is a reproducibility claim about our
own cohort, and a fixed download cannot support it. Local generation can.

Determinism was verified rather than assumed. Two runs at seed `20260827` produced byte-identical
`patients.csv` (SHA-256 `fded25222f51d340bd71245f3122455c5e44c88b79fd96f59b9e9e0cfd3c0b1f`).

## Commands

Survey population, used to characterise what presentations Synthea actually produces before any
selection logic was written:

```
java -jar synthea-with-dependencies.jar -p 400 -s 20260827 -cs 20260827 \
  --exporter.csv.export=true --exporter.fhir.export=false \
  --exporter.baseDirectory=./out_survey Massachusetts
```

Both the population seed (`-s`) and the clinician seed (`-cs`) are pinned. Pinning only the
former leaves provider assignment free to vary between runs.

## The constraint that governs how this data may be used

**Synthea's disease incidence is demographically parameterised.** Its modules encode real
prevalence differences by race, ethnicity, sex and age, which is a virtue for most purposes and
a defect for this one. FairMedAgent's design rests on the clinical narrative being frozen while
only the demographic descriptor varies. A vignette carrying both a Synthea patient's clinical
course *and* that patient's demographics would import the generator's demographic-clinical
correlation into the very contrast the benchmark is measuring, and a flip attributable to that
correlation would be indistinguishable from a flip attributable to the model.

Selection therefore runs on clinical criteria only, and the source patient's demographics are
discarded rather than carried forward. The demographics a vignette is rendered under come from
the condition set in `fairmedagent/conditions.py` and from nowhere else. The build tooling
asserts this rather than trusting it; see `tools/build_cohort.py`.

A second, softer limit is worth stating in the same place. Synthea produces longitudinal records
rather than emergency-department presentations bounded by a guideline-defined acceptable action.
It supplies a clinically coherent substrate: real code systems, plausible value distributions,
internally consistent histories. It does not supply finished vignettes, and the curation step
between the two is where the clinical judgement lives.

## Status

- [x] Generator obtained, digest recorded, determinism verified
- [x] Survey population generated
- [ ] Presentation availability characterised against the four action domains
- [ ] Frozen clinical cores curated
- [ ] Bands annotated per `docs/BAND_PROVENANCE.md`
- [ ] Cohort seed and command for the final set recorded here
