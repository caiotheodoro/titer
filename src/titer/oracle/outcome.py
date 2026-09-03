"""Decide what happened, by program. No model participates.

Exactly one outcome class applies per task. FALSE_MERGE is separated from
UNSURE_WRONG because being wrong while confident is a materially different
failure from being wrong while hedging - and it is the error that dominates
expected loss under the profiles that matter. See CONTRACTS.md section 4.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum

from titer.corpus.schema import AttestedTuple
from titer.corpus.title_map import TitleClass


class Outcome(str, Enum):
    CORRECT = "CORRECT"
    FALSE_MERGE = "FALSE_MERGE"
    UNSURE_WRONG = "UNSURE_WRONG"
    MISS = "MISS"
    ABSTAIN = "ABSTAIN"
    STALE = "STALE"


@dataclass(frozen=True, slots=True)
class Answer:
    """A provider's or policy's answer, already mapped to a CIK by resolve.py.

    `person_cik is None` means nothing was returned or the return could not be
    resolved. Resolution happens once, deterministically, *before* scoring.
    """

    person_cik: str | None = None
    confidence: float = 0.0
    abstained: bool = False
    employer_cik: str | None = None
    title_class: TitleClass | None = None
    employment_start: date | None = None
    employment_end: date | None = None


DEFAULT_TAU = 0.5


def judge(answer: Answer, truth: AttestedTuple, tau: float = DEFAULT_TAU) -> Outcome:
    if answer.abstained:
        return Outcome.ABSTAIN
    if answer.person_cik is None:
        return Outcome.MISS
    if answer.person_cik != truth.person_cik:
        return Outcome.FALSE_MERGE if answer.confidence >= tau else Outcome.UNSURE_WRONG
    # Right human. The task asked which organisation they were at, so an answer
    # that names no organisation has not answered it.
    #
    # This previously returned CORRECT when `employer_cik` was None, which made
    # withholding the employer strictly better than supplying a wrong one - the
    # metric was non-monotone in provider honesty and every provider's optimal
    # strategy was to return a bare name.
    if answer.employer_cik is None:
        return Outcome.MISS
    if answer.employer_cik != truth.issuer_cik:
        return Outcome.STALE
    return Outcome.CORRECT


@dataclass(frozen=True, slots=True)
class Atoms:
    """The three program-checked reward atoms. CONTRACTS.md section 6.

    **Which atoms are scored is a property of the TASK, never of the answer.**
    An earlier version let the answerer decide - `window_scored` was True only
    if the provider volunteered dates, and the mean was taken over scored atoms
    - so omitting a field RAISED the score. Withholding must never pay.

    `title_scored` is False only when the attested title is UNKNOWN, which is
    our coverage gap and not the answerer's fault (CONTRACTS 3.2). `identity_
    scored` is False when the identity could only be resolved using a fact the
    prompt itself supplied, which would make the atom a parrot check.
    """

    identity: bool
    title: bool
    window: bool
    title_scored: bool = True
    identity_scored: bool = True

    @property
    def total(self) -> float:
        """Mean over the atoms this TASK scores. The window atom is always
        scored: a provider that supplies no dates simply fails it."""
        got = float(self.identity) if self.identity_scored else 0.0
        n = 1 if self.identity_scored else 0
        if self.title_scored:
            got += float(self.title)
            n += 1
        got += float(self.window)
        n += 1
        return got / n if n else 0.0


def atoms(answer: Answer, truth: AttestedTuple, identity_scored: bool = True) -> Atoms:
    identity = answer.person_cik is not None and answer.person_cik == truth.person_cik

    title_scored = truth.title_class is not TitleClass.UNKNOWN
    # `==` not `is`: TitleClass subclasses str, so a value that survived a JSON
    # round-trip as a plain string compares equal but is not identical, and an
    # identity check would silently fail every atom.
    title = title_scored and answer.title_class is not None \
        and answer.title_class == truth.title_class

    # Always scored. No dates supplied means the atom fails, not that it vanishes.
    start, end = answer.employment_start, answer.employment_end
    window = (start is not None and start <= truth.period
              and (end is None or truth.period <= end))

    return Atoms(identity=identity, title=title, window=window,
                 title_scored=title_scored, identity_scored=identity_scored)
