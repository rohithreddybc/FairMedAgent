# Crossed (vignette x replicate) bootstrap: old vs new intervals

Source: `harness/scripts/crossed_boot.py` (`FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/robustness.py`, or
run the script directly), output `experiments/robustness_v3_crossed.json`. B=5000, seed 42. No existing JSON was
modified (md5-checked before and after). The manuscript was not edited.

## Method

Vignettes and replicates are resampled independently with replacement (Owen 2007 pigeonhole bootstrap for crossed
random effects). The vignette multisets are the identical 5000 draws behind `robustness_v3.json`; the vignette-only
branch of the new script reproduces every pooled five- and six-action interval in that file exactly (regression check
stored in the JSON meta). Replicate draws are layered on top, independently per model, so between-model differences
stay paired over vignettes.

Duplicated replicates: the resampled floor is the off-diagonal (U-statistic) form, the sum over distinct ORIGINAL
replicates a<b of m_a*m_b times the vignette-weighted discordance, divided by the same weights times the comparison
count (m_a = times replicate a was drawn). Pairs of two copies of one replicate never enter, so they cannot pose as
zero-disagreement pairs; every other draw-position pair enters exactly as often as it occurs. Resamples with only one
distinct replicate would be dropped (none occurred).

Majority vote (R=5 of 10): **no valid crossed interval exists.** The R=5 statistic uses all ten replicates in one
symmetric kernel. A with-replacement replicate resample has about 6.5 distinct replicates, so each "five-vote" side
contains repeats and votes with fewer effective draws. The crossed bootstrap distribution is therefore centred far below
the estimate (model A, five actions: observed reduction 0.532, crossed bootstrap median 0.261, vignette-only median
0.538), and its percentile interval ([-0.354, 0.812]) is an artifact. Replicate-level uncertainty of this statistic is
not estimable nonparametrically at R=10 (no replicate can be deleted or repeated without changing the estimator). The
existing vote intervals are valid only conditional on the ten replicates observed. The biased crossed numbers are kept
in the JSON for transparency only.

## Dependence diagnostic

Width ratio = crossed / vignette-only width of the pooled-floor interval on the same vignette draws. Permutation checks
(2000 permutations, five actions): within each vignette x action cell the R answers are permuted across replicates,
which preserves each cell's rate and destroys only replicate-level linkage. Ratio = observed / mean null statistic
(1 = no replicate effect); p is one-sided. The groq_t1 width ratio is from the temperature comparison (15 shared
vignettes).

| Model | R | Width ratio 5a | Width ratio 6a | Rep-mean var ratio (p) | Pair-floor var ratio (p) |
|---|---|---|---|---|---|
| A | 10 | 1.20 | 1.26 | 1.48 (0.137) | 1.02 (0.433) |
| B | 6 | 1.32 | 1.54 | 1.98 (0.062) | 1.21 (0.311) |
| C | 10 | 1.34 | 1.36 | 0.73 (0.703) | 0.67 (0.925) |
| D | 10 | 1.25 | 1.26 | 1.09 (0.376) | 0.93 (0.604) |
| E | 10 | 1.18 | 1.10 | 0.61 (0.954) | 0.80 (0.769) |
| F | 10 | 1.63 | 1.50 | 1.20 (0.289) | 2.17 (0.001) |
| groq_t1 | 5 | 1.41 | - | 1.42 (0.241) | 0.42 (0.932) |
| groq_t0 | 5 | - | - | 0.74 (0.750) | 1.61 (0.126) |
| F_t0 | 5 | - | - | 0.00 (1.000) | 3.92 (0.012) |

Reading: the crossed intervals are wider for every model, by 1.10 to 1.63 times, and A (1.20) and B (1.32) do not
stand out from the one-prompt-per-call local models C-F (1.18 to 1.63). Most of the widening is therefore the generic
replicate-sampling component that the vignette-only bootstrap omits for every model, not a shared-context effect
specific to A and B. The permutation checks find no significant replicate-level dependence for A (p = 0.137 and
0.433). B shows the largest excess in per-replicate mean rate (variance ratio 1.98, p = 0.062, R = 6), which is
suggestive but not significant. The only significant signal is F's pair-floor heterogeneity (ratio 2.17, p = 0.001),
on a local model with independent calls. F_t0 is degenerate (almost every cell is unanimous). With R = 6 to 10 these
tests have little power, so "no detected shared-context effect" is not evidence that there is none.

## Old vs new, every interval the manuscript reports

"Old" is the value printed in `srep_main.tex` / `supplementary.tex`; "crossed" is new. **Bold** marks a changed
conclusion.

### Main text, Table 2 and supplement text

| Quantity | Estimate | Old 95% CI | Crossed 95% CI | Conclusion |
|---|---|---|---|---|
| A pooled, 5 actions | 0.068 | [0.036, 0.101] | [0.032, 0.110] | unchanged |
| B pooled, 5 | 0.040 | [0.015, 0.070] | [0.008, 0.081] | unchanged (excludes 0) |
| C pooled, 5 | 0.230 | [0.195, 0.264] | [0.184, 0.276] | unchanged |
| D pooled, 5 | 0.098 | [0.070, 0.125] | [0.063, 0.133] | unchanged |
| E pooled, 5 | 0.017 | [0.003, 0.037] | [0.000, 0.041] | **lower bound now 0** |
| F pooled, 5 | 0.245 | [0.206, 0.284] | [0.182, 0.309] | unchanged |
| A pooled, 6 | 0.087 | [0.056, 0.117] | [0.048, 0.125] | unchanged |
| B pooled, 6 | 0.067 | [0.037, 0.096] | [0.024, 0.113] | unchanged |
| C pooled, 6 | 0.225 | [0.197, 0.256] | [0.186, 0.266] | unchanged |
| D pooled, 6 | 0.105 | [0.079, 0.131] | [0.073, 0.139] | unchanged |
| E pooled, 6 | 0.035 | [0.012, 0.065] | [0.009, 0.069] | unchanged |
| F pooled, 6 | 0.236 | [0.197, 0.278] | [0.178, 0.298] | unchanged |
| A ICU escalation | 0.022 | [0.000, 0.067] | [0.000, 0.093] | unchanged (includes 0) |
| A admission | 0.142 | [0.051, 0.242] | [0.039, 0.260] | unchanged (only defined action excluding 0) |
| A caution flag | 0.179 | [0.064, 0.296] | [0.041, 0.329] | unchanged |
| B: any defined action excluding 0 | - | none | none | unchanged |
| **A admission minus ICU** | 0.119 | [0.012, 0.229] | [-0.001, 0.245] | **now includes 0 (marginally)** |
| Range factor F/E, 5 | 14.7 | 7.1-96.8 (51 undefined) | 6.7-92.7 (309 undefined) | unchanged; still poorly determined |
| Range factor, 6 | 6.7 | 3.6-21.1 | 3.6-26.9 | unchanged |
| Pairs separated, 5 (unadjusted) | - | 12 of 15 | **11 of 15** | **A-B no longer separated** |
| Pairs separated, 6 | - | 11 of 15 | **10 of 15** | **A-B no longer separated** |
| C and F intervals exclude the other four | - | yes | yes (C low 0.184, F low 0.182 > D high 0.133) | unchanged |
| A vote reduction, 5 | 0.532 | 32-81% | not estimable (see Method) | **interval is conditional on replicates** |
| Local vote reductions, 5 | 25-61% | Supp. table | not estimable | as above |
| F t0 floor, 5 | 0.021 | 0.000-0.048 | 0.000-0.080 | unchanged (includes 0) |
| F t0 reduction, 5 | 91% | 79-100% | 65-100% | unchanged |
| F t0 floor / reduction, 6 | 0.018 / 92% | 0.000-0.040 / 82-100% | 0.000-0.067 / 70-100% | unchanged |
| F default (temperature table), 5 | 0.240 | [0.199, 0.282] | [0.177, 0.302] | unchanged |
| Groq t0 floor, 5 | 0.028 | 0.000-0.062 | 0.000-0.072 | unchanged |
| Groq t1 floor, 5 | 0.093 | 0.059-0.128 | 0.047-0.145 | unchanged |
| Groq t1 to t0 reduction | 69% | 33-100% | 15-100% | excludes 0 still, much wider |
| A per-action ratio, 5 (finite subset) | 6.38 | [2.407, 17.444], 2388 undefined | [2.333, 16.556], 3631 undefined | unchanged (still unbounded) |
| A caution minus ICU, 6 | 0.157 | [0.051, 0.269] | [0.019, 0.309] | unchanged |
| A caution/ICU ratio, 6 (finite subset) | 8.06 | [2.271, 12.688], 1784 ICU-zero | [1.188, 19.111], 2107 ICU-zero | unchanged (unbounded) |

C-E temperature-0 floors are 0.000 [0.000, 0.000] under both methods; their default-arm intervals widen as in Table 2.
The old Groq t0 interval is the manuscript's; the script's own vignette-only rerun gives 0.000-0.065 (different random
stream). Six-action vote intervals (supplement, B=2000) are likewise not estimable crossed.

Not affected: point estimates; leave-one-vignette-out ranges; the independent-noise null simulations (model checks,
not sampling intervals); the McNemar simulation; the G=4 pilot interval; and the A-B (and all other) Spearman rank
correlations with their exact permutation p-values, which use point per-action rates only and already are described
as descriptive. **Not recomputed:** the supplement's exceedance-probability ranges ([0.000, 0.004] pooled,
[0.001, 0.076] action-specific) are spans over the floor interval and would widen; rerun `exceedance_range.py` on the
crossed interval if the manuscript adopts it.

### Supplementary per-action floors (all models)

| Model | Action | Floor | Vignette-only | Crossed | Note |
|---|---|---|---|---|---|
| A | admit | 0.142 | [0.051, 0.242] | [0.039, 0.260] |  |
| A | any_opioid | 0.025 | [0.000, 0.062] | [0.000, 0.103] |  |
| A | cs_caution | 0.179 | [0.064, 0.296] | [0.041, 0.329] |  |
| A | escalate_icu | 0.022 | [0.000, 0.067] | [0.000, 0.093] |  |
| A | high_acuity | 0.076 | [0.000, 0.171] | [0.000, 0.186] |  |
| A | referral | 0.075 | [0.000, 0.167] | [0.000, 0.175] |  |
| B | admit | 0.042 | [0.000, 0.104] | [0.000, 0.148] |  |
| B | any_opioid | 0.033 | [0.000, 0.100] | [0.000, 0.130] |  |
| B | cs_caution | 0.200 | [0.067, 0.333] | [0.000, 0.409] | now includes 0 |
| B | escalate_icu | 0.021 | [0.000, 0.062] | [0.000, 0.104] |  |
| B | high_acuity | 0.067 | [0.000, 0.167] | [0.000, 0.192] |  |
| B | referral | 0.037 | [0.000, 0.113] | [0.000, 0.125] |  |
| C | admit | 0.201 | [0.100, 0.310] | [0.084, 0.337] |  |
| C | any_opioid | 0.069 | [0.013, 0.139] | [0.000, 0.178] | now includes 0 |
| C | cs_caution | 0.203 | [0.093, 0.315] | [0.078, 0.339] |  |
| C | escalate_icu | 0.069 | [0.000, 0.154] | [0.000, 0.170] |  |
| C | high_acuity | 0.412 | [0.358, 0.461] | [0.284, 0.525] |  |
| C | referral | 0.397 | [0.318, 0.468] | [0.278, 0.505] |  |
| D | admit | 0.022 | [0.000, 0.067] | [0.000, 0.093] |  |
| D | any_opioid | 0.069 | [0.000, 0.174] | [0.000, 0.176] |  |
| D | cs_caution | 0.142 | [0.051, 0.237] | [0.037, 0.266] |  |
| D | escalate_icu | 0.051 | [0.000, 0.132] | [0.000, 0.146] |  |
| D | high_acuity | 0.332 | [0.233, 0.425] | [0.201, 0.461] |  |
| D | referral | 0.013 | [0.000, 0.037] | [0.000, 0.069] |  |
| E | admit | 0.046 | [0.000, 0.125] | [0.000, 0.134] |  |
| E | any_opioid | 0.025 | [0.000, 0.062] | [0.000, 0.091] |  |
| E | cs_caution | 0.129 | [0.029, 0.233] | [0.026, 0.259] |  |
| E | escalate_icu | 0.000 | [0.000, 0.000] | [0.000, 0.000] |  |
| E | high_acuity | 0.000 | [0.000, 0.000] | [0.000, 0.000] |  |
| E | referral | 0.013 | [0.000, 0.037] | [0.000, 0.069] |  |
| F | admit | 0.336 | [0.235, 0.432] | [0.204, 0.469] |  |
| F | any_opioid | 0.069 | [0.013, 0.136] | [0.000, 0.169] | now includes 0 |
| F | cs_caution | 0.191 | [0.100, 0.281] | [0.077, 0.316] |  |
| F | escalate_icu | 0.094 | [0.013, 0.199] | [0.000, 0.214] | now includes 0 |
| F | high_acuity | 0.314 | [0.226, 0.399] | [0.173, 0.449] |  |
| F | referral | 0.411 | [0.346, 0.469] | [0.286, 0.518] |  |

Four cells that excluded 0 now reach it: B caution flag (exploratory), C and F any-opioid, F ICU escalation. No
five-action statement in the main text rests on those cells.

### Supplementary pairwise differences

| Pair | Diff (5a) | Old CI | Crossed CI | Diff (6a) | Old CI | Crossed CI |
|---|---|---|---|---|---|---|
| A-B | 0.028 | [0.008, 0.048] | [-0.010, 0.065] **lost** | 0.020 | [0.001, 0.038] | [-0.024, 0.065] **lost** |
| A-C | -0.162 | [-0.208, -0.114] | [-0.220, -0.098] | -0.139 | [-0.184, -0.094] | [-0.195, -0.080] |
| A-D | -0.029 | [-0.072, 0.017] | [-0.081, 0.024] | -0.018 | [-0.062, 0.027] | [-0.074, 0.035] |
| A-E | 0.051 | [0.014, 0.091] | [0.007, 0.098] | 0.051 | [0.019, 0.084] | [0.010, 0.093] |
| A-F | -0.177 | [-0.232, -0.124] | [-0.252, -0.102] | -0.150 | [-0.201, -0.097] | [-0.221, -0.079] |
| B-C | -0.190 | [-0.232, -0.147] | [-0.247, -0.130] | -0.159 | [-0.200, -0.118] | [-0.217, -0.098] |
| B-D | -0.058 | [-0.093, -0.017] | [-0.105, -0.007] | -0.038 | [-0.077, 0.001] | [-0.092, 0.017] |
| B-E | 0.023 | [-0.012, 0.061] | [-0.020, 0.070] | 0.031 | [-0.002, 0.065] | [-0.018, 0.080] |
| B-F | -0.205 | [-0.251, -0.158] | [-0.276, -0.133] | -0.169 | [-0.215, -0.122] | [-0.241, -0.099] |
| C-D | 0.133 | [0.095, 0.164] | [0.080, 0.183] | 0.121 | [0.092, 0.147] | [0.076, 0.165] |
| C-E | 0.213 | [0.164, 0.254] | [0.154, 0.267] | 0.190 | [0.146, 0.228] | [0.136, 0.239] |
| C-F | -0.015 | [-0.054, 0.024] | [-0.086, 0.058] | -0.011 | [-0.047, 0.024] | [-0.078, 0.054] |
| D-E | 0.081 | [0.053, 0.108] | [0.045, 0.116] | 0.069 | [0.037, 0.103] | [0.027, 0.112] |
| D-F | -0.147 | [-0.182, -0.112] | [-0.212, -0.083] | -0.131 | [-0.164, -0.099] | [-0.189, -0.072] |
| E-F | -0.228 | [-0.273, -0.184] | [-0.295, -0.162] | -0.201 | [-0.251, -0.150] | [-0.270, -0.133] |

B-D (five actions) stays separated, but its upper bound moves from -0.017 to -0.007.

## Recommendations per affected claim

1. **"12 of the 15 between-model differences" (main text; supplement pairwise section).** Becomes 11 of 15; the lost
   pair is A-B (haiku-4.5 vs sonnet-5), the one comparison between the two shared-context endpoints. Report the crossed
   count and name A-B among the unseparated pairs, describing the hosted-pair difference as descriptive. The six-action
   count becomes 10 of 15.
2. **Separation of the noisiest from the quietest action on the primary model (admission minus ICU, 0.119).** The
   crossed interval touches 0 ([-0.001, 0.245]). The main text lists this separation among what "survives" at 16
   vignettes; it should be made descriptive (point difference whose interval reaches zero once replicate variation is
   included) or removed from that list. The leave-one-vignette-out range (0.092-0.151) is unaffected.
3. **Majority-vote reduction (53%, CI 32-81%; local 25-61%).** Keep the point estimates, but state that the intervals
   resample vignettes only and are conditional on the ten replicates, because replicate-level uncertainty cannot be
   estimated for the R=5-of-10 vote. Make the reduction explicitly descriptive for this replicate set.
4. **qwen3:4b five-action floor and range factor.** The floor interval's lower bound is now 0.000, and the range-factor
   ratio is undefined in 309 resamples (was 51). The interval (6.7-92.7) is otherwise similar, and the existing "poorly
   determined" wording covers it. Report the crossed numbers.
5. **All other intervals.** Conclusions are unchanged. Widths increase by 10-63% for every model, not only A and B.
   Recommend adopting the crossed bootstrap for every reported interval, for consistency. Update the Methods sentence
   ("resampled over vignette clusters") to say vignettes and replicates are resampled as crossed factors, with the
   duplicate-replicate rule. Also state that A and B answered 16 vignettes per call in a shared context, that the
   crossed bootstrap accounts for replicate-level dependence of that kind, and that a permutation check found no
   significant excess for A (p = 0.14) and a non-significant one for B (p = 0.06).
