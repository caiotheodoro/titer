"""keel protocol facade.

`keel/docs/superpowers/specs/00-keel-protocol.md` froze reset/step/state with
`Actor = agent | human | probe` and `turnCap: 32`, and was never implemented.
This is its first implementation.

The facade is deliberately thin: OpenEnv is the primary surface because train
and eval must share the same scoring stack, and a bespoke gym would be a
different MDP. keel gets a faithful interface over that, not a reimplementation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal

from titer.env.titer_env import TURN_CAP, TiterEnv

Actor = Literal["agent", "human", "probe"]
Facade = Literal["webmcp", "http", "ui"]
Rung = Literal["smoke", "regression", "hill-climb"]


@dataclass
class EpisodeState:
    prompt: str
    turnsLeft: int
    turnCap: int
    budgetRemainingUsd: float
    candidates: list[dict[str, Any]]
    done: bool
    actor: Actor = "agent"


@dataclass
class StepResult:
    state: EpisodeState
    reward: float
    done: bool
    info: dict[str, Any]


class Keel:
    """reset / step / state over TiterEnv."""

    turnCap = TURN_CAP

    def __init__(self, env: TiterEnv, actor: Actor = "agent"):
        self._env = env
        self._actor = actor

    def _state_from(self, obs) -> EpisodeState:
        return EpisodeState(
            prompt=obs.prompt, turnsLeft=obs.turns_left, turnCap=self.turnCap,
            budgetRemainingUsd=obs.budget_remaining_usd,
            candidates=obs.candidates, done=obs.done, actor=self._actor,
        )

    def reset(self, req: dict[str, Any] | None = None) -> EpisodeState:
        idx = (req or {}).get("index")
        return self._state_from(self._env.reset(idx))

    def step(self, action: dict[str, Any]) -> StepResult:
        r = self._env.step(action)
        return StepResult(self._state_from(r.observation), r.reward, r.done, r.info)

    def state(self) -> EpisodeState:
        return self._state_from(self._env.state())

    def as_dict(self) -> dict[str, Any]:
        return asdict(self.state())
