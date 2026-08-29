"""Tests for the FairMedAgent core metrics. Pure stdlib + pytest-free runnable.

Run directly:  python tests/test_metrics.py   (prints OK or raises)
Or via pytest: pytest tests/
"""
import itertools
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fairmedagent.metrics import (  # noqa: E402
    Pair,
    counterfactual_flip_rate,
    within_range_flip_rate,
    wcfr_statistic,
    in_band,
    band_straddles,
    disparity_propagation,
    mean_absolute_score_difference,
    action_level_disparity,
    positive_rate,
    cluster_bootstrap_ci,
    mcnemar_exact,
    benjamini_hochberg,
    benjamini_yekutieli,
    WEBB_WEIGHTS,
    _cluster_robust_mean,
    wild_cluster_bootstrap_p,
    wild_cluster_bootstrap_ci,
    paired_values_by_cluster,
    signed_flip_value,
    paired_permutation_test,
    signed_ordinal_disparity,
    interventional_propagation,
    capability_floor_gate,
    trajectory_accumulation,
)


def _approx(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_cfr_basic():
    pairs = [
        Pair("v1", action_ref=True, action_cf=True),    # no flip
        Pair("v2", action_ref=True, action_cf=False),   # flip
        Pair("v3", action_ref=False, action_cf=False),  # no flip
        Pair("v4", action_ref=False, action_cf=True),   # flip
    ]
    assert _approx(counterfactual_flip_rate(pairs), 0.5)
    assert counterfactual_flip_rate([]) is None


def test_masd_basic():
    pairs = [
        Pair("v1", score_ref=80, score_cf=70),  # 10
        Pair("v2", score_ref=50, score_cf=50),  # 0
        Pair("v3", score_ref=20, score_cf=35),  # 15
    ]
    assert _approx(mean_absolute_score_difference(pairs), (10 + 0 + 15) / 3)


def test_disparity_and_positive_rate():
    rate_a = positive_rate([True, True, True, False])   # 0.75
    rate_b = positive_rate([True, False, False, False])  # 0.25
    assert _approx(rate_a, 0.75)
    assert _approx(rate_b, 0.25)
    assert _approx(action_level_disparity(rate_a, rate_b), 0.5)  # group A favored


def test_mcnemar_detects_imbalance():
    # Strong directional flip: many ref+/cf- (b), few c -> small p-value
    pairs = [Pair(f"v{i}", action_ref=True, action_cf=False) for i in range(15)]
    pairs += [Pair("vx", action_ref=False, action_cf=True)]
    res = mcnemar_exact(pairs)
    assert res["b"] == 15 and res["c"] == 1
    assert res["p_value"] < 0.01
    # No discordance -> p = 1.0
    concordant = [Pair("a", action_ref=True, action_cf=True)]
    assert mcnemar_exact(concordant)["p_value"] is None  # undefined, not a null result


def test_bootstrap_ci_orders_and_covers():
    # All flips -> CFR is 1.0 everywhere; CI should be a degenerate [1.0, 1.0]
    pairs = [Pair(f"v{i}", action_ref=True, action_cf=False) for i in range(20)]
    lo, hi = cluster_bootstrap_ci(pairs, counterfactual_flip_rate, n_boot=500, seed=1)
    assert lo is not None and hi is not None
    assert lo <= hi
    assert _approx(lo, 1.0) and _approx(hi, 1.0)
    # Mixed -> CI brackets the point estimate 0.5
    mixed = [Pair(f"v{i}", action_ref=True, action_cf=(i % 2 == 0)) for i in range(40)]
    point = counterfactual_flip_rate(mixed)
    lo2, hi2 = cluster_bootstrap_ci(mixed, counterfactual_flip_rate, n_boot=1000, seed=2)
    assert lo2 <= point <= hi2


def test_bootstrap_resamples_vignettes_not_rows():
    # Ten vignettes, each contributing 5 replicate-level pairs. Every replicate of a vignette
    # agrees, so the only real information is 10 clusters, not 50 rows. A flat row-resample
    # would treat this as n=50 and return a spuriously tight interval; clustering must not.
    pairs = []
    for i in range(10):
        flip = i < 5
        for _ in range(5):
            pairs.append(Pair(f"v{i}", action_ref=True, action_cf=(not flip)))
    lo, hi = cluster_bootstrap_ci(pairs, counterfactual_flip_rate, n_boot=800, seed=3)
    point = counterfactual_flip_rate(pairs)
    assert _approx(point, 0.5)
    assert lo <= point <= hi
    # 10 clusters at p=0.5: the clustered interval is wide. A row-level resample of 50
    # independent draws would give roughly [0.36, 0.64]; anything that tight means the
    # replicate correlation was ignored.
    assert hi - lo > 0.30


def test_bootstrap_is_invariant_to_replicate_duplication():
    # Duplicating every pair adds no clusters and therefore must not narrow the interval.
    base = [Pair(f"v{i}", action_ref=True, action_cf=(i % 2 == 0)) for i in range(12)]
    dup = [p for p in base for _ in range(4)]
    lo_b, hi_b = cluster_bootstrap_ci(base, counterfactual_flip_rate, n_boot=600, seed=5)
    lo_d, hi_d = cluster_bootstrap_ci(dup, counterfactual_flip_rate, n_boot=600, seed=5)
    assert _approx(lo_b, lo_d) and _approx(hi_b, hi_d)


def test_benjamini_hochberg():
    pvals = [0.001, 0.01, 0.02, 0.5, 0.9]
    res = benjamini_hochberg(pvals, alpha=0.05)
    assert len(res["qvalues"]) == 5
    # q-values are monotonic non-decreasing in original p-order here
    assert res["rejected"][0] is True   # 0.001 clearly survives FDR
    assert res["rejected"][4] is False  # 0.9 does not
    # all q-values within [0,1]
    assert all(0.0 <= q <= 1.0 for q in res["qvalues"])


def _run_all():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
        print(f"  PASS {t.__name__}")
    print(f"All {len(tests)} metric tests passed.")




def test_in_band_is_membership_unless_an_interval_is_named():
    assert in_band(2, {1, 2, 3}) is True
    assert in_band(5, {1, 2, 3}) is False
    # A two-element tuple is a SET of two acceptable actions, never an implicit range.
    # Reading (1, 5) as "1 through 5" silently widened a clinician band and admitted
    # clinically unacceptable actions into the within-range denominator.
    assert in_band(3, (1, 5)) is False
    assert in_band(5, (1, 5)) is True
    # An interval has to be asked for by name.
    assert in_band(3, {"min": 1, "max": 5}) is True
    assert in_band(6, {"min": 1, "max": 5}) is False
    assert in_band(2, range(1, 4)) is True
    assert in_band(None, {1, 2}) is None       # unknown action -> NA, not False
    assert in_band(2, None) is None            # missing clinician band -> NA, not False


def test_wcfr_counts_only_pairs_with_both_variants_in_band():
    pairs = [
        # in band both sides, flipped -> counts in numerator and denominator
        Pair("v1", action_ref=True,  action_cf=False, in_band_ref=True,  in_band_cf=True,
             straddles_threshold=True),
        # in band both sides, stable -> denominator only
        Pair("v2", action_ref=True,  action_cf=True,  in_band_ref=True,  in_band_cf=True,
             straddles_threshold=False),
        # flipped but the counterfactual action is OUT of band -> excluded entirely,
        # because that is a clinical error rather than demographic sensitivity
        Pair("v3", action_ref=True,  action_cf=False, in_band_ref=True,  in_band_cf=False),
    ]
    r = within_range_flip_rate(pairs, bands=[])
    assert r["n_in_band"] == 2
    assert r["n_flips_in_band"] == 1
    assert r["n_excluded_out_of_band"] == 1
    # The headline rate is restricted to straddling vignettes: a band wholly on one side of
    # the threshold cannot produce a flip, so counting it would make the rate depend on band
    # composition rather than agent behaviour. The all-in-band rate is kept as secondary.
    assert _approx(r["wcfr_all_in_band"], 0.5)
    assert _approx(r["wcfr"], 1.0)          # 1 flip over 1 straddling vignette
    # The estimator refuses to infer straddling from observed flips: if any in-band pair
    # lacks the flag it returns None rather than guessing, because inferring it from flips
    # would make a well-behaved agent look like it had no straddling vignettes at all.
    # the out-of-band flip DOES inflate the plain CFR -- this gap is the whole point
    assert _approx(counterfactual_flip_rate(pairs), 2 / 3)


def test_wcfr_is_na_not_zero_when_no_pair_is_in_band():
    pairs = [Pair("v1", action_ref=True, action_cf=False, in_band_ref=False, in_band_cf=True)]
    r = within_range_flip_rate(pairs, bands=[])
    assert r["wcfr"] is None, "empty denominator must report NA, never 0.0"
    assert r["n_in_band"] == 0
    assert wcfr_statistic(pairs) is None


def test_wcfr_bootstrap_ci_runs_over_the_headline_statistic():
    pairs = [
        Pair(f"v{i}", action_ref=True, action_cf=(i % 2 == 0), in_band_ref=True,
             in_band_cf=True, straddles_threshold=True)
        for i in range(8)
    ]
    lo, hi = cluster_bootstrap_ci(pairs, wcfr_statistic, n_boot=200, seed=1)
    assert lo is not None and hi is not None
    assert 0.0 <= lo <= hi <= 1.0


def test_propagation_detects_downstream_disparity_carried_from_upstream():
    # v1,v2 flip upstream and also flip downstream; v3,v4 stable upstream and downstream
    upstream = [
        Pair("v1", action_ref=True, action_cf=False),
        Pair("v2", action_ref=True, action_cf=False),
        Pair("v3", action_ref=True, action_cf=True),
        Pair("v4", action_ref=True, action_cf=True),
    ]
    downstream = [
        Pair("v1", action_ref=True, action_cf=False),
        Pair("v2", action_ref=True, action_cf=False),
        Pair("v3", action_ref=True, action_cf=True),
        Pair("v4", action_ref=True, action_cf=True),
    ]
    r = disparity_propagation(upstream, downstream)
    assert _approx(r["downstream_cfr_given_upstream_flip"], 1.0)
    assert _approx(r["downstream_cfr_given_upstream_stable"], 0.0)
    assert _approx(r["propagation"], 1.0)
    assert r["n_upstream_flipped"] == 2 and r["n_upstream_stable"] == 2


def test_propagation_is_na_when_a_stratum_is_empty():
    upstream = [Pair("v1", action_ref=True, action_cf=True)]     # nothing flips upstream
    downstream = [Pair("v1", action_ref=True, action_cf=False)]
    r = disparity_propagation(upstream, downstream)
    assert r["downstream_cfr_given_upstream_flip"] is None
    assert r["propagation"] is None, "an empty stratum must not collapse to a numeric 0"
    assert r["n_upstream_flipped"] == 0


def test_propagation_reports_excess_over_single_call_baseline():
    upstream = [Pair("v1", action_ref=True, action_cf=False),
                Pair("v2", action_ref=True, action_cf=True)]
    downstream = [Pair("v1", action_ref=True, action_cf=False),
                  Pair("v2", action_ref=True, action_cf=True)]
    baseline = [Pair("v1", action_ref=True, action_cf=True),
                Pair("v2", action_ref=True, action_cf=True)]
    r = disparity_propagation(upstream, downstream, baseline=baseline)
    assert _approx(r["baseline_cfr"], 0.0)
    assert _approx(r["vs_baseline"], 0.5)
    assert r["n_baseline"] == 2


def test_permutation_refuses_label_symmetric_statistics():
    """CFR cannot be permuted, and the API must say so instead of returning p=1.0.

    CFR counts action_ref != action_cf, which is unchanged by the very swap that generates
    the null, so its reference distribution is a point mass. Returning 1.0 would read as a
    null result rather than as an inapplicable test.
    """
    pairs = [Pair(f"v{i}", action_ref=True, action_cf=(i % 3 == 0)) for i in range(9)]
    r = paired_permutation_test(pairs, counterfactual_flip_rate)
    assert r["degenerate"] is True
    assert r["p_value"] is None, "a degenerate null must not be reported as p=1.0"
    assert "invariant" in r["reason"]
    # WCFR and MASD are symmetric for the same reason.
    w = [Pair(f"v{i}", action_ref=True, action_cf=(i % 3 == 0), in_band_ref=True,
              in_band_cf=True, straddles_threshold=True)
         for i in range(9)]
    assert paired_permutation_test(w, wcfr_statistic)["degenerate"] is True
    m = [Pair(f"v{i}", score_ref=2, score_cf=2 + (i % 3)) for i in range(9)]
    r_m = paired_permutation_test(m, mean_absolute_score_difference)
    assert r_m["n"] == 9, "score-only pairs must not be silently dropped"
    assert r_m["degenerate"] is True


def test_permutation_is_exact_and_valid_for_a_signed_statistic():
    pairs = [Pair(f"v{i}", action_ref=True, action_cf=False) for i in range(8)]
    r = paired_permutation_test(pairs, lambda ps: action_level_disparity(
        positive_rate([p.action_cf for p in ps]), positive_rate([p.action_ref for p in ps])))
    assert r["exact"] is True and r["degenerate"] is False
    assert r["n_reference_draws"] == 2 ** 8
    assert r["p_value"] <= 2 / 2 ** 8, "an all-one-direction shift must be extreme"


def test_permutation_test_on_a_signed_statistic_discriminates():
    def signed_rate(ps):
        v = [p for p in ps if p.action_ref is not None and p.action_cf is not None]
        if not v:
            return None
        return sum(1 for p in v if p.action_cf) / len(v) - sum(1 for p in v if p.action_ref) / len(v)
    pairs = [Pair(f"v{i}", action_ref=True, action_cf=False) for i in range(8)]
    r = paired_permutation_test(pairs, signed_rate)
    assert r["exact"] is True
    # only the all-unswapped assignment reproduces the observed extreme, plus its mirror
    assert r["p_value"] <= 2 / 2 ** 8


def test_permutation_test_returns_na_on_empty_input():
    r = paired_permutation_test([], counterfactual_flip_rate)
    assert r["p_value"] is None and r["n"] == 0


def test_signed_ordinal_disparity_separates_direction_from_magnitude():
    # systematic one-level UNDER-triage (higher ESI number = lower acuity)
    systematic = [Pair(f"v{i}", score_ref=2, score_cf=3) for i in range(6)]
    # symmetric noise: same absolute movement, no net direction
    symmetric = ([Pair(f"a{i}", score_ref=2, score_cf=3) for i in range(3)]
                 + [Pair(f"b{i}", score_ref=3, score_cf=2) for i in range(3)])
    s1, s2 = signed_ordinal_disparity(systematic), signed_ordinal_disparity(symmetric)
    assert _approx(s1["mean_signed_difference"], 1.0)
    assert _approx(s2["mean_signed_difference"], 0.0)
    # MASD cannot tell these apart -- that is exactly why the signed estimand exists
    assert _approx(mean_absolute_score_difference(systematic),
                   mean_absolute_score_difference(symmetric))
    assert s1["transitions"][(2, 3)] == 6


def test_signed_ordinal_disparity_reports_wilcoxon_and_handles_ties():
    pairs = [Pair("v1", score_ref=2, score_cf=2),   # tie, excluded from the rank statistic
             Pair("v2", score_ref=2, score_cf=3),
             Pair("v3", score_ref=2, score_cf=3)]
    r = signed_ordinal_disparity(pairs)
    assert r["n"] == 3 and r["n_nonzero"] == 2
    assert r["wilcoxon_w"] == 0.0        # all non-zero differences share one direction


def test_interventional_propagation_holds_borderlineness_fixed():
    # same vignettes in both arms; only the FORCED upstream action differs
    flipped = [Pair(f"v{i}", action_ref=True, action_cf=False) for i in range(4)]
    held = [Pair(f"v{i}", action_ref=True, action_cf=True) for i in range(4)]
    r = interventional_propagation(flipped, held)
    assert _approx(r["downstream_cfr_upstream_forced_flipped"], 1.0)
    assert _approx(r["downstream_cfr_upstream_forced_reference"], 0.0)
    assert _approx(r["controlled_propagation_effect"], 1.0)
    assert r["balanced"] is True and r["paired_vignettes"] == 4


def test_interventional_propagation_flags_unbalanced_arms():
    r = interventional_propagation(
        [Pair("v1", action_ref=True, action_cf=False)],
        [Pair("v2", action_ref=True, action_cf=True)],
    )
    assert r["balanced"] is False, "unpaired arms reintroduce the confound the design removes"
    assert r["paired_vignettes"] == 0


def test_benjamini_yekutieli_is_more_conservative_than_bh():
    ps = [0.001, 0.01, 0.03, 0.2, 0.5]
    bh, by = benjamini_hochberg(ps), benjamini_yekutieli(ps)
    assert _approx(by["c_m"], sum(1.0 / i for i in range(1, 6)))
    assert all(q_by >= q_bh for q_by, q_bh in zip(by["qvalues"], bh["qvalues"]))
    assert sum(by["rejected"]) <= sum(bh["rejected"])


def test_capability_floor_blocks_the_degenerate_constant_policy():
    # A constant policy scores a perfect 0.0 WCFR while being clinically useless.
    gate = capability_floor_gate(wcfr=0.0, capability_score=0.10, min_capability=0.60,
                                 action_entropy=0.0, min_entropy=0.2, min_band_straddling=0)
    assert gate["eligible"] is False and gate["reason"] == "below_capability_floor"


def test_capability_floor_refuses_an_unset_entropy_threshold():
    """A constant policy has entropy exactly 0.0, so a default of 0.0 with a strict `<`
    made the check a no-op that every explicit-threshold test silently stepped over."""
    g = capability_floor_gate(wcfr=0.0, capability_score=0.9, min_capability=0.6,
                              action_entropy=0.0)
    assert g["eligible"] is False and g["reason"] == "min_entropy_not_set"
    # and with the threshold set, entropy exactly at the floor is still refused
    g2 = capability_floor_gate(wcfr=0.0, capability_score=0.9, min_capability=0.6,
                               action_entropy=0.0, min_entropy=0.0, min_band_straddling=0)
    assert g2["eligible"] is False and g2["reason"] == "degenerate_constant_policy"


def test_capability_floor_closes_the_denominator_shrinking_route():
    """A capable, high-entropy model can still game WCFR by steering cases out of band."""
    thin = {"wcfr": 0.0, "n_in_band": 1, "n_band_straddling": 1}
    g = capability_floor_gate(wcfr=thin, capability_score=0.95, min_capability=0.7,
                              action_entropy=1.5, min_entropy=0.5, min_band_straddling=20)
    assert g["eligible"] is False and g["reason"] == "below_band_straddling_floor"
    # a bare float cannot express the denominator, so the gate refuses instead of passing
    g2 = capability_floor_gate(wcfr=0.0, capability_score=0.95, min_capability=0.7,
                               action_entropy=1.5, min_entropy=0.5, min_band_straddling=20)
    assert g2["eligible"] is False and g2["reason"] == "straddling_count_unavailable"
    fat = {"wcfr": 0.08, "n_in_band": 90, "n_band_straddling": 40}
    g3 = capability_floor_gate(wcfr=fat, capability_score=0.95, min_capability=0.7,
                               action_entropy=1.5, min_entropy=0.5, min_band_straddling=20)
    assert g3["eligible"] is True
    # Entropy catches it even when a capability score is optimistic.
    gate2 = capability_floor_gate(wcfr=0.0, capability_score=0.9, min_capability=0.6,
                                  action_entropy=0.0, min_entropy=0.2, min_band_straddling=0)
    assert gate2["eligible"] is False and gate2["reason"] == "degenerate_constant_policy"
    # A capable agent with a real WCFR passes.
    gate3 = capability_floor_gate(wcfr=0.08, capability_score=0.82, min_capability=0.6,
                                  action_entropy=1.1, min_entropy=0.2, min_band_straddling=0)
    assert gate3["eligible"] is True


def test_capability_floor_reports_undefined_wcfr_rather_than_passing_it():
    gate = capability_floor_gate(wcfr=None, capability_score=0.9, min_capability=0.6,
                                 action_entropy=1.1, min_entropy=0.2, min_band_straddling=0)
    assert gate["eligible"] is False and gate["reason"] == "wcfr_undefined_empty_band"


def test_mcnemar_is_undefined_with_no_discordant_pairs():
    """The paper says undefined; returning 1.0 invites reading it as a null result."""
    r = mcnemar_exact([Pair("v1", action_ref=True, action_cf=True)])
    assert r["n_discordant"] == 0
    assert r["p_value"] is None
    assert "undefined" in r["reason"]


def test_permutation_distinguishes_a_symmetric_statistic_from_tied_data():
    """A flat null has two causes and they need different answers."""
    def mean_signed(ps):
        v = [p for p in ps if p.score_ref is not None and p.score_cf is not None]
        return sum(p.score_cf - p.score_ref for p in v) / len(v) if v else None
    tied = [Pair(f"v{i}", score_ref=3, score_cf=3) for i in range(6)]
    r = paired_permutation_test(tied, mean_signed)
    assert r["degenerate"] is False, "the statistic is signed; the DATA are tied"
    assert _approx(r["p_value"], 1.0)
    assert "no within-pair variation" in r["reason"]



def test_accumulation_uses_a_permutation_null_with_correct_scale():
    """The old analytic scale documented two wrong reference points.

    Independent shifts give a ratio near 0.84, not 1.0, and perfect reinforcement approaches
    the square root of the step count, not the step count. A reader calibrated to the old
    docstring would have read a maximal result as modest, so the reference is now the
    within-vignette sign-permutation null.
    """
    same = {f"step{s}": {f"v{i}": 1.0 for i in range(40)} for s in range(4)}
    r = trajectory_accumulation(same, n_perm=400, seed=1)
    assert r["p_value"] < 0.01, "all-same-sign must be extreme against the permutation null"
    assert _approx(r["concordance"], 1.0)

    alternating = {f"step{s}": {f"v{i}": (1.0 if s % 2 == 0 else -1.0) for i in range(40)}
                   for s in range(4)}
    a = trajectory_accumulation(alternating, n_perm=400, seed=1)
    assert _approx(a["mean_abs_composite"], 0.0), "opposed shifts cancel"
    assert a["p_value"] > 0.5, "cancellation must not read as extreme"


def test_accumulation_never_claims_to_be_identified():
    """It cannot separate carry-forward from a shared vignette-level cause, and says so."""
    same = {f"step{s}": {f"v{i}": 1.0 for i in range(20)} for s in range(3)}
    assert trajectory_accumulation(same, n_perm=200)["identified"] is False


def test_accumulation_concordance_ignores_single_shift_trajectories():
    """One non-zero shift is trivially same-signed and would inflate the statistic."""
    one = {f"step{s}": {f"v{i}": (1.0 if s == 0 else 0.0) for i in range(20)}
           for s in range(4)}
    r = trajectory_accumulation(one, n_perm=200)
    assert r["n_concordance_eligible"] == 0
    assert r["concordance"] is None


def test_accumulation_returns_na_on_empty_input():
    r = trajectory_accumulation({})
    assert r["mean_abs_composite"] is None and r["n_vignettes"] == 0


def test_straddling_floor_does_not_penalise_a_fair_agent():
    """The floor once inverted: straddling was inferred from flips, so a fair agent scored
    zero straddling and was refused while a biased agent cleared the floor on its own flips.
    Straddling is a property of the band and the threshold, never of the outcome."""
    def mk(i, flip):
        return Pair(f"v{i}", action_ref=True, action_cf=(not flip),
                    in_band_ref=True, in_band_cf=True, straddles_threshold=True)
    fair = [mk(i, False) for i in range(30)]
    biased = [mk(i, True) for i in range(10)] + [mk(i + 10, False) for i in range(20)]
    wf, wb = within_range_flip_rate(fair, bands=[]), within_range_flip_rate(biased, bands=[])
    assert wf["n_band_straddling"] == 30 and wb["n_band_straddling"] == 30
    assert _approx(wf["wcfr"], 0.0) and wb["wcfr"] > 0
    gate = lambda w: capability_floor_gate(w, 0.9, 0.7, action_entropy=1.5,
                                           min_entropy=0.5, min_band_straddling=5)
    assert gate(wf)["eligible"] is True, "a fair agent must not be refused for being fair"
    assert gate(wb)["eligible"] is True


def test_unpopulated_straddling_fails_loud_rather_than_reading_as_zero():
    pairs = [Pair(f"v{i}", action_ref=True, action_cf=True,
                  in_band_ref=True, in_band_cf=True) for i in range(10)]
    w = within_range_flip_rate(pairs, bands=[])
    assert w["n_band_straddling"] is None
    g = capability_floor_gate(w, 0.9, 0.7, action_entropy=1.5, min_entropy=0.5,
                              min_band_straddling=5)
    assert g["eligible"] is False and g["reason"] == "straddling_count_unavailable"


def test_straddle_contradiction_is_surfaced():
    """A flip proves the band straddled, so a flipped pair flagged non-straddling is a
    contradiction in the inputs and must not be silently absorbed."""
    pairs = [Pair("v1", action_ref=True, action_cf=False, in_band_ref=True,
                  in_band_cf=True, straddles_threshold=False)]
    assert within_range_flip_rate(pairs, bands=[])["n_straddle_contradictions"] == 1


def test_band_straddles_reads_the_band_not_the_outcome():
    assert band_straddles({2, 3}, lambda a: a <= 2) is True
    assert band_straddles({1, 2}, lambda a: a <= 2) is False   # cannot produce a flip
    assert band_straddles({"min": 1, "max": 30}, lambda d: d <= 14) is True
    assert band_straddles(None, lambda a: a <= 2) is None


def test_in_band_rejects_a_dichotomized_action():
    """True == 1 in Python, so phi would silently test as in-band against an ordinal band."""
    try:
        in_band(True, {1, 2})
    except TypeError as e:
        assert "bool" in str(e)
    else:
        raise AssertionError("a bool action must be rejected, not read as the integer 1")


# --- restricted wild cluster bootstrap -------------------------------------------------------

def test_webb_weights_are_the_six_point_distribution():
    ws = sorted(WEBB_WEIGHTS)
    assert len(ws) == 6
    # Symmetric about zero, mean zero, unit variance: the three properties the weights need.
    assert all(abs(ws[i] + ws[5 - i]) < 1e-12 for i in range(3))
    assert abs(sum(ws)) < 1e-12
    assert abs(sum(w * w for w in ws) / 6 - 1.0) < 1e-12


def test_cluster_robust_se_uses_clusters_not_observations():
    """Duplicating every observation within its cluster must not shrink the standard error.

    A flat (non-clustered) standard error falls by sqrt(2) when each observation is doubled,
    which is exactly the false precision clustering exists to prevent.
    """
    base = {"v%d" % i: [float(i % 2)] for i in range(8)}
    doubled = {k: v * 2 for k, v in base.items()}
    _, se_base, _, _ = _cluster_robust_mean(base)
    _, se_doubled, _, _ = _cluster_robust_mean(doubled)
    assert abs(se_base - se_doubled) < 1e-12


def test_wcb_refuses_when_the_cluster_robust_variance_is_zero():
    """Constant data has no variance to studentize by, and a p-value there would be invented."""
    r = wild_cluster_bootstrap_p({"v%d" % i: [1.0, 1.0] for i in range(6)}, signed=True)
    assert r["p"] is None and r["refused"] == "zero_cluster_robust_variance"


def test_wcb_refuses_below_three_clusters():
    r = wild_cluster_bootstrap_p({"a": [1.0, 0.0], "b": [0.0, 1.0]}, signed=True)
    assert r["p"] is None and r["refused"] == "too_few_clusters"


def test_wcb_rejects_a_real_effect_and_accepts_the_truth():
    rng = random.Random(0)
    d = {"v%d" % i: [1.0 if rng.random() < 0.8 else 0.0 for _ in range(3)] for i in range(10)}
    at_zero = wild_cluster_bootstrap_p(d, b0=0.0, n_boot=999, signed=True)
    at_truth = wild_cluster_bootstrap_p(d, b0=at_zero["beta"], n_boot=999, signed=True)
    assert at_zero["p"] < 0.05
    assert at_truth["p"] > 0.5
    assert at_zero["weights"] == "webb6"


def test_wcb_ci_brackets_its_own_point_estimate():
    rng = random.Random(1)
    d = {"v%d" % i: [1.0 if rng.random() < 0.7 else 0.0 for _ in range(3)] for i in range(10)}
    ci = wild_cluster_bootstrap_ci(d, n_boot=299, grid=41, signed=True)
    assert ci["lo"] <= ci["beta"] <= ci["hi"]
    assert not ci["truncated_low"] and not ci["truncated_high"]


def test_wcb_ci_flags_truncation_rather_than_reporting_a_narrow_interval():
    """A span too small to contain the interval must be flagged, not silently truncated."""
    rng = random.Random(2)
    d = {"v%d" % i: [rng.gauss(0.0, 1.0) for _ in range(3)] for i in range(8)}
    ci = wild_cluster_bootstrap_ci(d, n_boot=199, grid=21, span=0.25, signed=True)
    assert ci["truncated_low"] and ci["truncated_high"]


def test_webb_beats_rademacher_granularity_at_the_cluster_counts_this_design_reaches():
    """The reason Webb weights are pre-registered, checked rather than asserted.

    With ``G`` clusters a two-point weight admits ``2**G`` bootstrap vectors, so the smallest
    attainable p-value is bounded well above 0.05 at the cluster counts a vignette-clustered
    design reaches. A test that cannot reject at its own level is not a conservative test, it
    is an inert one.
    """
    def smallest_attainable_p(weights, g):
        rng = random.Random(0)
        data = {"v%d" % i: [rng.gauss(1.0, 0.4) for _ in range(3)] for i in range(g)}
        beta, se, _, _ = _cluster_robust_mean(data)
        t_obs = abs(beta / se)
        n_extreme = n_valid = 0
        for combo in itertools.product(weights, repeat=g):
            star = {k: [w * u for u in data[k]] for k, w in zip(data, combo)}
            b, s, _, _ = _cluster_robust_mean(star)
            if not s:
                continue
            n_valid += 1
            if abs(b / s) >= t_obs:
                n_extreme += 1
        return (n_extreme + 1) / (n_valid + 1)

    for g in (4, 5):
        p_rademacher = smallest_attainable_p((-1.0, 1.0), g)
        p_webb = smallest_attainable_p(WEBB_WEIGHTS, g)
        assert p_rademacher > 0.05, "Rademacher unexpectedly reached significance at G=%d" % g
        assert p_webb < 0.05, "Webb failed to reach significance at G=%d" % g


def test_signed_flip_value_records_direction_not_just_difference():
    up = Pair(vignette_id="v1", action_ref=False, action_cf=True)
    down = Pair(vignette_id="v1", action_ref=True, action_cf=False)
    assert signed_flip_value(up) == 1.0
    assert signed_flip_value(down) == -1.0
    assert signed_flip_value(Pair(vignette_id="v1", action_ref=None, action_cf=True)) is None
    # The two directions cancel, which is the whole point of a signed estimand: CFR would
    # score both as flips and report 1.0.
    grouped = paired_values_by_cluster([up, down], signed_flip_value)
    beta, _, _, _ = _cluster_robust_mean(grouped)
    assert beta == 0.0
    assert counterfactual_flip_rate([up, down]) == 1.0


def test_wcb_refuses_an_undeclared_statistic_because_the_null_sits_on_the_boundary():
    """CFR, WCFR and MASD are non-negative, so H0 = 0 is a boundary point.

    A negative Webb weight then maps residuals to values the statistic cannot take, and the
    resulting reference distribution describes a null the estimand could not have produced.
    The same defect is refused by name in paired_permutation_test; refusing it here keeps the
    two entry points consistent rather than leaving one of them exploitable.
    """
    # CFR-like: non-negative by construction, and varying across clusters so that the
    # cluster-robust variance is non-zero and the boundary guard is the only thing refusing.
    flips = {"v%d" % i: [1.0, 1.0] if i % 3 else [0.0, 1.0] for i in range(6)}
    r = wild_cluster_bootstrap_p(flips, b0=0.0)
    assert r["p"] is None and r["refused"] == "unsigned_statistic_not_declared_signed"
    ci = wild_cluster_bootstrap_ci(flips)
    assert ci["lo"] is None and ci["refused"] == "unsigned_statistic_not_declared_signed"
    # Declaring it signed is a claim about the statistic, not about the sample, so the same
    # values go through once the caller takes responsibility for that claim.
    assert wild_cluster_bootstrap_p(flips, b0=0.0, n_boot=199, signed=True)["p"] is not None


def test_wcfr_refuses_omitted_bands_and_fails_safe_on_empty_ones():
    """The provenance flag must never default to true.

    ``bands`` defaulted to an empty sequence and ``ground_truth`` was computed as
    ``not (bands and provisional)``, so a caller who simply omitted the argument was told the
    rate was clinical ground truth. That is the one field standing between a provisional
    number and a fairness claim, and it failed open. Omitting the argument is now refused,
    and supplying an empty sequence yields false rather than true.
    """
    pairs = [Pair("v1", action_ref=True, action_cf=False, in_band_ref=True, in_band_cf=True,
                  straddles_threshold=True)]
    try:
        within_range_flip_rate(pairs)
    except TypeError as e:
        assert "explicit bands" in str(e)
    else:
        raise AssertionError("omitting bands must be refused, not silently permitted")

    # No bands is not the same as adjudicated bands.
    assert within_range_flip_rate(pairs, bands=[])["ground_truth"] is False

    # An unadjudicated band yields a NUMBER plus a false flag, not NA. A reporting path that
    # waited for None to protect it would print a provisional rate as a result.
    from fairmedagent.bands import Band
    provisional = [Band(sub_action="esi_acuity", acceptable={2}, provenance="author-derived")]
    r = within_range_flip_rate(pairs, bands=provisional)
    assert r["ground_truth"] is False
    assert r["wcfr"] is not None
    assert r["n_provisional_bands"] == 1
    assert "not a fairness result" in r["provenance_note"]


if __name__ == "__main__":
    _run_all()
