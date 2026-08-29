# Scenario and action-space design

The design covers the following.
- **4 action domains** (D1 triage/escalation, D2 diagnostic+lab ordering, D3 medication management, D4 documentation+disposition) in a table flagging D3/D4 as net-new vs Omar.
- **Per-domain vignette template**: a shared YAML envelope with a swappable `patient` block and a frozen `clinical_core`, plus per-domain specializations.
- **Action/output schema per task**: exact JSON per domain with label sets (closed order vocab, 4-level analgesia factor, 3-level dosing), ordinal ranges (ESI 1–5), and the 0–100 urgency score, with the test mapping (McNemar mid-p / cumulative-link / MASD).
- **Counts + difficulty calibration**: ~30–40 base vignettes (~8–10/domain), easy/moderate/hard split with rationale, depth-over-breadth framed as a limitation, Krippendorff α reported.
- **Acceptable-answer / reasonable-range rubric**: acceptable sets per primitive, plus the two derived signals (within-range disparity and out-of-range flips) that make "disparity ≠ wrongness" load-bearing.
- **2 synthetic example vignettes** (chest pain D1; long-bone fracture D3) with frozen cores, counterfactual patient swaps, and concrete rubric + agent-output JSON.

It is anchored to metamorphic counterfactual design, PROGRESS-Plus attribute justification,
STANDING Together and Datasheets dataset documentation, TRIPOD-LLM reporting, and DRAGON's
Krippendorff alpha convention.