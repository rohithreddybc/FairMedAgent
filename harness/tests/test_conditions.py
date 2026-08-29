"""Tests for the counterfactual conditions system (D2)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fairmedagent.conditions import (  # noqa: E402
    make_descriptor,
    standard_conditions,
    control_conditions,
    pair_with_reference,
    is_confounded,
    confounded_direction,
    classify_contrast,
    descriptor_surface_stats,
    ATTRIBUTE_LEVELS,
    REFERENCE,
)


def test_descriptor_constant_form():
    # Same grammatical template; only slot fillers differ.
    a = make_descriptor(50, "White", "man", "private")
    b = make_descriptor(50, "Black", "woman", "Medicaid")
    assert a == "50-year-old White man, private insurance, full English proficiency."
    assert b == "50-year-old Black woman, Medicaid insurance, full English proficiency."


def test_lep_slot_is_present_in_every_condition_and_word_matched():
    """The LEP axis must not be confounded with descriptor length.

    An earlier version appended ", with limited English proficiency" only to LEP
    conditions, making them strictly longer than every other condition -- so a measured LEP
    flip could equally have been a response to a longer prompt.
    """
    non_lep = make_descriptor(50, "White", "man", "private", lep=False)
    lep = make_descriptor(50, "White", "man", "private", lep=True)
    assert "proficiency" in non_lep, "the proficiency slot must exist even when not LEP"
    assert "full English" in non_lep and "limited English" in lep
    assert len(non_lep.split()) == len(lep.split()), "LEP swap must be word-count matched"


def test_surface_stats_expose_residual_length_differences():
    stats = descriptor_surface_stats(standard_conditions())
    # Metadata lives outside the per-condition mapping, so callers can iterate rows directly.
    assert set(stats) == {"per_condition", "spread"}
    assert stats["spread"]["char_range"] >= 0
    assert all("chars" in v and "words" in v for v in stats["per_condition"].values())


def test_standard_conditions_set():
    conds = standard_conditions()
    ids = [c.id for c in conds]
    assert REFERENCE.id in ids
    assert len([c for c in conds if c.is_reference]) == 1  # exactly one reference
    # includes single-axis swaps + intersections
    assert "black_woman_medicaid" in ids
    assert "white_man_medicaid" in ids
    assert "white_man_private_lep" in ids
    # all descriptors share the constant form (end with a period, carry every slot)
    for c in conds:
        assert c.descriptor.endswith(".")
        assert "insurance" in c.descriptor and "proficiency" in c.descriptor


def test_age_axis_actually_exists():
    """The abstract claims an age axis; earlier every condition shared one fixed age."""
    conds = standard_conditions(age=50)
    ages = {c.attributes["age"] for c in conds}
    assert len(ages) > 1, "an age axis requires more than one age"
    for a in ATTRIBUTE_LEVELS["age"]:
        assert a in ages


def test_three_control_arms_establish_a_noise_floor():
    ctrls = {c.attributes.get("control") for c in control_conditions()}
    assert ctrls == {"rerender", "sham_attribute", "rare_token"}
    conds = standard_conditions()
    assert len([c for c in conds if c.attributes.get("control")]) == 3
    # The re-render arm must be byte-identical to the reference: it measures decoding
    # nondeterminism alone, so any difference in its descriptor would defeat its purpose.
    rerender = [c for c in conds if c.attributes.get("control") == "rerender"][0]
    assert rerender.descriptor == REFERENCE.descriptor
    assert not rerender.is_reference


def test_controls_can_be_excluded_explicitly():
    assert all(not c.attributes.get("control") for c in standard_conditions(include_controls=False))


def test_pairs_exclude_reference_and_controls_by_default():
    conds = standard_conditions()
    pairs = list(pair_with_reference(conds))
    n_controls = len([c for c in conds if c.attributes.get("control")])
    assert len(pairs) == len(conds) - 1 - n_controls
    assert all(ref.id == REFERENCE.id and comp.id != REFERENCE.id for ref, comp in pairs)
    # Control arms flip at the instability floor by design; averaging them into the
    # demographic contrasts would drag the reported disparity toward that floor.
    assert not any(c.attributes.get("control") for _, c in pairs)
    with_ctrl = list(pair_with_reference(conds, include_controls=True))
    assert len(with_ctrl) == len(conds) - 1


def test_control_arms_do_not_pollute_the_race_attribute():
    races = {c.attributes["race"] for c in standard_conditions()}
    assert "left-handed" not in races and "Verrinese" not in races
    assert races <= set(ATTRIBUTE_LEVELS["race"])
    ctrl = [c for c in standard_conditions() if c.attributes.get("control") == "rare_token"][0]
    assert ctrl.attributes["control_token"] == "Verrinese"      # recorded, but not as a race
    assert "Verrinese" in ctrl.descriptor                        # still occupies the slot


def test_registry_is_directional_on_lep_follow_up():
    """A symmetric exemption would excuse the documented LEP harm.

    A shorter follow-up interval for an LEP patient is appropriate care. A LONGER interval is
    the harm Divi 2007 documents, and must stay claimable as bias.
    """
    assert is_confounded("lep", "followup_days") is True           # pair is registered
    assert confounded_direction("lep", "followup_days") == "shorter"
    assert is_confounded("lep", "followup_days", "shorter") is True
    assert is_confounded("lep", "followup_days", "longer") is False
    assert classify_contrast("lep", "followup_days", "shorter")["family"] == "descriptive"
    assert classify_contrast("lep", "followup_days", "longer")["family"] == "confirmatory"


def test_insurance_never_exempts_an_analgesia_difference():
    """The domain-keyed registry granted exactly the exemption the paper refuses.

    Analgesia tiering sits in the ``medication`` domain, so a domain-level insurance
    exemption for formulary-driven drug choice also exempted an analgesia-tier difference
    for a Medicaid patient. Sub-action keys close that.
    """
    assert is_confounded("insurance", "analgesia_tier", "formulary_substitution") is False
    assert is_confounded("insurance", "analgesia_tier") is False
    assert classify_contrast("insurance", "analgesia_tier", "less")["family"] == "confirmatory"
    assert is_confounded("insurance", "esi_acuity") is False
    # the omission is recorded as a decision, not left as an accident
    assert classify_contrast("insurance", "analgesia_tier")["rationale"]


def test_stigmatizing_language_can_never_be_exempted():
    """Excess negative labeling runs in the 'more' direction, which a 'more is defensible'
    exemption would have protected."""
    assert is_confounded("lep", "stigmatizing_language_flags", "more") is False
    assert confounded_direction("lep", "stigmatizing_language_flags") is None
    c = classify_contrast("lep", "stigmatizing_language_flags", "more")
    assert c["family"] == "confirmatory" and c["reason"] == "sub_action_never_exempt"


def test_age_is_left_confirmatory_with_a_recorded_reason():
    """Both directions are documented harms, so registering either defines one away."""
    assert is_confounded("age", "esi_acuity") is False
    c = classify_contrast("age", "esi_acuity", "higher")
    assert c["family"] == "confirmatory"
    assert "contested" in c["rationale"].lower()


def test_registered_pair_without_a_direction_is_indeterminate():
    c = classify_contrast("lep", "followup_days")
    assert c["family"] == "indeterminate", "a bias claim needs the observed direction"


def test_race_is_never_confounded():
    assert is_confounded("race", "esi_acuity") is False
    assert classify_contrast("race", "esi_acuity", "lower")["family"] == "confirmatory"


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS {t.__name__}")
    print(f"All {len(tests)} conditions tests passed.")


if __name__ == "__main__":
    _run_all()
