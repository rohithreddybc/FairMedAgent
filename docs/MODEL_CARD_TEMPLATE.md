# Model Card (template) — per evaluated model × scaffold

*Following Mitchell et al., "Model Cards for Model Reporting" (FAccT 2019). One card per (model, scaffold) config in the FairMedAgent panel; results auto-filled from the eval artifacts at release. `\final{}` = filled after full-panel evaluation.*

## Model details
- **Model + version + date:** \final{e.g., claude-haiku-4-5, run YYYY-MM-DD}
- **Scaffold:** \final{C0 direct | C1 chain-of-thought | C2 two-clinician deliberation}
- **Decoding:** temperature 0; replicates R = \final{R}; per-cell agreement = \final{}
- **Evaluated by:** FairMedAgent harness v\final{x.y.z}

## Intended use
- Research evaluation of demographic action-fairness on the FairMedAgent benchmark. NOT a clinical deployment endorsement.

## Metrics (disaggregated by attribute × domain)
- Within-range disparity, CFR, MASD, signed action-level disparity, with wild-cluster-bootstrap 95% CIs and cluster count G.
- \final{per-attribute × per-domain table for this config}

## Quantitative analysis
- \final{which contrasts are confirmatory (≥25 discordant pairs) vs estimation-only; which survive BH-FDR}
- Cross-step disparity propagation: \final{}

## Ethical considerations & caveats
- In-silico signal on synthetic vignettes; not a patient-outcome estimate.
- Confounded attribute×domain cells reported descriptively only.
- Small G → wide/illustrative per-domain intervals.
- Safety-relevant flips (e.g., analgesia under-treatment) handled via responsible disclosure before public posting.
