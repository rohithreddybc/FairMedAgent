# Crossed (vignette by replicate) bootstrap

Script: `harness/scripts/crossed_boot.py`, run as `FMA_PANEL=v3 FMA_BOOT=crossed python harness/scripts/robustness.py` or
directly as `FMA_PANEL=v3 python harness/scripts/crossed_boot.py`. Output: `experiments/robustness_v3_crossed.json`
(B=5000, seed 42). The vignette-only intervals used for comparison below are those in `experiments/robustness_v3.json`
(same vignette resamples).

## Method

Vignettes and replicates are resampled independently with replacement (the pigeonhole bootstrap for crossed random
effects, Owen 2007). The vignette multisets are the 5000 draws behind `robustness_v3.json`; the vignette-only branch
of `crossed_boot.py` reproduces every pooled five- and six-action interval in that file (the check is stored in the
`meta` block of the JSON). Replicate draws are layered on top, independently per model, so between-model
differences remain paired over vignettes.

A resample of replicates contains repeats. The resampled floor therefore uses the off-diagonal (U-statistic) form: the
sum over distinct original replicates a<b of m_a*m_b times the vignette-weighted discordance, divided by the same
weights times the comparison count, where m_a is the number of times replicate a was drawn. Pairs formed from two
copies of one replicate never enter, so they cannot act as zero-disagreement pairs. A resample containing only one
distinct replicate has no admissible pair and is dropped (the JSON records the count as `n_dropped`).

Majority vote (five of ten replicates): the statistic uses all ten replicates in one symmetric kernel, and a
with-replacement replicate resample contains about 6.5 distinct replicates, so each five-draw side contains repeats and
votes with fewer effective draws. The crossed bootstrap distribution is then centred below the estimate (model A, five
actions: observed reduction 0.532, crossed median 0.261, vignette-only median 0.538; crossed percentile interval [-0.354, 0.812]),
and the crossed interval is not valid for this statistic. The vote-reduction intervals reported in the manuscript are
vignette-bootstrap intervals, conditional on the ten replicates observed. The crossed values are kept in the JSON
(`majority_vote`) and are flagged there as biased.

## Dependence diagnostic

Width ratio is the crossed over the vignette-only width of the pooled-floor interval on the same vignette draws. The
permutation checks (2000 permutations, five actions) permute, within each vignette x action cell, the R answers across
replicates, which preserves each cell's rate and removes only replicate-level linkage. The ratio is the observed
statistic over the mean null statistic (1 means no replicate effect); p is one-sided. The `groq_t1` width ratio comes
from the temperature comparison (15 shared vignettes).

| Model | R | Width ratio, five actions | Width ratio, six actions | Replicate-mean variance ratio (p) | Pair-floor variance ratio (p) |
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

Across models A-F the crossed intervals are wider than the vignette-only intervals by a factor of 1.10 to 1.63 (five
and six actions together). Models A and B answered 16 vignettes per call in a shared context; models C-F answered one
prompt per call. The permutation checks do not detect significant replicate-level dependence for A (p = 0.137 and 0.433);
B has the largest excess in per-replicate mean rate (variance ratio 1.98, p = 0.062, R = 6), which is not significant at
the 5 percent level. The only significant result is the pair-floor heterogeneity of F (ratio 2.17, p = 0.001), a local
model with independent calls. F at temperature 0 is degenerate (almost every cell is unanimous). With R between 5 and
10 these tests have little power, so the absence of a detected shared-context effect is not evidence that none exists.

## Pooled floors

| Model | Five-action floor | Vignette-only 95% CI | Crossed 95% CI | Six-action floor | Vignette-only 95% CI | Crossed 95% CI |
|---|---|---|---|---|---|---|
| A | 0.068 | [0.036, 0.101] | [0.032, 0.110] | 0.087 | [0.056, 0.117] | [0.048, 0.125] |
| B | 0.040 | [0.015, 0.070] | [0.008, 0.081] | 0.067 | [0.038, 0.096] | [0.024, 0.113] |
| C | 0.230 | [0.195, 0.264] | [0.184, 0.276] | 0.225 | [0.198, 0.256] | [0.186, 0.266] |
| D | 0.098 | [0.070, 0.125] | [0.063, 0.133] | 0.105 | [0.079, 0.132] | [0.073, 0.139] |
| E | 0.017 | [0.003, 0.037] | [0.000, 0.041] | 0.035 | [0.011, 0.065] | [0.009, 0.069] |
| F | 0.245 | [0.206, 0.284] | [0.182, 0.309] | 0.236 | [0.197, 0.277] | [0.178, 0.298] |

## Per-action floors

Vignette-only intervals are those in `robustness_v3.json` (item 1, B=5000).

| Model | Action | Floor | Vignette-only 95% CI | Crossed 95% CI |
|---|---|---|---|---|
| A | admit | 0.142 | [0.051, 0.242] | [0.039, 0.260] |
| A | any_opioid | 0.025 | [0.000, 0.062] | [0.000, 0.103] |
| A | cs_caution | 0.179 | [0.064, 0.296] | [0.041, 0.329] |
| A | escalate_icu | 0.022 | [0.000, 0.067] | [0.000, 0.093] |
| A | high_acuity | 0.076 | [0.000, 0.171] | [0.000, 0.186] |
| A | referral | 0.075 | [0.000, 0.167] | [0.000, 0.175] |
| B | admit | 0.042 | [0.000, 0.104] | [0.000, 0.148] |
| B | any_opioid | 0.033 | [0.000, 0.100] | [0.000, 0.130] |
| B | cs_caution | 0.200 | [0.067, 0.333] | [0.000, 0.409] |
| B | escalate_icu | 0.021 | [0.000, 0.062] | [0.000, 0.104] |
| B | high_acuity | 0.067 | [0.000, 0.167] | [0.000, 0.192] |
| B | referral | 0.037 | [0.000, 0.113] | [0.000, 0.125] |
| C | admit | 0.201 | [0.100, 0.310] | [0.084, 0.337] |
| C | any_opioid | 0.069 | [0.013, 0.139] | [0.000, 0.178] |
| C | cs_caution | 0.203 | [0.093, 0.315] | [0.078, 0.339] |
| C | escalate_icu | 0.069 | [0.000, 0.154] | [0.000, 0.170] |
| C | high_acuity | 0.412 | [0.358, 0.461] | [0.284, 0.525] |
| C | referral | 0.397 | [0.318, 0.468] | [0.278, 0.505] |
| D | admit | 0.022 | [0.000, 0.067] | [0.000, 0.093] |
| D | any_opioid | 0.069 | [0.000, 0.174] | [0.000, 0.176] |
| D | cs_caution | 0.142 | [0.051, 0.237] | [0.037, 0.266] |
| D | escalate_icu | 0.051 | [0.000, 0.132] | [0.000, 0.146] |
| D | high_acuity | 0.332 | [0.233, 0.425] | [0.201, 0.461] |
| D | referral | 0.013 | [0.000, 0.037] | [0.000, 0.069] |
| E | admit | 0.046 | [0.000, 0.125] | [0.000, 0.134] |
| E | any_opioid | 0.025 | [0.000, 0.062] | [0.000, 0.091] |
| E | cs_caution | 0.129 | [0.029, 0.233] | [0.026, 0.259] |
| E | escalate_icu | 0.000 | [0.000, 0.000] | [0.000, 0.000] |
| E | high_acuity | 0.000 | [0.000, 0.000] | [0.000, 0.000] |
| E | referral | 0.013 | [0.000, 0.037] | [0.000, 0.069] |
| F | admit | 0.336 | [0.235, 0.432] | [0.204, 0.469] |
| F | any_opioid | 0.069 | [0.013, 0.136] | [0.000, 0.169] |
| F | cs_caution | 0.191 | [0.100, 0.281] | [0.077, 0.316] |
| F | escalate_icu | 0.094 | [0.013, 0.199] | [0.000, 0.214] |
| F | high_acuity | 0.314 | [0.226, 0.399] | [0.173, 0.449] |
| F | referral | 0.411 | [0.346, 0.469] | [0.286, 0.518] |

## Pairwise differences in pooled floor

| Pair | Difference (5 actions) | Vignette-only CI | Crossed CI | Difference (6 actions) | Vignette-only CI | Crossed CI |
|---|---|---|---|---|---|---|
| A-B | 0.028 | [0.008, 0.048] | [-0.010, 0.065] | 0.020 | [0.001, 0.038] | [-0.024, 0.065] |
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

Pairs whose interval excludes zero (unadjusted): five actions, 11 of 15 crossed (12 of 15 vignette-only); six actions,
10 of 15 crossed (11 of 15 vignette-only).

## Other quantities

| Quantity | Estimate | Vignette-only | Crossed |
|---|---|---|---|
| Range factor (largest over smallest pooled floor), 5 actions | 14.7 | 7.1-96.8 (51 undefined resamples) | 6.7-92.7 (309 undefined) |
| Range factor, 6 actions | 6.7 | 3.6-21.1 (1 undefined) | 3.6-26.9 (15 undefined) |
| Model A, admission minus ICU escalation | 0.119 | [0.012, 0.229] | [-0.001, 0.245] |
| Model A, caution flag minus ICU escalation | 0.157 | [0.051, 0.269] | [0.019, 0.309] |
| Model A, ratio of largest to smallest five-action floor (finite resamples only) | 6.38 | [2.407, 17.444] (2388 undefined) | [2.333, 16.556] (3631 undefined) |
| Model F (phi3:mini), temperature 0 versus default, 5 actions: floor at temperature 0 | 0.021 | [0.000, 0.048] | [0.000, 0.080] |
| Model F (phi3:mini), temperature 0 versus default, 5 actions: reduction | 91% | 79-100% | 65-100% |
| Groq gpt-oss-20b, temperature 1 versus 0, 5 actions: floor at temperature 0 | 0.029 | [0.000, 0.067] | [0.000, 0.073] |
| Groq gpt-oss-20b, temperature 1 versus 0, 5 actions: reduction | 69% | 33-100% | 15-100% |
| Groq gpt-oss-20b at temperature 0, 5 actions (22/800) | 0.028 | [0.000, 0.065] | [0.000, 0.072] |

Models C-E at temperature 0 have floors of 0.000 with interval [0.000, 0.000] under both methods.

## Quantities not affected by the crossed bootstrap

Point estimates, leave-one-vignette-out ranges, the independent-noise null simulations (model checks, not sampling
intervals), the McNemar simulation, the four-vignette pilot interval, and the rank correlations with their exact
permutation p-values (which use point per-action rates only). The exceedance-probability ranges computed by
`harness/scripts/exceedance_range.py` are spans over the vignette-bootstrap floor interval.
