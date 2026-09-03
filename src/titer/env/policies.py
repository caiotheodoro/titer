"""The floors. Every one of these is reported, including if it wins.

`assay`'s bar: the arm that has to be beaten is the trivial floor, not the
incumbent. Three trivial policies bracket the value-of-information problem from
both ends - spend nothing and trust rank 1, spend everything, or answer nothing.
A trained policy that cannot beat all three has not learned to price certainty.
"""
from __future__ import annotations

from typing import Any, Callable

Policy = Callable[[Any, Any], dict[str, Any]]   # (env, observation) -> action


def _answer_from_top(obs) -> dict[str, Any]:
    if not obs.candidates:
        return {"type": "answer", "person_name": None, "employer_name": None,
                "confidence": 0.0}
    top = obs.candidates[0]
    return {"type": "answer", "person_name": top["name"],
            "employer_name": top["employer"],
            "title_text": top.get("title"),
            "employment_start": top.get("employment_start"),
            "employment_end": top.get("employment_end"),
            "confidence": max(float(top.get("confidence") or 0.0), 0.9)}


def never_verify(cheapest_action: tuple[str, str]) -> Policy:
    """One cheapest search, take rank 1, answer confidently. Spends the minimum
    and never pays to disambiguate - the naive integration a developer writes
    on day one."""
    provider, action = cheapest_action
    state = {"queried": False}

    def policy(env, obs):
        if not state["queried"]:
            state["queried"] = True
            return {"type": "query", "provider": provider, "action": action}
        state["queried"] = False
        return _answer_from_top(obs)

    return policy


def always_deep_verify(sequence: list[tuple[str, str]]) -> Policy:
    """Run every action in order, most expensive included, then answer. Spends
    the maximum on every task regardless of whether the first result was
    already unambiguous."""
    state = {"i": 0}

    def policy(env, obs):
        while state["i"] < len(sequence):
            provider, action = sequence[state["i"]]
            state["i"] += 1
            price = next((a["price_usd"] for a in obs.available
                          if a["provider"] == provider and a["action"] == action), 0.0)
            if price <= obs.budget_remaining_usd:
                return {"type": "query", "provider": provider, "action": action}
        state["i"] = 0
        return _answer_from_top(obs)

    return policy


def abstain_always(env=None, obs=None) -> dict[str, Any]:
    """The degenerate floor. It must LOSE under every reportable profile - if it
    does not, the abstention credit is mis-set and the reward is hackable.
    docs/RED-TEAM.md A8 asserts exactly this."""
    return {"type": "abstain"}


def run_episode(env, policy: Policy, index: int | None = None):
    obs = env.reset(index)
    while True:
        action = policy(env, obs) if policy is not abstain_always else abstain_always()
        result = env.step(action)
        obs = result.observation
        if result.done:
            return env.record
