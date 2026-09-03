"""Scoring an expertise verdict. The FALSE_MERGE branch is the headline result,
so it gets the adversarial cases."""
import pytest

from titer.costs.profiles import REPORTABLE, expected_loss
from titer.oracle.outcome import (ATTESTED, CONSTRUCTED_FALSE, ExpertiseAnswer,
                                  Outcome, judge_expertise)


def A(**kw):
    return ExpertiseAnswer(**kw)


# --- the four cells of the confusion matrix ---

def test_affirming_an_attested_claim_is_correct():
    assert judge_expertise(A(affirms=True, confidence=0.9), ATTESTED) is Outcome.CORRECT


def test_denying_an_attested_claim_is_a_miss():
    """A real expert not verified. Costs roughly one sourcing bounty."""
    assert judge_expertise(A(affirms=False, confidence=0.9), ATTESTED) is Outcome.MISS


def test_denying_a_false_claim_is_correct_not_a_non_event():
    """Rejecting a fabricated claim IS the job. Scoring it as anything else
    would make abstaining look identical to competence."""
    assert judge_expertise(A(affirms=False, confidence=0.9),
                           CONSTRUCTED_FALSE) is Outcome.CORRECT


def test_confidently_affirming_a_false_claim_is_a_fake_expert_admitted():
    """The headline error. E1's whole reason for existing."""
    assert judge_expertise(A(affirms=True, confidence=0.9),
                           CONSTRUCTED_FALSE) is Outcome.FALSE_MERGE


def test_hedged_affirmation_of_a_false_claim_is_separated_out():
    assert judge_expertise(A(affirms=True, confidence=0.1),
                           CONSTRUCTED_FALSE) is Outcome.UNSURE_WRONG


# --- silence is not a denial ---

def test_no_verdict_is_a_miss_not_a_correct_denial():
    """A provider that cannot answer is failing to verify, not correctly
    rejecting. Collapsing the two would credit silence as caution and hand a
    perfect false-merge rate to an arm that never answers anything."""
    assert judge_expertise(A(affirms=None), CONSTRUCTED_FALSE) is Outcome.MISS
    assert judge_expertise(A(affirms=None), ATTESTED) is Outcome.MISS


def test_abstention_is_distinct_from_both():
    assert judge_expertise(A(abstained=True), ATTESTED) is Outcome.ABSTAIN
    assert judge_expertise(A(abstained=True), CONSTRUCTED_FALSE) is Outcome.ABSTAIN


def test_unknown_polarity_raises_rather_than_guessing():
    with pytest.raises(ValueError):
        judge_expertise(A(affirms=True), "MAYBE")


# --- the cost model does what the addendum says ---

def test_fake_expert_dominates_expected_loss_under_expert_sourcing():
    """CONTRACTS A5: 150x. An arm that is accurate but occasionally admits a
    fake must lose to a cautious one, or the profile is not doing its job."""
    reckless = [Outcome.CORRECT] * 99 + [Outcome.FALSE_MERGE]
    cautious = [Outcome.CORRECT] * 80 + [Outcome.MISS] * 20
    p = REPORTABLE["expert_sourcing"]
    assert expected_loss(reckless, p) > expected_loss(cautious, p)


def test_expert_sourcing_is_the_harshest_profile_on_false_merges():
    fm = Outcome.FALSE_MERGE
    ratios = {k: v[fm] / v[Outcome.MISS] for k, v in REPORTABLE.items()}
    assert max(ratios, key=ratios.get) == "expert_sourcing"


def test_an_always_deny_arm_scores_perfectly_on_false_merges_and_must_still_lose():
    """The degenerate strategy this task invites: deny everything, never admit a
    fake. It must lose on expected loss, or the benchmark rewards uselessness."""
    always_deny = ([judge_expertise(A(affirms=False, confidence=0.9), ATTESTED)] * 50
                   + [judge_expertise(A(affirms=False, confidence=0.9),
                                      CONSTRUCTED_FALSE)] * 50)
    assert Outcome.FALSE_MERGE not in always_deny
    honest = [Outcome.CORRECT] * 90 + [Outcome.MISS] * 10
    for name, p in REPORTABLE.items():
        assert expected_loss(honest, p) < expected_loss(always_deny, p), name
