The Statistical Analysis Plan is complete and saved.

**File:** `C:\Users\rohit\Documents\Research Papers\FairMedAgent_Statistical_Analysis_Plan.md`

The document (~1,000 words in the body, 12 sections) delivers everything requested, grounded entirely in the verified stats guidance with no fabricated numbers:

- **Formal definitions**: CFR as a metamorphic-relation violation rate `(1/n)Σ1[Y(c)≠Y(c0)]`, MASD `(1/n)Σ|S(c)−S(c0)|`, and signed/directional action-level disparity `Δ_g(Y)=P̂(Y=1|g)−P̂(Y=1|ref)` with the ordinal net-up-shift analogue `Δ⁺`.
- **Estimators**: plug-in/empirical, on aggregated cells, with the explicit estimand decision (population-average descriptive gap is the leaderboard number, not the GLMM conditional coefficient).
- **95% CI**: cluster (block) bootstrap resampling whole vignettes, B=10,000, percentile/BCa; Wilson only as a sanity check; near-lower-bound cluster-count limitation stated.
- **Multiple comparisons**, two-tier: Holm for the PRIMARY family, Benjamini–Hochberg FDR at q=0.05 for the SECONDARY exploded grid, with the BH rejection rule written out.
- **Paired test**: McNemar mid-P primary (Fagerland 2013), `χ²=(b−c)²/(b+c)`, exact-binomial fallback below 25 discordant pairs, with the explicit "do not use exact-conditional / continuity-corrected" rule.
- **Mixed-effects model**: full GLMM logit equation with crossed random intercepts (vignette/model/scaffold), proportional-odds for ordinal tiers, LMM for urgency, plus the conditional-vs-marginal caveat and GEE alternative.
- **PRIMARY vs SECONDARY endpoints**: four named confirmatory cells; everything else (incl. intersections) hypothesis-generating pending the sealed split.
- **Sample size/power**: McNemar power as a function of `p_discordant`, pilot-seeded calculation, pre-registered 10-pp MDE at 80% power, ≥25 discordant pairs/cell target.
- **Intersectional small-N rules**: minimum cell size, mandatory N+CI, strength-borrowing, Bayesian beta-binomial credible intervals, FDR + sealed-split confirmation.
- **Ceiling-effect handling**: 5%/95% flagging, latent-scale (cumulative-link) analysis, and the load-bearing distinction between "consistent (no flip)" and "unmeasurable due to ceiling."

A test-choice-by-action-type table and a pre-registration freeze statement close it out. Note: per the precedent guidance the document deliberately holds to the no-fabricated-numbers honesty bar: the pilot `p_discordant`, actual CFR/MASD values, and final vignette/replicate counts are left as placeholders to be filled from a real `audit_harness.js` run, not invented.