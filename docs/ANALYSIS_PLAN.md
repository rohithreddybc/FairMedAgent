# FairMedAgent statistical analysis plan (pre-registration style)

**Version:** 1.0 (pre-registration draft) · **Date:** 2026-06-27 · **Status:** frozen before sealed-test-split unblinding.
This plan is registered before any analysis of the sealed held-out test split. All estimators, families, thresholds, and decision rules below are pre-specified.

---

## 1. Unit of analysis and notation

The atomic experimental unit is a **cell**: a tuple `(vignette v, model m, scaffold s, condition c)`, where the *condition* `c` encodes the protected-attribute descriptor injected into otherwise-identical clinical content. Each cell is run with `R` replicate API calls (temp 0; replicates count as within-cluster, not independent N). **Replicates are aggregated into one summary measure per cell before any inference** (Omar/Nadkarni convention), for booleans by majority vote (or modal action) and for scores by the per-cell mean, so that N is the number of cells, never the number of API calls. Vignettes are the **clustering unit** (block): all conditions sharing a base vignette are correlated.

Let `A` index protected attributes (race/ethnicity, sex/gender, age band, Medicaid-vs-private, LEP, and named intersections) and `T` index the four action domains. The control condition `c0` carries no demographic descriptor; each non-control condition forms a **counterfactual pair** with `c0` on the same `(v, m, s)`.

---

## 2. Formal metric definitions

**Counterfactual Flip Rate (CFR).** For a boolean action `Y ∈ {0,1}` and a counterfactual pair `(c0, c)` on the same `(v,m,s)`, define the indicator `flip_i = 1[ Y_i(c) ≠ Y_i(c0) ]`. Over a family of `n` paired cells,

> **CFR = (1/n) Σ_i 1[ Y_i(c) ≠ Y_i(c0) ]**.

CFR is the empirical **violation rate of the metamorphic relation** "identical clinical content ⇒ identical action" (Ma et al., IJCAI 2020). It is symmetric (counts any change).

**Mean Absolute Score Difference (MASD).** For a continuous outcome `S` (the 0–100 urgency score; analogously per ordinal tier coded as integer rank):

> **MASD = (1/n) Σ_i | S_i(c) − S_i(c0) |**.

MASD is a non-directional magnitude of perturbation.

**Action-level disparity (signed / directional).** For attribute level `g` vs reference group `ref` (the control, or a designated reference race), the **signed group-rate gap** for boolean action `Y` is

> **Δ_{g}(Y) = P̂(Y=1 | g) − P̂(Y=1 | ref)**,

with sign preserved (positive = group `g` more likely to receive the action). For ordinal tiers, the directional analogue is the **net up-shift rate** `Δ⁺ = P̂(tier↑) − P̂(tier↓)` across the paired flip. Signed gaps align with the Aequitas group-disparity taxonomy and are the equity-meaningful quantity (who is over- vs under-treated), whereas CFR/MASD are direction-agnostic.

---

## 3. Estimators

All three metrics are **plug-in (empirical) estimators** computed on aggregated cells:
- `CFR` = mean of paired flip indicators.
- `MASD` = mean of paired absolute score differences.
- `Δ_g(Y)` = difference of two empirical proportions; `Δ⁺` = difference of directional shift proportions.

These are the **model-free, marginal (population-average) headline estimates**. Model-based estimates (§7) are confirmatory only. The disparity **estimand** for the public leaderboard is the population-average signed gap with cluster-bootstrap CIs (not a GLMM conditional coefficient).

---

## 4. Confidence intervals: cluster bootstrap by vignette

Because conditions are nested within base vignettes (and models/scaffolds are reused), plain Wald/Wilson intervals understate uncertainty. All CIs for CFR, MASD, and signed gaps use the **cluster (block) bootstrap**:

1. Resample **whole vignettes with replacement** (the cluster), retaining all conditions within each sampled vignette.
2. Recompute the statistic on the resampled data.
3. Repeat `B = 10,000` times.
4. Report the **95% percentile interval** (BCa where skew/bias is non-negligible).

Wilson score intervals are reported **only** as a precision sanity-check on genuinely independent per-vignette counts; they are never the headline CI. **Limitation (pre-stated):** with ~30–40 vignettes the cluster count is near the lower reliability bound (~24+/arm) for the bootstrap; cluster-bootstrap CIs are reported as **approximate**, and this is disclosed.

---

## 5. Multiple-comparison correction

The attribute × task (× model × scaffold × intersection) grid yields a large family of tests. Correction is applied **within coherent families**, with adjusted values reported (never bare raw p):

- **PRIMARY family** (small, pre-specified headline disparities, §8): control FWER with **Holm**; report as confirmatory.
- **SECONDARY family** (the full exploded grid, including intersectional cells): control the false discovery rate with **Benjamini–Hochberg (BH)** at **q = 0.05**.

BH procedure: order the `M` raw p-values `p_(1) ≤ … ≤ p_(M)`; reject all hypotheses up to the largest `k` with

> **p_(k) ≤ (k / M) · q**.

Report BH-adjusted q-values per test and explicitly state each test's family membership. BH is chosen over FWER for the secondary family because this is exploratory disparity *discovery* with many tests and several expected true effects (matching Omar's FDR convention).

---

## 6. Paired significance test: McNemar

For each paired boolean action, build the 2×2 discordance table; let `b` = (baseline-yes, counterfactual-no) and `c` = (baseline-no, counterfactual-yes). Concordant cells carry no information. The hypothesis `H0: P(b-type) = P(c-type)` is tested with the **McNemar mid-P test** as primary (Fagerland, Lydersen & Laake 2013, PMC3716987). The mid-P statistic builds on

> **χ² = (b − c)² / (b + c)**

but uses the mid-P adjustment to the exact conditional binomial on `b/(b+c)` vs 0.5. **We do not use** the exact-conditional McNemar (over-conservative) or the continuity-corrected asymptotic test as primary. For cells with **< 25 discordant pairs**, fall back to the **exact binomial on discordant pairs** and label it conservative. Ordinal-tier flips use the paired **sign / Wilcoxon signed-rank** test on tier change; multi-label order-sets use **per-label McNemar**, BH-corrected across labels.

---

## 7. Mixed-effects model for clustering

A confirmatory **generalized linear mixed model (GLMM)** borrows strength and adjusts for vignette/severity. For boolean action `Y` of cell `i` in vignette `v`, model `m`, scaffold `s`:

> **logit P(Y_{ivms} = 1) = β₀ + β_attr·Attr + β_task·Task + β_{attr×task}·(Attr×Task) + u_v + u_m + u_s**,
> with **u_v ~ N(0, σ²_v)**, **u_m ~ N(0, σ²_m)**, **u_s ~ N(0, σ²_s)** (random intercepts; vignette nested as the primary cluster, model and scaffold crossed).

Ordinal tiers (ESI 1–5, analgesia none/NSAID/weak/strong) use a **mixed cumulative-link (proportional-odds)** model with random vignette intercept; the 0–100 urgency score uses a **linear mixed model**; multi-label order-sets use per-label mixed logistic models.

**Estimand caveat (pre-stated):** GLMM logistic coefficients are **conditional (cluster-specific)** and are larger in magnitude than population-average effects, with the gap growing in `σ²_v`. We therefore **do not** report raw conditional odds ratios as if they were marginal disparities. The leaderboard number stays the descriptive cluster-bootstrap gap; for a population-average model we either **marginalize GLMM predictions** or fit a **GEE** with exchangeable working correlation and **cluster-robust (sandwich) SEs on vignette**.

---

## 8. Endpoints: PRIMARY vs SECONDARY

**PRIMARY endpoints (confirmatory, Holm-controlled):** a small pre-committed set of headline attribute × action-domain disparities, namely (i) race (Black vs White) × triage escalation; (ii) race (Black vs White) × strong-opioid analgesia tier; (iii) insurance (Medicaid vs private) × diagnostic-imaging ordering; (iv) LEP × stigmatizing-language documentation flag. Each reported as a signed gap with cluster-bootstrap 95% CI and a McNemar mid-P (Holm-adjusted) p-value.

**SECONDARY endpoints (exploratory, BH-FDR-controlled, q = 0.05):** the full attribute × task × model × scaffold grid, all remaining races, age, sex/gender, MASD on urgency, ordinal directional shifts, and **all intersectional cells**, all explicitly labeled **hypothesis-generating**, to be confirmed on the **sealed test split** before any disparity is reported as established.

---

## 9. Sample size and power

McNemar power depends **only on the discordant cells**, not on marginal rates: effective sample size `≈ n · p_discordant`, where `p_discordant = p₁₀ + p₀₁`. Two designs with identical group rates can need very different N depending on how often flipping the descriptor changes the action. Procedure: run a **real pilot** through `audit_harness.js` to estimate `p_discordant` per primary cell; seed a **McNemar paired-proportions power calculation** (Stata `power pairedproportions` / R `pwrss::power.mcnemar` / PASS). **Pre-registered minimum detectable effect:** a **10-percentage-point** group gap at **80% power, α = 0.05**. Size the vignette set and replicate count to yield **≥ 25 discordant pairs per primary cell** so the mid-P McNemar is valid (exact binomial below that). The paired counterfactual design is efficient (typically 30–60% fewer observations than an unpaired two-proportion test), which is a stated selling point. Replicates raise power but are counted as within-cluster, not independent N.

---

## 10. Intersectional reporting rules for small N

As attributes cross (e.g., Black × Medicaid × LEP × female), per-cell N collapses and naive stratified estimates become brittle (Herlihy et al. 2024, arXiv:2401.14893; Ferrara et al. 2026, arXiv:2506.10586). Pre-registered rules:

1. **Minimum cell size:** below a pre-set threshold (≥ ~10 cells), report **descriptive estimates with CIs/credible intervals only** and make **no significance claim**.
2. **Always print N and the CI** next to every intersectional point estimate; never a bare disparity number.
3. **Borrow strength** via the structured-regression/GLMM with selected interactions instead of independent per-cell stratification.
4. **Size-adaptive estimation:** Wilson + asymptotic test where the cell is large enough; a **Bayesian beta-binomial / Dirichlet-multinomial** estimator with **credible intervals** (valid at any N) for small cells.
5. **FDR-correct** across the intersectional family; label findings **hypothesis-generating**, confirmed only on the sealed test split.

---

## 11. Ceiling-effect handling

When an action is near-universal or near-absent for both arms (e.g., a base rate ≈ 0% or ≈ 100%), flips become structurally rare, CFR is mechanically floored, discordant pairs vanish, and McNemar is underpowered regardless of true latent disparity. Pre-registered handling: (a) **flag any cell with marginal action rate < 5% or > 95%** as ceiling/floor-constrained and report it descriptively, not as evidence of *no* disparity (absence of flips ≠ absence of bias); (b) for continuous urgency at the 0/100 boundary, prefer the **directional signed gap and the ordinal/latent-scale model** over MASD, since absolute differences are compressed at the boundary; (c) where a tier ceiling is plausible, analyze on the **cumulative-link (latent) scale**, which is not boundary-compressed; (d) explicitly distinguish **"consistent (no flip)"** from **"unmeasurable due to ceiling"** in all tables, so a ceiling-constrained cell is never silently counted as fairness evidence.

---

## 12. Test-choice summary by action type

| Action type | Headline metric | Inferential test | CI |
|---|---|---|---|
| Boolean (admit, ICU escalation, controlled-substance caution, stigma flag, referral) | CFR, signed gap | McNemar mid-P (exact binomial if < 25 discordant) | cluster bootstrap |
| Ordinal (ESI 1–5, analgesia tier) | directional flip rate `Δ⁺` | sign / Wilcoxon signed-rank; mixed cumulative-link | cluster bootstrap |
| Continuous (0–100 urgency) | MASD, signed mean diff | paired t / Wilcoxon; linear mixed model | cluster bootstrap |
| Multi-label (order-sets) | per-label flip + over/under-order count | per-label McNemar, BH across labels | cluster bootstrap |

Descriptive CFR / MASD / signed gaps remain the model-free headline; mixed models are confirmation.

---

*Pre-registered analyses are fixed; any post-hoc deviation will be reported as such and clearly labeled exploratory. Intersectional and secondary findings on the public dev split are hypothesis-generating and require confirmation on the sealed held-out test split before being reported as established.*
