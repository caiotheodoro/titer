"""Fit a cost/error model to the replay cache, and sample from it.

Live RL rollouts are arithmetically impossible at $5 a verification, so the
policy trains against this simulator and is *evaluated on held-out real calls*.
The gap between the two is R4's central limitation and is published as a number.

Two rules keep that number meaningful:

1. **The simulator never sees the evaluation split.** It is fitted on the
   training portion of the cache only. A simulator fitted on the eval set makes
   the sim-to-real gap unmeasurable, which is the one thing this module exists
   to expose. `fit` raises if handed the eval split.
2. **It is fitted per (provider, action, collision band).** Accuracy that falls
   with collision degree is the structure R2 measures; a simulator that averaged
   it away would train a policy on a world where disambiguation is never worth
   paying for.
"""
from __future__ import annotations

import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Sequence

from titer.adapters.base import RawAnswer, Spend
from titer.corpus.tasks import Task
from titer.oracle.outcome import Outcome


@dataclass(frozen=True, slots=True)
class Cell:
    """Observed behaviour of one (provider, action) at one collision band."""

    n: int
    p_correct: float
    p_stale: float
    p_wrong_person: float
    p_miss: float
    mean_confidence: float
    mean_spend_usd: float

    def check(self) -> None:
        total = self.p_correct + self.p_stale + self.p_wrong_person + self.p_miss
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"cell probabilities sum to {total}, not 1.0")


@dataclass
class FittedModel:
    cells: dict[tuple[str, str, str], Cell] = field(default_factory=dict)
    fallback: Cell | None = None
    split_fitted_on: str = "train"

    def cell_for(self, provider: str, action: str, band: str) -> Cell:
        c = self.cells.get((provider, action, band))
        if c is not None:
            return c
        if self.fallback is None:
            raise KeyError(f"no fitted cell for {(provider, action, band)} and no fallback")
        return self.fallback

    def coverage(self) -> dict[str, int]:
        return {f"{p}/{a}/{b}": c.n for (p, a, b), c in self.cells.items()}


@dataclass(frozen=True, slots=True)
class Observation:
    provider: str
    action: str
    band: str
    outcome: Outcome
    confidence: float
    spend_usd: float


def fit(observations: Sequence[Observation], split: str = "train",
        min_cell_n: int = 5) -> FittedModel:
    """Fit per (provider, action, band). Thin cells fall back to the pooled cell,
    and the pooling is visible in `coverage()` rather than silent."""
    if split != "train":
        raise ValueError(
            f"refusing to fit the simulator on the {split!r} split. Fitting on "
            "evaluation data makes the sim-to-real gap unmeasurable, which is the "
            "one number this module exists to expose."
        )
    groups: dict[tuple[str, str, str], list[Observation]] = defaultdict(list)
    for o in observations:
        groups[(o.provider, o.action, o.band)].append(o)

    def cell_of(obs: list[Observation]) -> Cell:
        n = len(obs)
        c = Cell(
            n=n,
            p_correct=sum(o.outcome is Outcome.CORRECT for o in obs) / n,
            p_stale=sum(o.outcome is Outcome.STALE for o in obs) / n,
            p_wrong_person=sum(o.outcome in (Outcome.FALSE_MERGE, Outcome.UNSURE_WRONG)
                               for o in obs) / n,
            p_miss=sum(o.outcome in (Outcome.MISS, Outcome.ABSTAIN) for o in obs) / n,
            mean_confidence=sum(o.confidence for o in obs) / n,
            mean_spend_usd=sum(o.spend_usd for o in obs) / n,
        )
        c.check()
        return c

    model = FittedModel(split_fitted_on=split)
    if observations:
        model.fallback = cell_of(list(observations))
    for key, obs in groups.items():
        if len(obs) >= min_cell_n:
            model.cells[key] = cell_of(obs)
    return model


class SimulatedProvider:
    """Samples from a fitted cell instead of calling a vendor.

    Deterministic under a seed, so a training run is reproducible without
    network access or spend.
    """

    def __init__(self, name: str, action: str, model: FittedModel,
                 task_ref: dict, price_usd: float, seed: int = 11):
        self.name = name
        self._action = action
        self._model = model
        self._ref = task_ref
        self._price = price_usd
        self._rng = random.Random(seed)

    def actions(self):
        from titer.adapters.base import Call
        return [Call(self.name, self._action, self._price)]

    def query(self, action: str, prompt: str, **kw):
        task: Task = self._ref["task"]
        cell = self._model.cell_for(self.name, action, task.collision_band)
        u = self._rng.random()
        conf = cell.mean_confidence
        if u < cell.p_correct:
            a = RawAnswer(person_name=task.person_name_raw,
                          employer_name=task.truth_issuer_name,
                          title_text=task.truth_title_class.value,
                          confidence=conf, rank=0)
        elif u < cell.p_correct + cell.p_stale:
            a = RawAnswer(person_name=task.person_name_raw,
                          employer_name=task.anchor_issuer_name,
                          title_text=task.anchor_title_class.value,
                          confidence=conf, rank=0)
        elif u < cell.p_correct + cell.p_stale + cell.p_wrong_person:
            a = RawAnswer(person_name=task.person_name_raw,
                          employer_name=self._ref.get("decoy_employer"),
                          title_text=None, confidence=conf, rank=0)
        else:
            a = RawAnswer(person_name=None, employer_name=None, confidence=0.0, rank=0)
        return [a], Spend(cell.mean_spend_usd or self._price, 1.0, "unit")
