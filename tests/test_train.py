import pytest

from titer.train.rollout import (Trajectory, in_band, rejection_sample,
                                 solve_rates, write_jsonl)
from titer.train.seeds import verdict


def _t(task, outcome, spend=0.1, turns=2):
    return Trajectory(task_id=task, outcome=outcome, reward=1.0, spend_usd=spend,
                      turns=turns)


# --- rejection sampling ---

def test_only_oracle_passing_trajectories_survive():
    trs = [_t("a", "CORRECT"), _t("a", "STALE"), _t("b", "FALSE_MERGE"),
           _t("b", "MISS"), _t("c", "ABSTAIN")]
    kept = rejection_sample(trs)
    assert [t.task_id for t in kept] == ["a"]


def test_per_task_cap_stops_easy_tasks_dominating():
    trs = [_t("easy", "CORRECT") for _ in range(20)] + [_t("hard", "CORRECT")]
    kept = rejection_sample(trs, max_per_task=2)
    ids = [t.task_id for t in kept]
    assert ids.count("easy") == 2 and ids.count("hard") == 1


def test_cheapest_success_is_preferred():
    trs = [_t("a", "CORRECT", spend=0.50), _t("b", "CORRECT", spend=0.01)]
    kept = rejection_sample(trs)
    assert kept[0].spend_usd == 0.01


def test_no_passing_trajectories_yields_an_empty_set_not_a_crash():
    assert rejection_sample([_t("a", "MISS")]) == []


# --- solve band ---

def test_solve_rates_and_band_selection():
    trs = ([_t("always", "CORRECT") for _ in range(10)]
           + [_t("never", "MISS") for _ in range(10)]
           + [_t("mixed", "CORRECT") for _ in range(4)]
           + [_t("mixed", "MISS") for _ in range(6)])
    rates = solve_rates(trs)
    assert rates == {"always": 1.0, "never": 0.0, "mixed": 0.4}
    assert in_band(rates) == ["mixed"]


def test_saturated_and_impossible_tasks_leave_the_rl_mix():
    """They contribute noise, not learning. They stay in evaluation."""
    rates = {"a": 0.0, "b": 0.05, "c": 0.5, "d": 0.95, "e": 1.0}
    assert in_band(rates) == ["c"]


def test_write_jsonl_round_trips(tmp_path):
    n = write_jsonl([_t("a", "CORRECT")], tmp_path / "d" / "sft.jsonl")
    assert n == 1 and (tmp_path / "d" / "sft.jsonl").exists()


# --- the seed rule ---

def test_reconforge_scenario_is_refused():
    """The real numbers: R_w 0.746 / 0.820 / 0.835 / 0.945, mean 0.8365,
    across-seed SD 0.0821. The shipped model was 0.945 - the top of the range -
    and beat the frontier baseline by 0.0288, putting that baseline at 0.9162.

    The mean is BELOW the baseline. So the gate refuses for the stronger reason:
    the recipe never beat the baseline at all, and the published headline was a
    property of one lucky seed rather than of the method."""
    seeds = [0.746, 0.820, 0.835, 0.945]
    v = verdict("lora-1.7b", seeds, baseline=0.9162)
    assert not v.claimable
    assert "does not beat" in v.reason
    assert abs(v.sd - 0.0821) < 1e-3
    assert max(seeds) > v.baseline > v.mean   # only the shipped seed cleared it


def test_a_margin_smaller_than_the_seed_spread_is_refused_as_noise():
    """The other reconforge failure mode: the mean does clear the baseline, but
    by less than the seeds vary among themselves."""
    v = verdict("arm", [0.746, 0.820, 0.835, 0.945], baseline=0.80)
    assert v.margin > 0
    assert not v.claimable and "seed noise" in v.reason
    assert v.ratio > 1.0


def test_a_real_margin_is_claimable():
    v = verdict("policy", [0.90, 0.91, 0.905, 0.895], baseline=0.60)
    assert v.claimable and v.ratio < 1.0


def test_three_seeds_is_never_enough():
    v = verdict("policy", [0.90, 0.91, 0.905], baseline=0.60)
    assert not v.claimable and "minimum" in v.reason


def test_losing_to_the_baseline_is_not_a_claim():
    v = verdict("policy", [0.50, 0.51, 0.49, 0.50], baseline=0.60)
    assert not v.claimable and "does not beat" in v.reason


def test_verdict_string_always_shows_the_spread():
    """A margin cannot be written down without its spread."""
    v = verdict("p", [0.9, 0.91, 0.905, 0.895], 0.6)
    s = str(v)
    assert "across-seed SD" in s and "seeds" in s and "margin" in s


class TestLinearPolicy:
    """The trained arm's policy. Stdlib only, 130 parameters."""

    def test_action_set_covers_query_abstain_and_every_confidence_bucket(self):
        from titer.train.policy import ACTIONS, CONF_BUCKETS
        assert ("query", None) in ACTIONS and ("abstain", None) in ACTIONS
        for c in CONF_BUCKETS:
            assert ("answer", c) in ACTIONS
        assert len(ACTIONS) == 2 + len(CONF_BUCKETS)

    def test_collision_band_is_not_a_feature(self):
        """The simulator conditions on collision band; the observation does not
        expose it, and a policy trained on it would learn from something a live
        provider never hands over."""
        from titer.train.policy import FEATURES
        assert not any("band" in f or "collision" in f for f in FEATURES)

    def test_probabilities_are_a_distribution(self):
        from titer.train.policy import LinearPolicy, N_FEATURES
        p = LinearPolicy()
        probs = p.probs([1.0] * N_FEATURES)
        assert abs(sum(probs) - 1.0) < 1e-9
        assert all(x >= 0 for x in probs)

    def test_a_gradient_step_moves_probability_the_signed_way(self):
        from titer.train.policy import LinearPolicy, N_FEATURES
        p = LinearPolicy()
        x = [1.0] * N_FEATURES
        before = p.probs(x)[3]
        p.grad_step(x, 3, advantage=1.0, lr=0.1)
        assert p.probs(x)[3] > before
        p.grad_step(x, 3, advantage=-1.0, lr=0.5)
        assert p.probs(x)[3] < before

    def test_zero_advantage_is_a_no_op(self):
        """GRPO groups whose rollouts all score alike carry no signal, and
        applying them anyway is how a run drifts on noise."""
        from titer.train.policy import LinearPolicy, N_FEATURES
        p = LinearPolicy()
        x = [0.5] * N_FEATURES
        w = p.snapshot()
        p.grad_step(x, 2, advantage=0.0, lr=0.5)
        assert p.snapshot() == w


class TestRealEnvBuilder:
    """`sim/real.py` is shared by env_health --real and train_policy, so the
    training run is fitted exactly like the health report that blessed it."""

    def test_fits_from_the_cache_with_no_network(self):
        from pathlib import Path
        from titer.sim.real import build, NoObservations
        root = Path(__file__).resolve().parent.parent
        if not (root / "data" / "replay.jsonl").exists():
            return
        try:
            parts = build(root)
        except NoObservations:
            return
        assert len(parts.observations) == len(parts.tasks)
        assert parts.model.fallback is not None
        assert 0.0 <= parts.model.fallback.p_correct <= 1.0
