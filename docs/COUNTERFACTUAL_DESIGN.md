# Counterfactual Profile Design. FairMedAgent

## 1. Protected attributes and exact levels

FairMedAgent varies a small, equity-grounded set of protected attributes, each mapped onto a **PROGRESS-Plus** dimension (Cochrane Equity Methods Group) so the attribute set is principled rather than ad hoc:

| Attribute | Levels (exact) | PROGRESS-Plus dimension |
|---|---|---|
| Race/ethnicity | White, Black, Hispanic, Asian, Native American | Race/ethnicity/culture/language |
| Sex/gender | Male, Female (nonbinary documented as a **limitation**, not a level) | Gender/sex |
| Age | Young adult (~30), Middle-aged (~55), Older adult (~78) | Age (PLUS) |
| Insurance/SES proxy | Medicaid, Private | Socioeconomic status |
| Limited English proficiency (LEP) | LEP-present, English-proficient | Race/ethnicity/culture/**language** |

A sixth **control condition carries no demographic descriptor** (following Omar/Nadkarni 2025's 31 groups + 1 control design), serving as the neutral reference for signed group-rate gaps. Dimensions deliberately out of scope (nonbinary gender, disability, religion, sexual orientation) are named as limitations rather than silently omitted (per STANDING Together documentation discipline).

## 2. Intersectional cells

Single-attribute variation is the baseline; **intersections are first-class reported axes, not appendix material** (the gap Omar left open). The pre-registered intersectional cells are the equity-salient crossings: Black×Medicaid, Black×Female, Hispanic×LEP, Black×Medicaid×LEP×Female (the maximal stress cell), and Native American×Medicaid. Because per-cell N collapses as attributes are crossed, every intersectional point estimate is reported **only descriptively with its N and CI**; cells below the pre-registered minimum size receive Bayesian beta-binomial credible intervals and **no significance claim**, and all intersectional findings are labeled **hypothesis-generating** pending confirmation on the sealed split.

## 3. Encoding method

Demographics are signaled by **name + an explicit one-clause descriptor**, never by altering clinical facts (the Bertrand–Mullainathan lineage of name-as-signal, extended with an explicit descriptor to remove ambiguity). Race/ethnicity, insurance, and LEP appear in a single fixed sentence injected at a constant location in the vignette header, for example *"The patient is a [age]-year-old [race/ethnicity] [sex] with [Medicaid/private] insurance; [a professional interpreter is required / English is the patient's primary language]."* Names are drawn from a fixed, demographically-congruent roster so the name and the descriptor agree. Clinical narrative, vitals, labs, history, and complaint text are byte-identical across all conditions of the same base vignette. This realizes counterfactual fairness as a **metamorphic relation** (Ma et al., IJCAI 2020): the only permitted perturbation is the protected descriptor, so any output change is a fairness-bug signal.

## 4. Synthetic generation protocol

Vignettes are **templated and parameterized** for reproducibility. Each of the ~30–40 base vignettes is a frozen clinical core (chief complaint, history, vitals, exam, labs) authored/reviewed by the clinician co-author. A deterministic renderer expands `base_vignette × condition` by substituting only the demographic slot, producing the full grid `CONFIGS × PROFILES × CONDITIONS` consumed by `audit_harness.js`. Generation is fully reproducible: fixed seeds, **temperature 0**, pinned model IDs + release dates (Haiku 4.5, Sonnet 4.6, Opus 4.8, Fable 5), scaffolds C0/C1/C2, and a content hash per rendered profile. The renderer, base vignettes, and a **Gebru-style Datasheet** ship together in the versioned Hugging Face dataset card.

## 5. Verifying clinical content is held constant

Constancy is enforced mechanically, not by inspection. For each base vignette, the renderer computes a **SHA-256 hash of the clinical core with the demographic slot masked out**; all conditions of that vignette must share an identical masked hash, and a CI test fails the build otherwise. A diff harness asserts that the *only* token spans differing across sibling conditions are the name and the descriptor sentence. The clinician co-author signs off that ESI-relevant facts, red flags, and lab abnormalities are demographically neutral (satisfying DECIDE-AI human-oversight framing). Where any vignette has human-labeled ground truth, inter-rater agreement is reported as **Krippendorff's α** (DRAGON precedent).

## 6. Contamination and anti-memorization

To resist train-set memorization and leaderboard overfitting: (a) **canary strings**: a unique GUID is embedded in every dataset shard and the protocol, so future models trained on leaked data can be detected; neither Omar, DRAGON, nor MedS-Bench published explicit canaries, making this a cheap differentiator. (b) **Template parameterization**: surface realizations (synonyms, unit formats, name rosters) are drawn from parameter pools so the public dev split never exposes the exact string form used in the sealed test split. (c) Sealed-split items are held off-platform entirely.

## 7. Dev-split vs sealed-test-split and anti-gaming

The dataset is partitioned into a **public dev split** (vignettes + renderer + `audit_harness.js` semver pip package on GitHub, versioned dataset on Hugging Face, following the MedS-Bench release pattern) and a **SEALED held-out test split** that drives the leaderboard. The sealed split's labels and exact strings are never published. Leaderboard mechanics follow the **DRAGON** template: hidden test labels, server-side or attestation-based evaluation, a single composite score that is an explicit **unweighted mean across action domains × metrics** with the formula and per-cell sub-scores published, a stated minimum support window, and **mandatory open-source disclosure** within a fixed window of submission. Every submission is logged with **name, affiliation, and country**. Any disparity discovered on the dev split is treated as exploratory until it **survives confirmation on the sealed split under BH-FDR**, which is the operational guard against tuning to the public set. This dev/sealed separation plus canaries plus submission logging is FairMedAgent's anti-gaming spine, the public-leaderboard rigor Omar's design lacked.
