# Responsible-disclosure SOP — FairMedAgent

*Because FairMedAgent can surface safety-relevant demographic flips in deployed/vendor models (e.g., systematic analgesia under-treatment for a demographic group), we follow coordinated disclosure before publicly posting model-identifying safety findings. Referenced by the paper's Ethics section and the Datasheet.*

## Scope
Applies to **safety-relevant, model-identifying** results — a named model showing a systematic, clinically consequential disparity (controlled-substance/analgesia under-treatment, under-triage, escalation denial) for a protected group. Aggregate/methodological results and the dev split are released openly and are not gated.

## Procedure
1. **Detect + confirm.** Result survives the confirmatory bar (≥25 independent discordant pairs, BH-FDR) or is flagged as a clear safety pattern in the pilot; confirm it is within-range (not a correctness artifact).
2. **Notify the vendor.** Contact the model provider's security/responsible-AI channel with the specific finding, reproduction (harness version, seeds, prompts), and severity.
3. **Remediation window.** Allow **30 days** (extendable by mutual agreement) before public posting of the model-identifying safety finding on the leaderboard/preprint. Aggregate results may publish; the model may be shown de-identified during the window if needed.
4. **Publish.** After the window, post results with the vendor's response noted where provided. If a vendor requests a short extension in good faith, accommodate reasonably.
5. **Log.** Record disclosure date, vendor, finding, and response in a private disclosure log (not the public repo).

## Leaderboard governance
- Held-out labels stored privately; submissions attested + spot re-run.
- No self-population; ≥3 unrelated groups required before claiming external adoption.
- Sunset plan: if unmaintained > [12] months, freeze the leaderboard and archive the sealed split's evaluation script so results remain reproducible.

## Contacts (fill before release)
- Vendor security contacts: [Anthropic / OpenAI / Google / Meta responsible-AI channels]
- Maintainer: Rohith Reddy [email]
