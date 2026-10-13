# Dependence-robust zero-discordance bounds (v4)

Code: harness/scripts/zero_bounds_v4.py -> experiments/zero_bounds_v4.json. Coverage check: harness/scripts/coverage_sim.py --v4 -> experiments/COVERAGE_SIM_v4.json.

Method. A vignette is one unit with floor F_v = mean_k 2 q_vk (1 - q_vk). P(vignette v all-unanimous) <= min_k U(f_vk) <= U(F_v), U(f) = (1-q)^R + q^R with q the smaller root of f = 2q(1-q) (U is decreasing in f and F_v <= max_k f_vk). Vignettes are independent, so P(all unanimous) <= prod_v U(F_v). The bound is max mean_v F_v subject to prod_v U(F_v) >= 0.05.

Maximum is at equal F_v. log U(F) is concave on [0, 0.5] for R=5 and R=10 (no positive second difference on a 2001-point grid). Two-level search (m vignettes at a, V-m at b, 4001-point grid plus refinement) and 300 SLSQP multi-starts (seed 42) return the equal-F value in every case (differences < 1e-6). K does not enter: five-action and six-action pooled bounds coincide.

| case | old (independence) | new (dependence-robust) |
|---|---|---|
| pooled 5-action, R=5, V=16 | 0.0148 | 0.0708 |
| pooled 6-action, R=5, V=16 | 0.0124 | 0.0708 |
| one action, R=10, V=16 | 0.0364 | 0.0364 |
| one action, R=5, V=16 | 0.0708 | 0.0708 |
| one action, R=5, V=15 | 0.0752 | 0.0752 |

Unseen-vignette (case-population) bound with vignette as the unit: 0.0911 (R=5, V=16), 0.0855 (R=10, V=16), 0.0966 (R=5, V=15); old five-action value 0.0854.

Inequality P(all unanimous) <= U(F) by brute force: K=2..6, R=5 and 10, 480,000 Dirichlet joint distributions per cell plus 60 Nelder-Mead/BFGS adversarial searches. Max violation 2.2e-15 (float rounding); identical actions give equality.

Counterexample (five identical actions, q=0.02, V=16, R=5; true floor 0.0392): P(all unanimous) = 0.198649 exact, 0.198687 by 2,000,000-draw Monte Carlo (seed 42). The old 0.0148 bound is below the truth in all of those runs, so P(zero observed and truth > bound) = 0.198687. New bound 0.0708 is above the truth: 0.0.
