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
    # Right human. Is the employer the one attested on this date?
    if answer.employer_cik is not None and answer.employer_cik != truth.issuer_cik:
        return Outcome.STALE
    return Outcome.CORRECT


@dataclass(frozen=True, slots=True)
class Atoms:
    """The three program-checked reward atoms. CONTRACTS.md section 6.

    `title_scored` is False when the attested title is UNKNOWN: that atom is
    then excluded rather than counted as a match or a mismatch, because scoring
    it either way converts our coverage gap into the answerer's score.
    """

    identity: bool
    title: bool
    title_scored: bool
    window: bool
    window_scored: bool

    @property
    def total(self) -> float:
        """Sum over scored atoms only, so an excluded atom neither helps nor hurts."""
        got = float(self.identity)
        n = 1
        if self.title_scored:
            got += float(self.title)
            n += 1
        if self.window_scored:
            got += float(self.window)
            n += 1
        return got / n


def atoms(answer: Answer, truth: AttestedTuple) -> Atoms:
    identity = answer.person_cik is not None and answer.person_cik == truth.person_cik

    title_scored = truth.title_class is not TitleClass.UNKNOWN
    title = title_scored and answer.title_class is truth.title_class

    window_scored = answer.employment_start is not None
    window = False
    if window_scored:
        start = answer.employment_start
        end = answer.employment_end
        window = start <= truth.period and (end is None or truth.period <= end)

    return Atoms(identity=identity, title=title, title_scored=title_scored,
                 window=window, window_scored=window_scored)
