from datetime import date, timedelta

import pytest

from titer.adapters.base import Call, RawAnswer, Spend
from titer.corpus.collision import build_index
from titer.corpus.schema import AttestedTuple, RoleClass
from titer.corpus.tasks import build_tasks
from titer.corpus.title_map import TitleClass
from titer.costs.profiles import REPORTABLE
from titer.env.keel import Keel
from titer.env.policies import (abstain_always, always_deep_verify, never_verify,
                                run_episode)
from titer.env.titer_env import TiterEnv
from titer.oracle.outcome import Outcome
from titer.oracle.resolve import build_issuer_index


def _row(cik, name, issuer, iname, period, title=TitleClass.CEO):
    return AttestedTuple(
        accession=f"a-{cik}-{issuer}-{period}", person_cik=cik, person_name_raw=name,
        issuer_cik=issuer, issuer_name_raw=iname, issuer_ticker="T",
        role_class=frozenset({RoleClass.OFFICER}), title_raw=title.value,
        title_class=title, period=period, filed=period + timedelta(days=2))


@pytest.fixture
def world():
    rows = [
        _row("1", "SMITH JOHN", "A", "ALPHA CORP", date(2020, 1, 1)),
        _row("1", "SMITH JOHN", "B", "BETA CORP", date(2022, 6, 1)),
        _row("2", "SMITH JOHN", "C", "GAMMA CORP", date(2020, 3, 1)),
        _row("2", "SMITH JOHN", "D", "DELTA CORP", date(2023, 3, 1)),
    ]
    idx = build_index(rows)
    tasks, _ = build_tasks(rows, idx)
    return rows, idx, build_issuer_index(rows), tasks


class FakeProvider:
    """Returns whatever it is told to, at a stated price."""

    def __init__(self, name, answers, price, actions=("search",)):
        self.name = name
        self._answers = answers
        self._price = price
        self._actions = actions
        self.calls = 0

    def actions(self):
        return [Call(self.name, a, self._price) for a in self._actions]

    def query(self, action, prompt, **kw):
        self.calls += 1
        return list(self._answers), Spend(self._price, 1.0, "unit")


def _env(world, answers, price=0.10, budget=1.0, profile="gtm_outbound"):
    rows, idx, iidx, tasks = world
    tasks = [t for t in tasks if t.person_cik == "1"]
    return TiterEnv(tasks, {"p": FakeProvider("p", answers, price)},
                    idx, iidx, budget_usd=budget, profile_name=profile)


# --- verifier integrity -------------------------------------------------

def test_gold_answer_scores_the_maximum(world):
    """Right person, right employer. If this is not the top score, everything
    downstream is measuring the harness."""
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="BETA CORP",
                                 title_text="Chief Executive Officer",
                                 employment_start=date(2022, 1, 1),
                                 confidence=0.95, rank=0)])
    rec = run_episode(env, never_verify(("p", "search")))
    assert rec.outcome is Outcome.CORRECT
    assert rec.atoms.identity is True
    assert rec.atoms.title is True and rec.atoms.window is True
    assert rec.atoms.total == 1.0
    assert rec.reward == pytest.approx(1.0 - 0.30 * 0.10 / 1.0)


def test_noop_answer_is_a_miss_and_is_priced_by_the_profile(world):
    """MISS is no longer free. Every outcome is priced by the cost profile, so
    the trained objective is the reported loss rather than a proxy."""
    env = _env(world, [])
    rec = run_episode(env, never_verify(("p", "search")))
    assert rec.outcome is Outcome.MISS
    assert rec.reward < 0.0


def test_confidently_naming_the_other_john_smith_is_a_false_merge(world):
    """The measurement this project exists for: a same-name different-CIK
    answer, stated confidently."""
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="DELTA CORP",
                                 confidence=0.95, rank=0)])
    rec = run_episode(env, never_verify(("p", "search")))
    assert rec.outcome is Outcome.FALSE_MERGE
    assert rec.reward < 0


def test_returning_the_anchor_employer_is_stale_not_correct(world):
    """R1's signal: right human, employer the index has not updated."""
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="ALPHA CORP",
                                 confidence=0.9, rank=0)])
    rec = run_episode(env, never_verify(("p", "search")))
    assert rec.outcome is Outcome.STALE


# --- no shaping ---------------------------------------------------------

def test_querying_earns_nothing(world):
    """CONTRACTS 6 forbids shaping. Searching must be worth exactly zero until
    an answer is given, or the policy learns to search performatively."""
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="BETA CORP",
                                 confidence=0.9, rank=0)])
    env.reset(0)
    for _ in range(5):
        r = env.step({"type": "query", "provider": "p", "action": "search"})
        assert r.reward == 0.0 and not r.done


def test_efficiency_penalty_applies_only_among_successes(world):
    """Charging failures for spend rewards failing cheaply, which is
    abstain_always wearing a disguise."""
    correct = RawAnswer(person_name="John Smith", employer_name="BETA CORP",
                        title_text="Chief Executive Officer", confidence=0.9, rank=0)
    cheap = run_episode(_env(world, [correct], price=0.01), never_verify(("p", "search")))
    dear = run_episode(_env(world, [correct], price=0.50), never_verify(("p", "search")))
    assert dear.reward < cheap.reward          # spending costs a correct answer

    miss = RawAnswer(person_name=None, employer_name=None, confidence=0.0, rank=0)
    cheap_miss = run_episode(_env(world, [miss], price=0.01), never_verify(("p", "search")))
    dear_miss = run_episode(_env(world, [miss], price=0.50), never_verify(("p", "search")))
    assert cheap_miss.reward == dear_miss.reward   # spending is free when you fail


# --- the degenerate floor ----------------------------------------------

@pytest.mark.parametrize("profile", list(REPORTABLE))
def test_abstain_always_loses_to_a_correct_policy_under_every_profile(world, profile):
    """docs/RED-TEAM.md A8. If the abstention credit is too generous the reward
    is hackable and 'the policy learned to be careful' is an artefact."""
    correct = RawAnswer(person_name="John Smith", employer_name="BETA CORP",
                        title_text="Chief Executive Officer", confidence=0.9, rank=0)
    good = run_episode(_env(world, [correct], profile=profile),
                       never_verify(("p", "search")))
    lazy = run_episode(_env(world, [correct], profile=profile), abstain_always)
    assert lazy.outcome is Outcome.ABSTAIN
    assert lazy.reward < good.reward, f"abstain_always is competitive under {profile}"


def test_abstaining_still_beats_a_confident_false_merge(world):
    """The ordering that makes abstention worth having at all."""
    wrong = RawAnswer(person_name="John Smith", employer_name="DELTA CORP",
                      confidence=0.95, rank=0)
    lazy = run_episode(_env(world, [wrong]), abstain_always)
    reckless = run_episode(_env(world, [wrong]), never_verify(("p", "search")))
    assert lazy.reward > reckless.reward


# --- budget is part of the MDP -----------------------------------------

def test_unaffordable_action_is_refused_not_penalised(world):
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="BETA CORP")],
               price=10.0, budget=1.0)
    env.reset(0)
    r = env.step({"type": "query", "provider": "p", "action": "search"})
    assert r.info["refused"] == "insufficient_budget"
    assert r.reward == 0.0 and not r.done


def test_spend_never_exceeds_the_budget(world):
    seq = [("p", "search")] * 40
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="BETA CORP",
                                 confidence=0.9, rank=0)], price=0.10, budget=0.35)
    rec = run_episode(env, always_deep_verify(seq))
    assert rec.spend_usd <= 0.35 + 1e-9


def test_turn_cap_forces_termination(world):
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="BETA CORP")],
               price=0.0, budget=1.0)
    env.turn_cap = 4
    seq = [("p", "search")] * 100
    rec = run_episode(env, always_deep_verify(seq))
    assert rec.turns <= 4


def test_stepping_after_done_raises(world):
    env = _env(world, [])
    env.reset(0)
    env.step({"type": "abstain"})
    with pytest.raises(RuntimeError):
        env.step({"type": "abstain"})


# --- keel facade --------------------------------------------------------

def test_keel_facade_exposes_reset_step_state(world):
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="BETA CORP",
                                 confidence=0.9, rank=0)])
    k = Keel(env)
    st = k.reset({"index": 0})
    assert st.turnCap == 32 and st.actor == "agent" and not st.done
    assert k.state().prompt == st.prompt
    r = k.step({"type": "query", "provider": "p", "action": "search"})
    assert r.reward == 0.0 and not r.done
    r = k.step({"type": "answer", "person_name": "John Smith",
                "employer_name": "BETA CORP", "confidence": 0.9})
    assert r.done and r.info["outcome"] == "CORRECT"


def test_keel_actor_roles_are_the_frozen_set(world):
    env = _env(world, [])
    for actor in ("agent", "human", "probe"):
        assert Keel(env, actor=actor).reset().actor == actor


def test_provider_title_text_is_classified_by_our_frozen_map(world):
    """Providers return free text. Classifying it is title_map/v1's job, not the
    policy's - a policy handing us a pre-classified enum would be doing our own
    normalization, which is a leak. This was a live defect: the env expected an
    enum, so every answer silently failed the title atom."""
    for text in ("Chief Executive Officer", "CEO", "President and CEO"):
        env = _env(world, [RawAnswer(person_name="John Smith", employer_name="BETA CORP",
                                     title_text=text, confidence=0.9, rank=0)])
        rec = run_episode(env, never_verify(("p", "search")))
        assert rec.atoms.title is True, text


def test_wrong_title_costs_an_atom(world):
    env = _env(world, [RawAnswer(person_name="John Smith", employer_name="BETA CORP",
                                 title_text="General Counsel",
                                 employment_start=date(2022, 1, 1),
                                 confidence=0.9, rank=0)])
    rec = run_episode(env, never_verify(("p", "search")))
    assert rec.outcome is Outcome.CORRECT
    assert rec.atoms.title is False
    # "John Smith" collides, so the identity was pinned by the returned employer
    # and is not independent evidence: title + window only.
    assert rec.atoms.identity_scored is False
    assert rec.atoms.total == pytest.approx(0.5)


def test_identity_atom_is_scored_when_the_name_is_unique(world):
    """The complement: with no collision, identifying the person IS independent
    evidence and does count. See docs/DECISIONS.md D024."""
    rows, idx, iidx, tasks = world
    rows = rows + [
        _row("9", "UNIQUE PERSON", "A", "ALPHA CORP", date(2020, 1, 1)),
        _row("9", "UNIQUE PERSON", "B", "BETA CORP", date(2022, 6, 1)),
    ]
    idx2 = build_index(rows)
    tasks2 = [t for t in build_tasks(rows, idx2)[0] if t.person_cik == "9"]
    env = TiterEnv(tasks2, {"p": FakeProvider("p", [RawAnswer(
        person_name="Unique Person", employer_name="BETA CORP",
        title_text="Chief Executive Officer", employment_start=date(2022, 1, 1),
        confidence=0.9, rank=0)], 0.10)}, idx2, build_issuer_index(rows),
        budget_usd=1.0)
    rec = run_episode(env, never_verify(("p", "search")))
    assert rec.resolution_reason == "unique_name"
    assert rec.atoms.identity_scored is True and rec.atoms.identity is True
    assert rec.atoms.total == 1.0
