"""Collect trajectories and rejection-sample the passing ones for SFT.

SFT is what makes RL possible: GRPO amplifies what already sometimes works, so
if the SFT checkpoint never solves a training task there are no advantages to
compute. That is why this module exists before any GRPO config does.

Rejection sampling keeps only trajectories that *succeeded by the oracle*, never
ones that merely looked good. The filter is the same `judge` used at evaluation,
so train and eval share one scoring stack.
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from titer.env.titer_env import EpisodeRecord, TiterEnv
from titer.oracle.outcome import Outcome


@dataclass
class Trajectory:
    task_id: str
    steps: list[dict[str, Any]] = field(default_factory=list)
    outcome: str = ""
    reward: float = 0.0
    spend_usd: float = 0.0
    turns: int = 0

    @property
    def passing(self) -> bool:
        return self.outcome == Outcome.CORRECT.value


def rollout(env: TiterEnv, policy: Callable, index: int) -> Trajectory:
    obs = env.reset(index)
    traj = Trajectory(task_id=env.task.task_id)
    while True:
        action = policy(env, obs)
        result = env.step(action)
        traj.steps.append({"observation": {"prompt": obs.prompt,
                                           "turns_left": obs.turns_left,
                                           "budget_remaining_usd": obs.budget_remaining_usd,
                                           "candidates": obs.candidates},
                           "action": action})
        obs = result.observation
        if result.done:
            rec: EpisodeRecord = env.record
            traj.outcome = rec.outcome.value
            traj.reward = rec.reward
            traj.spend_usd = rec.spend_usd
            traj.turns = rec.turns
            return traj


def collect(env: TiterEnv, policy: Callable, n_tasks: int, k: int = 8
            ) -> list[Trajectory]:
    return [rollout(env, policy, i) for i in range(n_tasks) for _ in range(k)]


def rejection_sample(trajectories: Iterable[Trajectory],
                     max_per_task: int = 2) -> list[Trajectory]:
    """Keep passing trajectories only, capped per task.

    The cap matters: without it, easy tasks dominate the SFT mix and the model
    learns the easy distribution rather than the workflow.
    """
    kept: dict[str, list[Trajectory]] = {}
    for t in trajectories:
        if not t.passing:
            continue
        bucket = kept.setdefault(t.task_id, [])
        if len(bucket) < max_per_task:
            bucket.append(t)
    out = [t for bucket in kept.values() for t in bucket]
    # Cheapest successes first: among successes, spending less is better.
    return sorted(out, key=lambda t: (t.spend_usd, t.turns))


def solve_rates(trajectories: Iterable[Trajectory]) -> dict[str, float]:
    tot: dict[str, int] = {}
    win: dict[str, int] = {}
    for t in trajectories:
        tot[t.task_id] = tot.get(t.task_id, 0) + 1
        win[t.task_id] = win.get(t.task_id, 0) + int(t.passing)
    return {k: win[k] / tot[k] for k in tot}


def in_band(rates: dict[str, float], lo: float = 0.10, hi: float = 0.80) -> list[str]:
    """The RL mix. Always-fail and always-pass tasks contribute noise, not
    learning - they are removed from training and KEPT in evaluation."""
    return [k for k, p in rates.items() if lo <= p <= hi]


def write_jsonl(trajectories: Iterable[Trajectory], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w") as fh:
        for t in trajectories:
            fh.write(json.dumps(asdict(t)) + "\n")
            n += 1
    return n
