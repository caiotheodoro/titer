from datetime import date, timedelta

import pytest

from titer.corpus.build import build_quarter
from titer.corpus.schema import ExclusionCounts
from titer.corpus.title_map import TitleClass
from titer.costs.profiles import FLAT, PRIMARY, REPORTABLE, accuracy, expected_loss
from titer.oracle.outcome import Answer, Outcome, atoms, judge


@pytest.fixture
def truth(quarter_zip):
    rows = build_quarter(quarter_zip, ExclusionCounts())
    return next(r for r in rows if r.person_cik == "1000001")  # CEO, Apple, 2025-02-13


def test_correct(truth):
    a = Answer(person_cik="1000001", confidence=0.9, employer_cik="320193")
    assert judge(a, truth) is Outcome.CORRECT


def test_false_merge_requires_confidence(truth):
    """Same wrong answer, different confidence, different class. That split is
    the whole point of separating FALSE_MERGE from UNSURE_WRONG."""
    wrong_confident = Answer(person_cik="1000002", confidence=0.9)
    wrong_hedged = Answer(person_cik="1000002", confidence=0.1)
    assert judge(wrong_confident, truth) is Outcome.FALSE_MERGE
    assert judge(wrong_hedged, truth) is Outcome.UNSURE_WRONG


def test_miss_and_abstain_are_distinct(truth):
    assert judge(Answer(), truth) is Outcome.MISS
    assert judge(Answer(abstained=True), truth) is Outcome.ABSTAIN
    # abstaining beats being confidently wrong under every reportable profile
    for name, prof in REPORTABLE.items():
        assert prof[Outcome.ABSTAIN] < prof[Outcome.FALSE_MERGE], name


def test_stale_is_right_human_wrong_employer(truth):
    a = Answer(person_cik="1000001", confidence=0.9, employer_cik="789019")
    assert judge(a, truth) is Outcome.STALE


def test_atoms_identity_and_title(truth):
    a = Answer(person_cik="1000001", title_class=TitleClass.CEO,
               employment_start=date(2020, 1, 1))
    got = atoms(a, truth)
    assert got.identity and got.title and got.window
    assert got.total == 1.0


def test_unknown_title_atom_is_excluded_not_failed(quarter_zip):
    """CONTRACTS 3.2. A blank filed title is our coverage gap, not the
    answerer's fault, so that atom is dropped from the denominator."""
    rows = build_quarter(quarter_zip, ExclusionCounts())
    t = next(r for r in rows if r.title_class is TitleClass.UNKNOWN)
    a = Answer(person_cik=t.person_cik, title_class=None,
               employment_start=t.period - timedelta(days=1))
    got = atoms(a, t)
    assert got.title_scored is False
    assert got.total == 1.0  # identity + window, title neither helps nor hurts


def test_withholding_dates_fails_the_window_atom_rather_than_removing_it(truth):
    """The TASK decides which atoms are scored, never the answer. Letting the
    provider drop an atom by staying silent made omission strictly profitable."""
    silent = atoms(Answer(person_cik="1000001", title_class=TitleClass.CEO), truth)
    full = atoms(Answer(person_cik="1000001", title_class=TitleClass.CEO,
                        employment_start=date(2020, 1, 1)), truth)
    assert silent.window is False and silent.total < full.total
    assert full.total == 1.0


def test_identity_atom_is_dropped_when_only_the_prompt_pinned_it(truth):
    """A provider that echoes the employer we handed it has not identified
    anyone. See docs/DECISIONS.md D024."""
    a = Answer(person_cik="1000001", title_class=TitleClass.CEO,
               employment_start=date(2020, 1, 1))
    parrot = atoms(a, truth, identity_scored=False)
    earned = atoms(a, truth, identity_scored=True)
    assert parrot.total <= earned.total


def test_window_atom_rejects_period_outside_employment(truth):
    a = Answer(person_cik="1000001", title_class=TitleClass.CEO,
               employment_start=date(2025, 6, 1))     # started after the filing
    assert atoms(a, truth).window is False


def test_flat_profile_ranking_equals_accuracy_ranking():
    """The integrity probe. If this fails, the harness has a bug - it is not a
    finding about anyone. CONTRACTS.md section 5.1."""
    arms = {
        "a": [Outcome.CORRECT] * 8 + [Outcome.FALSE_MERGE] * 2,
        "b": [Outcome.CORRECT] * 6 + [Outcome.MISS] * 4,
        "c": [Outcome.CORRECT] * 9 + [Outcome.ABSTAIN],
        "d": [Outcome.MISS] * 10,
    }
    by_acc = sorted(arms, key=lambda k: -accuracy(arms[k]))
    by_flat = sorted(arms, key=lambda k: expected_loss(arms[k], FLAT))
    assert by_acc == by_flat


def test_flat_is_not_reportable():
    assert FLAT not in REPORTABLE.values()
    assert "flat" not in REPORTABLE


def test_cost_asymmetry_reorders_arms():
    """The reason the project exists: an arm can win on accuracy and lose badly
    once a confident wrong answer is priced."""
    accurate_but_reckless = [Outcome.CORRECT] * 9 + [Outcome.FALSE_MERGE]
    cautious = [Outcome.CORRECT] * 7 + [Outcome.ABSTAIN] * 3
    assert accuracy(accurate_but_reckless) > accuracy(cautious)
    assert expected_loss(accurate_but_reckless, REPORTABLE["kyc_sanctions"]) > \
           expected_loss(cautious, REPORTABLE["kyc_sanctions"])


def test_primary_profile_is_declared():
    assert PRIMARY in REPORTABLE
