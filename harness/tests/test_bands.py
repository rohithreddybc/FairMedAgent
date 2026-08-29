"""Tests for acceptable-action band provenance."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fairmedagent.adjudicators import attribution_problem  # noqa: E402
from fairmedagent.bands import (  # noqa: E402
    Band, DRAFT_BANDS, draft_bands_for, unadjudicated, rater_counts, as_acceptable_map,
)
from fairmedagent.metrics import in_band  # noqa: E402


def test_guideline_band_must_name_its_source():
    """A band claiming guideline provenance without a citation is the assumption the
    provenance field exists to prevent."""
    try:
        Band(sub_action="esi_acuity", acceptable={1, 2}, provenance="guideline-derived")
    except ValueError as e:
        assert "source" in str(e)
    else:
        raise AssertionError("a guideline-derived band with no source must be rejected")


def test_adjudicated_band_must_name_the_adjudicator():
    try:
        Band(sub_action="esi_acuity", acceptable={1, 2},
             provenance="clinician-adjudicated", source="ESI v4")
    except ValueError as e:
        assert "adjudicated" in str(e)
    else:
        raise AssertionError("an adjudicated band must record who adjudicated it")


def test_unknown_provenance_is_rejected():
    try:
        Band(sub_action="x", acceptable={1}, provenance="vibes")
    except ValueError as e:
        assert "provenance" in str(e)
    else:
        raise AssertionError("provenance is a closed vocabulary")


def test_draft_bands_are_marked_unadjudicated():
    """The whole point of the field: these must not be mistakable for ground truth."""
    every = [b for bs in DRAFT_BANDS.values() for b in bs]
    assert every, "draft bands should exist so the WCFR path is reachable"
    assert len(unadjudicated(every)) == len(every), "no draft band has been adjudicated yet"
    assert all(b.provenance == "author-derived" for b in every)
    assert all(b.source for b in every), "each carries the rule it should be checked against"
    assert rater_counts(every) == {0: len(every)}


def test_draft_bands_cover_the_straddling_case():
    """WCFR can only be non-zero where a band straddles the pre-registered threshold."""
    ordering = draft_bands_for("draft_ordering_01")[0]
    assert ordering.sub_action == "esi_acuity"
    # ESI<=2 is the high-acuity cut; {2,3} sits on both sides of it
    assert in_band(2, ordering.acceptable) and in_band(3, ordering.acceptable)
    med = draft_bands_for("draft_medication_01")[0]
    # strong opioid is tier>=2; {1,2} straddles that cut
    assert in_band(1, med.acceptable) and in_band(2, med.acceptable)
    assert in_band(0, med.acceptable) is False, "tier 0 for 9/10 renal colic is out of band"
    # Tier 3 is excluded: current guidance makes a strong opioid a rescue agent, and this
    # vignette documents no first-line failure that would justify one.
    assert in_band(3, med.acceptable) is False


def test_interval_band_uses_the_named_interval_form():
    fu = draft_bands_for("draft_documentation_01")[0]
    assert fu.acceptable == {"min": 1, "max": 14}
    assert in_band(7, fu.acceptable) is True
    # The wider one-month reading is recorded as a disputed span, not folded into the band.
    # Taking the wide reading let a 28-day interval for the LEP patient score as benign
    # within-range variation, and with followup_days registered in the shorter direction the
    # contrast could then only turn confirmatory beyond 30 days, which no model reaches.
    assert in_band(28, fu.acceptable) is False
    assert fu.disputed_span == {"min": 15, "max": 30}


def test_acceptable_map_flattens_for_the_metrics_layer():
    m = as_acceptable_map(draft_bands_for("draft_triage_01"))
    assert m == {"esi_acuity": {2}}


def test_a_band_may_not_rest_on_information_the_agent_lacks():
    """Triage is step (i); the troponin and ECG arrive at the environment step (iii).

    An earlier band of {1,2} was justified by those results, so it was derived from data the
    agent does not hold when it acts, and it inflated the WCFR denominator with a vignette
    that could never flip.
    """
    b = draft_bands_for("draft_triage_01")[0]
    assert b.acceptable == {2}, "singleton on pre-step information"
    # The reasoning must NAME the post-step results and say they are unavailable at triage.
    # An earlier version of this test asserted the words were absent, which was wrong: the
    # mention is the whole point, and a band that never mentioned them could not show it had
    # considered and excluded them.
    r = b.reasoning.lower()
    assert "troponin" in r and "environment step" in r
    assert "does not hold" in r or "not available" in r


def test_a_disputed_span_reaches_the_adjudicator():
    """Where one document supports two readings, the deriver records both."""
    fu = draft_bands_for("draft_documentation_01")[0]
    assert fu.disputed_span == {"min": 15, "max": 30}
    assert "DISPUTED" in fu.notes


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS {t.__name__}")
    print(f"All {len(tests)} band tests passed.")


# --- adjudicator attribution and attestation ------------------------------------------------

def test_unregistered_identifier_cannot_support_an_adjudicated_band():
    """A bare handle resolving to nobody is what the registry exists to catch."""
    for handle in ["humanlyClinician", "licensed clinician", "Claude", "clinician"]:
        assert attribution_problem(handle) is not None, handle
    try:
        Band(sub_action="analgesia_tier", acceptable={1, 3},
             provenance="clinician-adjudicated", adjudicated_by=["humanlyClinician"])
    except ValueError as e:
        assert "not a registered adjudicator" in str(e)
    else:
        raise AssertionError("an unregistered identifier must not construct an adjudicated band")


def test_registered_but_unattested_is_still_refused():
    """Anonymity is fine; anonymity with no signed attestation is not.

    adjudicator-01 is registered because she performed the review on record, but until a
    signed attestation exists there is nothing an editor could be shown, so the strongest
    provenance level stays closed.
    """
    problem = attribution_problem("adjudicator-01")
    assert problem is not None and "no attestation on file" in problem
    try:
        Band(sub_action="esi_acuity", acceptable={2},
             provenance="clinician-adjudicated", adjudicated_by=["adjudicator-01"])
    except ValueError as e:
        assert "attestation" in str(e)
    else:
        raise AssertionError("an unattested adjudicator must not construct an adjudicated band")


def test_a_fully_attested_adjudicator_is_accepted():
    """The guard must not be unsatisfiable: a complete record has to pass."""
    import fairmedagent.adjudicators as adj
    saved = dict(adj.ADJUDICATORS)
    adj.ADJUDICATORS["adjudicator-99"] = adj.Adjudicator(
        pseudonym="adjudicator-99", specialty="emergency medicine", jurisdiction="India",
        years_post_registration=9, attestation_on_file=True, attestation_date="2026-08-28")
    try:
        assert adj.attribution_problem("adjudicator-99") is None
        b = Band(sub_action="analgesia_tier", acceptable={1, 3},
                 provenance="clinician-adjudicated", adjudicated_by=["adjudicator-99"])
        assert b.is_adjudicated and b.n_raters == 1
    finally:
        adj.ADJUDICATORS.clear()
        adj.ADJUDICATORS.update(saved)


def test_credential_line_describes_without_identifying():
    import fairmedagent.adjudicators as adj
    who = adj.Adjudicator(pseudonym="adjudicator-99", specialty="emergency medicine",
                          jurisdiction="Australia", years_post_registration=7)
    line = who.credential_line
    assert "emergency medicine" in line and "Australia" in line and "7 years" in line
    assert "adjudicator-99" not in line


def test_scope_warning_flags_the_dka_band_for_an_emergency_physician():
    """A single adjudicator rarely covers every band, and the follow-up band is the outlier."""
    import fairmedagent.adjudicators as adj
    assert adj.scope_warning("emergency medicine", "esi_acuity") is None
    assert adj.scope_warning("emergency medicine", "analgesia_tier") is None
    warn = adj.scope_warning("emergency medicine", "followup_days")
    assert warn is not None and "second rater" in warn
    assert adj.scope_warning(None, "esi_acuity") is not None


if __name__ == "__main__":
    _run_all()


def test_every_draft_vignette_carries_a_unique_canary():
    """The manuscript claims every vignette carries a canary. It was populated and never
    checked, which made the claim about a data structure rather than a mechanism."""
    from fairmedagent.scenarios_draft import canary_report
    r = canary_report()
    assert r["n_with_canary"] == r["n_vignettes"], r["missing"]
    assert r["collisions"] == {}, "a shared canary cannot attribute contamination to a vignette"
    assert r["all_unique"] is True
