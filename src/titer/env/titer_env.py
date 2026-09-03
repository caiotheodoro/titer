"""The value-of-information environment.

An episode hands the policy one task (docs/DECISIONS.md D022), a set of priced
actions, and a budget. The policy queries providers, or does not, and ends by
naming an identity with a confidence or by abstaining.

The reward is CONTRACTS.md section 6, and the three rules there are enforced
here rather than trusted:

  * **Three program-checked atoms.** Density comes from the filing, not from
    invented process credit.
  * **No shaping terms.** Nothing rewards searching, narrowing candidates, or
    "checking the evidence". Shaped exploration produces performative
    exploration, so there is no code path that can grant it.
  * **The efficiency term applies only among successes.** Charging failures for
    spend rewards failing cheaply, which is `abstain_always` in disguise.

Train and eval share this scoring stack. A different wrapper would be a
different MDP and the checkpoint would be selected against something we do not
report.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any

from titer.adapters.base import BudgetExceeded, Ledger, RawAnswer, Spend
from titer.corpus.collision import CollisionIndex
from titer.corpus.tasks import Task
from titer.corpus.title_map import classify
from titer.costs.profiles import PRIMARY, REPORTABLE, Profile
from titer.oracle.outcome import Answer, Atoms, Outcome, atoms, judge
from titer.oracle.resolve import resolve, resolve_issuer

TURN_CAP = 32   # keel protocol
LAMBDA = 0.30   # weight on spend, applied only among successes


@dataclass
class Observation:
    prompt: str
    turns_left: int
    budget_remaining_usd: float
    available: list[dict[str, Any]]
    candidates: list[dict[str, Any]] = field(default_factory=list)
    done: bool = False


@dataclass
class StepResult:
    observation: Observation
    reward: float
    done: bool
    info: dict[str, Any]


@dataclass
class EpisodeRecord:
    task_id: str
    outcome: Outcome
    atoms: Atoms
    reward: float
    spend_usd: float
    turns: int
    resolution_reason: str
    confidence: float


class TiterEnv:
    """Gymnasium-shaped: `reset` then `step`. The keel facade wraps this."""

    def __init__(self, tasks: list[Task], providers: dict[str, Any],
                 index: CollisionIndex, issuer_index: dict[str, set[str]],
                 budget_usd: float = 1.0, profile_name: str = PRIMARY,
                 turn_cap: int = TURN_CAP, measured_on: date | None = None):
        self.tasks = tasks
        self.providers = providers
        self.index = index
        self.issuer_index = issuer_index
        self.budget_usd = budget_usd
        self.profile_name = profile_name
        self.profile: Profile = REPORTABLE[profile_name]
        self.turn_cap = turn_cap
        self.measured_on = measured_on or date.today()
        self._i = -1
        self.task: Task | None = None

    # --- gym surface -----------------------------------------------------
    def reset(self, index: int | None = None) -> Observation:
        self._i = self._i + 1 if index is None else index
        self.task = self.tasks[self._i % len(self.tasks)]
        self.ledger = Ledger(self.budget_usd)
        self.turns = 0
        self.candidates: list[RawAnswer] = []
        self.done = False
        self.record: EpisodeRecord | None = None
        return self._observe()

    def step(self, action: dict[str, Any]) -> StepResult:
        if self.done:
            raise RuntimeError("step called after the episode ended; call reset")
        self.turns += 1
        kind = action.get("type")

        if kind == "query":
            return self._do_query(action)
        if kind == "answer":
            return self._finish(Answer(
                person_cik=None, confidence=float(action.get("confidence", 0.0))),
                raw=action)
        if kind == "abstain":
            return self._finish(Answer(abstained=True), raw=action)
        raise ValueError(f"unknown action type {kind!r}")

    def state(self) -> Observation:
        return self._observe()

    # --- internals -------------------------------------------------------
    def _observe(self) -> Observation:
        return Observation(
            prompt=self.task.prompt(),
            turns_left=self.turn_cap - self.turns,
            budget_remaining_usd=self.ledger.remaining_usd,
            available=[{"provider": c.provider, "action": c.action,
                        "price_usd": c.list_price_usd,
                        "affordable": self.ledger.can_afford(c.list_price_usd)}
                       for p in self.providers.values() for c in p.actions()],
            candidates=[{"name": a.person_name, "employer": a.employer_name,
                         "title": a.title_text, "rank": a.rank,
                         "employment_start": a.employment_start,
                         "employment_end": a.employment_end,
                         "confidence": a.confidence,
                         "resolution_source": a.resolution_source,
                         "identity_verified": a.identity_verified}
                        for a in self.candidates],
            done=self.done,
        )

    def _do_query(self, action) -> StepResult:
        provider = self.providers[action["provider"]]
        price = next(c.list_price_usd for c in provider.actions()
                     if c.action == action["action"])
        if not self.ledger.can_afford(price):
            # Not an error and not a penalty: the budget is part of the MDP.
            return StepResult(self._observe(), 0.0, False,
                              {"refused": "insufficient_budget", "price_usd": price})
        answers, spend = provider.query(action["action"], self.task.prompt(),
                                        **action.get("kwargs", {}))
        try:
            self.ledger.charge(spend)
        except BudgetExceeded:
            return StepResult(self._observe(), 0.0, False, {"refused": "budget_exceeded"})
        self.candidates.extend(answers)
        out = self._observe()
        if self.turns >= self.turn_cap:
            return self._finish(Answer(abstained=True), raw={"forced": "turn_cap"})
        return StepResult(out, 0.0, False, {"spend_usd": spend.usd, "n": len(answers)})

    def _finish(self, partial: Answer, raw: dict) -> StepResult:
        task = self.task
        reason = "abstained"
        ans = partial
        res = None
        if not partial.abstained:
            name = raw.get("person_name")
            employer_name = raw.get("employer_name")
            employer_cik = resolve_issuer(employer_name, self.issuer_index)
            res = resolve(name, employer_cik, self.index,
                          anchor_issuer_cik=task.anchor_issuer_cik)
            reason = res.reason
            # Providers return title *text*. Classifying it is our own frozen,
            # deterministic step (title_map/v1) - never the policy's, and never
            # a model's. A policy that hands us a pre-classified enum would be
            # doing our normalization for us, which is a leak.
            title_text = raw.get("title_text")
            ans = Answer(
                person_cik=res.person_cik,
                confidence=float(raw.get("confidence", 0.0)),
                employer_cik=employer_cik,
                title_class=classify(title_text) if title_text else None,
                employment_start=raw.get("employment_start"),
                employment_end=raw.get("employment_end"),
            )

        truth = self._truth_tuple(task)
        outcome = judge(ans, truth)
        # The identity atom is scored only when the name alone pinned the
        # person. If a collision had to be broken by the returned employer,
        # identity is implied by the employer answer and scoring both
        # double-counts one signal. See docs/DECISIONS.md D024.
        identity_scored = bool(res is not None and res.independent_of_employer)
        got = atoms(ans, truth, identity_scored=identity_scored)
        reward = self._reward(outcome, got)

        self.done = True
        self.record = EpisodeRecord(
            task_id=task.task_id, outcome=outcome, atoms=got, reward=reward,
            spend_usd=self.ledger.spent.usd, turns=self.turns,
            resolution_reason=reason, confidence=ans.confidence,
        )
        obs = self._observe()
        return StepResult(obs, reward, True, {
            "outcome": outcome.value, "atoms": got.total,
            "spend_usd": self.ledger.spent.usd, "resolution_reason": reason,
        })

    def _truth_tuple(self, task: Task):
        from titer.corpus.schema import AttestedTuple, RoleClass
        return AttestedTuple(
            accession=task.truth_accession, person_cik=task.person_cik,
            person_name_raw=task.person_name_raw, issuer_cik=task.truth_issuer_cik,
            issuer_name_raw=task.truth_issuer_name, issuer_ticker="",
            role_class=frozenset({RoleClass.OFFICER}), title_raw="",
            title_class=task.truth_title_class,
            period=task.truth_period, filed=task.truth_filed,
        )

    def _reward(self, outcome: Outcome, got: Atoms) -> float:
        """CONTRACTS section 6. No shaping term exists anywhere in this method.

        Two earlier defects are fixed here:

        * The atoms were computed and then thrown away for every outcome except
          CORRECT, so a policy that named the right human with the right title
          and was merely STALE scored exactly the same as one returning nothing.
        * There was a flat `ABSTAIN_CREDIT` bonus. Combined with a free provider
          it made stalling to the turn cap - which force-abstains - pay the same
          as answering, and strictly better than answering wrong. That is a
          shaping term rewarding delay, which CONTRACTS 6 prohibits outright.

        Abstention is now priced by the cost profile like every other outcome,
        so the trained objective is the reported loss rather than a proxy for it.
        """
        norm = max(self.profile.values()) or 1.0
        return got.total - self.profile[outcome] / norm - (
            LAMBDA * (self.ledger.spent.usd / self.budget_usd)
            if outcome is Outcome.CORRECT else 0.0
        )
