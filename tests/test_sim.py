import pytest

from titer.oracle.outcome import Outcome
from titer.sim.fit import Cell, Observation, fit


def _obs(band, outcome, n, provider="ploid", action="search", conf=0.8, spend=0.10):
    return [Observation(provider, action, band, outcome, conf, spend) for _ in range(n)]


def test_refuses_to_fit_on_the_evaluation_split():
    """A simulator fitted on eval data makes the sim-to-real gap unmeasurable -
    the one number this module exists to expose."""
    with pytest.raises(ValueError) as e:
        fit(_obs("unique", Outcome.CORRECT, 10), split="test")
    assert "unmeasurable" in str(e.value)


def test_accuracy_falling_with_collision_degree_survives_the_fit():
    """Averaging this structure away would train the policy on a world where
    disambiguation is never worth paying for."""
    obs = (_obs("unique", Outcome.CORRECT, 90) + _obs("unique", Outcome.MISS, 10)
           + _obs("high", Outcome.CORRECT, 20) + _obs("high", Outcome.FALSE_MERGE, 80))
    m = fit(obs)
    assert m.cell_for("ploid", "search", "unique").p_correct == 0.9
    assert m.cell_for("ploid", "search", "high").p_correct == 0.2
    assert m.cell_for("ploid", "search", "high").p_wrong_person == 0.8


def test_thin_cells_fall_back_and_the_pooling_is_visible():
    obs = _obs("unique", Outcome.CORRECT, 50) + _obs("high", Outcome.MISS, 2)
    m = fit(obs, min_cell_n=5)
    assert ("ploid", "search", "high") not in m.cells
    assert m.cell_for("ploid", "search", "high") is m.fallback
    assert "ploid/search/unique" in m.coverage()
    assert "ploid/search/high" not in m.coverage()


def test_cell_probabilities_must_sum_to_one():
    with pytest.raises(ValueError):
        Cell(n=10, p_correct=0.5, p_stale=0.2, p_wrong_person=0.2, p_miss=0.2,
             mean_confidence=0.5, mean_spend_usd=0.1).check()


def test_missing_cell_without_fallback_raises_rather_than_inventing():
    m = fit([])
    with pytest.raises(KeyError):
        m.cell_for("ploid", "search", "unique")


def test_abstain_is_pooled_with_miss_not_with_correct():
    m = fit(_obs("unique", Outcome.ABSTAIN, 10))
    c = m.cell_for("ploid", "search", "unique")
    assert c.p_miss == 1.0 and c.p_correct == 0.0
