# zero-observed bounds, estimands, interval coverage

Scripts: `harness/scripts/fixed_case_bounds.py` (bounds, replicate-only intervals, S12 shifts; writes
`experiments/fixed_case_bounds_v3.json`, run with `FMA_PANEL=v3`, ~35 s) and `harness/scripts/coverage_sim.py`
(coverage; writes `experiments/COVERAGE_SIM.json`, 2000 datasets per scenario, B=1000, seed 20261012, ~2 min).
No manuscript file was edited. No existing JSON was modified.

## 1. One-sided 95% upper bounds for zero-observed floors

Fixed-case bound (recommended). The observed event is "every vignette x action cell unanimous". With per-cell
minority probabilities q_c, P(event) = prod_c [(1-q_c)^R + q_c^R]; {q : P >= 0.05} is an exact 95% confidence
region (zero is the most extreme value of the count of non-unanimous cells). The bound is the maximum of the
fixed-case floor, mean_c 2 q_c (1 - q_c), over that region. With s_c = -log(1-q_c) the floor kernel is concave for
s_c < ln 4, and every feasible s_c is below -ln(0.05)/R <= 0.6, so the maximum is at equal q_c (Jensen). The
common-probability Clopper-Pearson bound q_u = 1 - 0.05^(1/N), floor <= 2 q_u (1 - q_u), N = cells x R, is
therefore also the heterogeneity-robust bound for these fixed vignettes; no common-probability assumption is
needed. Checked numerically (SLSQP from 20 heterogeneous starts per row): same value to 4 decimals. The exact form
(with the q^R term) and the simple form agree to 4 decimals in every row.

Population bound. For a new vignette drawn from the generating distribution, P(all G vignettes unanimous) =
(E_H[g])^G; maximising E_H[floor] subject to E_H[g] >= 0.05^(1/G) (linear programme over vignette types) gives a
two-point solution: 17.1% of vignettes at q = 0.5 on every action, the rest unanimous. This is the "rule of three"
for 16 vignettes and cannot be tightened without a model for unseen vignettes.

"Every vignette at its own bound" (q_v = 1 - 0.05^(1/R) in every cell) is not a 95% joint bound (its coverage is
far above 95%); listed only because it was requested.

| Floor (printed as 0.000) | G | K | R | Draws N | Fixed-case 95% UB | Population 95% UB | Own-bound max |
|---|---|---|---|---|---|---|---|
| C, D, E temperature 0, pooled five actions | 16 | 5 | 5 | 400 | **0.015** (q_u = 0.0075) | 0.085 | 0.495 |
| C, D, E temperature 0, pooled six actions | 16 | 6 | 5 | 480 | **0.012** (q_u = 0.0062) | 0.085 | 0.495 |
| C, D, E temperature 0, any single action | 16 | 1 | 5 | 80 | 0.071 (q_u = 0.037) | 0.091 | 0.495 |
| E (qwen3:4b) default, ICU escalation (0/720) | 16 | 1 | 10 | 160 | **0.036** (q_u = 0.0185) | 0.086 | 0.384 |
| E (qwen3:4b) default, high acuity (0/720) | 16 | 1 | 10 | 160 | **0.036** | 0.086 | 0.384 |
| F temperature 0: any opioid, ICU, caution (unprinted) | 15 | 1 | 5 | 75 | 0.075 | 0.097 | 0.495 |
| Groq t0: any opioid, ICU, high acuity, caution (unprinted) | 16 | 1 | 5 | 80 | 0.071 | 0.091 | 0.495 |
| Groq t1: ICU escalation (unprinted) | 15 | 1 | 5 | 75 | 0.075 | 0.097 | 0.495 |

Every C/D/E temperature-0 per-action floor is also 0 (all six actions, G=16; the paired and unpaired vignette sets
coincide). Arithmetic check: 0.99^80 = 0.448.

Recommended print: the fixed-case bound, labelled "one-sided 95% upper bound for these 16 vignettes", e.g.
"0.000 (one-sided 95% upper bound 0.015)" for C, D, E at temperature 0 (five actions), and "0.000 (upper bound
0.036)" for qwen3:4b ICU escalation and high acuity. State the population bound once in the SI text (about 0.09:
up to 17% of unseen vignettes could be fully unstable without contradicting 16 unanimous ones).

## 2. Estimands and replicate-only intervals

(i) Fixed-case estimand. The expected floor for this model configuration on the 16 vignettes studied: the
probability that two independent runs on the same vignette give different answers, averaged over these vignettes
and the defined actions. Its only source of uncertainty is run-to-run (replicate) variation; the replicate-only
bootstrap (vignettes fixed, replicates resampled with replacement, pairs of copies of one replicate excluded)
targets it.

(ii) Case-population estimand. The expected floor for a vignette drawn at random from the population of cases of
which the 16 are taken as representative. It adds case-composition uncertainty to replicate uncertainty; the
crossed bootstrap (vignettes and replicates resampled independently) targets it. Because the vignettes were
constructed, not sampled, the population is hypothetical and the crossed interval is a case-composition
sensitivity, not a generalisation guarantee.

Replicate-only 95% intervals (B=5000, random.Random(42), one draw sequence per model in label order):

| Model | R | Five-action floor | Replicate-only | Crossed (printed) | Six-action floor | Replicate-only |
|---|---|---|---|---|---|---|
| A | 10 | 0.068 | [0.051, 0.081] | [0.032, 0.110] | 0.087 | [0.065, 0.101] |
| B | 6 | 0.040 | [0.022, 0.058] | [0.008, 0.081] | 0.067 | [0.031, 0.092] |
| C | 10 | 0.230 | [0.211, 0.246] | [0.184, 0.276] | 0.225 | [0.210, 0.242] |
| D | 10 | 0.098 | [0.084, 0.112] | [0.063, 0.133] | 0.105 | [0.091, 0.119] |
| E | 10 | 0.017 | [0.009, 0.024] | [0.000, 0.041] | 0.035 | [0.026, 0.045] |
| F | 10 | 0.245 | [0.202, 0.286] | [0.182, 0.309] | 0.236 | [0.198, 0.270] |

Model A per action: admission 0.142 [0.105, 0.176]; any opioid 0.025 [0.000, 0.067]; ICU escalation 0.022
[0.000, 0.040]; high acuity 0.076 [0.048, 0.102]; referral 0.075 [0.049, 0.098]; caution flag 0.179
[0.075, 0.236].

Caution: the simulation (section 3) shows the replicate-only interval undercovers the fixed-case estimand
(76-93%), so these intervals should not be printed as calibrated 95% intervals. See section 4.

## 3. Coverage simulation

Design: G=16 vignettes x K=5 actions x R replicates, binary answers; pooled floor and 95% percentile intervals
(crossed, replicate-only, vignette-only) with B=1000; 2000 datasets per scenario. Truths are exact: fixed-case
theta_F = mean_c 2 m_c (1-m_c), m_c = E_u[expit(logit p_c + u)] (Gauss-Hermite), population theta_P by Monte Carlo
over 2,000,000 cells (s.e. <= 0.0001). Estimator bias was nil in every scenario (mean estimate = mean theta_F to
3 decimals). Hybrid = crossed interval if the observed floor > 0, else [0, fixed-case bound of section 1].

Scenarios: S1 q ~ Beta(0.3, 25) (theta_P = 0.023); S2 90% of cells q = 0, else q ~ Beta(1, 19)
(theta_P = 0.009); S3 model A fit by beta-binomial mixture MLE on its 80 five-action cells (45.2% p = 0, 54.8%
Beta(0.626, 0.135); theta_P = 0.069); S4 S3 plus a shared per-replicate logit shift N(0, 0.5^2), giving a
between-replicate variance ratio of 1.72 at R=10 (1.00 at sigma 0; 3.33 at sigma 1.0) and 1.65 at R=6; S5 S4 at
R=6. Difference: scenario model minus an S3-type model (R=10), cells coupled by a Gaussian copula (rho 0.5) on
instability rank, vignette resample shared.

| Scenario | R | Zero-observed | Crossed: fixed | Crossed: population | Rep-only: fixed | Vig-only: population | Hybrid: fixed | Hybrid: population | Diff crossed: fixed / population |
|---|---|---|---|---|---|---|---|---|---|
| S1 sparse | 10 | 0.0% | 99.2 | 98.3 | 87.9 | 90.4 | 99.2 | 98.3 | 100.0 / 98.2 |
| S1 sparse | 5 | 1.7% | 97.7 | 97.5 | 78.9 | 91.5 | 97.8 | 97.5 | 99.8 / 98.3 |
| S2 near-boundary | 10 | 7.0% | 92.9 | 92.8 | 83.7 | 81.3 | 99.3 | 92.8 | 100.0 / 97.2 |
| S2 near-boundary | 5 | 18.2% | 81.8 | 81.7 | 75.9 | 79.9 | 99.8 | 99.9 | 100.0 / 96.9 |
| S3 heterogeneous | 10 | 0% | 100.0 | 96.8 | 92.3 | 92.4 | 100.0 | 96.8 | 100.0 / 97.6 |
| S3 heterogeneous | 5 | 0% | 100.0 | 97.6 | 89.5 | 91.6 | 100.0 | 97.6 | 100.0 / 98.2 |
| S4 replicate dependence | 10 | 0% | 100.0 | 96.1 | 92.5 | 91.6 | 100.0 | 96.1 | 100.0 / 97.4 |
| S5 replicate dependence | 6 | 0% | 100.0 | 97.5 | 90.6 | 91.4 | 100.0 | 97.5 | 100.0 / 97.6 |

Crossed misses are almost all on the low side of the truth (interval below truth): S2 R=5 misses 18.25% that way,
exactly the zero-observed datasets whose interval is [0, 0]. Mean crossed width: 0.044 (S1, R=10) to 0.097 (S3,
R=5). In S2 at R=10 the hybrid does not repair population coverage because the fixed-case bound (0.0074 at
N=800 draws) is below theta_P = 0.0091; it does at R=5 (bound 0.0148).

Readings. The crossed percentile interval is conservative for the fixed-case estimand (97.7-100% except near the
boundary) and close to nominal for the population estimand (96-98%) away from the boundary; between-model
differences cover at 97-100%. It fails where expected: when a sizeable fraction of datasets show
no discordance (S2: 93% at R=10, 82% at R=5). Replacing a [0, 0] interval with the exact one-sided bound restores
>= 99% fixed-case coverage in every scenario. The replicate-only interval undercovers the fixed-case estimand it
targets (76-93%): with 5-10 replicates the resampled U-statistic understates replicate variance and, like any
bootstrap, cannot create discordance in unanimous cells. The vignette-only (pre-crossed) interval undercovers the
population estimand (80-92%), which supports the switch to crossed.

## 4. Recommended wording

Methods/SI: "In simulation (2000 datasets per scenario, 16 vignettes, 5-10 replicates, including heterogeneous
cell rates fitted to model A and shared per-replicate shifts), the crossed percentile intervals covered the
case-population floor in 96-98% of datasets and the fixed-case floor in at least 97%, and between-model differences
in 97-100%. When a substantial fraction of cells is unanimous, coverage fell to 93% at ten replicates and 82% at
five, because a bootstrap cannot produce discordance that was not observed; for floors with no observed
discordance we therefore report an exact one-sided 95% upper bound instead of an interval."

On the fixed-case interval: do not print the replicate-only interval as a 95% interval. Either state that the
crossed interval is conservative for the fixed-case estimand (simulated coverage 97.7-100% away from the boundary)
and use it for both readings, or print replicate-only intervals in the SI labelled as conditional on the 16
vignettes with their simulated coverage (76-93%) stated.

## 5. S12 signed-test simulation: achieved shifts after clipping

Exact expectations over robustness.py item 8's pool (model A's 96 six-action per-cell rates, R=10: 49.0% at
p = 0, 29.2% at p = 1). All V in the table are even, so the opposing scenario is an exact half split.

| Scenario | Nominal | Mean signed shift | Mean absolute shift | Mean squared shift |
|---|---|---|---|---|
| Uniform | +0.10 | +0.071 | 0.071 | 0.0071 |
| Opposing, + half | +0.10 | +0.071 | 0.071 | 0.0071 |
| Opposing, - half | -0.10 | -0.051 | 0.051 | 0.0051 |
| Opposing, overall | +/-0.10 | +0.0099 | 0.061 | 0.0061 |

The table's delta^2 column (0.007, 0.006) matches. The achieved uniform effect is 0.071, not 0.10, and the
"opposing" scenario carries a net signed shift of +0.010, so it is not a zero-net-effect scenario: its rejection
rate at V=300 (0.052) partly reflects that residual drift. The SI should say the nominal effects are clipped and
state the achieved values.
