"""Build measurement tasks from the corpus. See docs/DECISIONS.md D022.

One task family serves both R1 and R2:

    Person named N, who was <role> at issuer A on t1 (attested).
    What organisation were they at on t2?

The query supplies t1's employer; the scored fact is t2's employer. They are
never the same fact, which is what keeps the scoring non-circular.

This requires a person who actually moved - at least two distinct attested
issuers at two distinct times. The retained fraction is a measured coverage
number, published rather than estimated.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Iterable, Sequence

from titer.corpus.collision import CollisionIndex, band
from titer.corpus.schema import AttestedTuple
from titer.corpus.title_map import TitleClass


@dataclass(frozen=True, slots=True)
class Task:
    """What is shown to a provider, and what is held back to score it."""

    # --- shown ---
    person_name_raw: str
    anchor_issuer_cik: str
    anchor_issuer_name: str
    anchor_title_class: TitleClass
    anchor_date: date
    target_date: date
    # --- held back ---
    person_cik: str
    truth_issuer_cik: str
    truth_issuer_name: str
    truth_title_class: TitleClass
    truth_period: date
    truth_filed: date
    truth_accession: str
    collision_degree: int

    @property
    def task_id(self) -> str:
        raw = "|".join([self.person_cik, self.anchor_issuer_cik,
                        self.truth_issuer_cik, self.target_date.isoformat()])
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    @property
    def collision_band(self) -> str:
        return band(self.collision_degree)

    def elapsed_days(self, as_of: date) -> int:
        """Days between the move becoming public and the measurement.

        Computed from `truth_filed`, not `truth_period`: the filing date is the
        earliest moment the fact was available to anyone, including the index.
        """
        return (as_of - self.truth_filed).days

    def prompt(self) -> str:
        """The anchor EMPLOYER identifies the person; the anchor TITLE is not
        emitted.

        Titles persist across a move for most executives, and title_map has only
        nine coarse classes, so printing the anchor title handed the provider
        the answer to reward atom 2 - a parrot could pass it by echoing the
        prompt. The employer alone is enough to disambiguate, and the employer
        we print is the one we do NOT score.
        """
        return (
            f"{self.person_name_raw} was an officer or director at "
            f"{self.anchor_issuer_name} as of {self.anchor_date.isoformat()}. "
            f"What organisation were they at on {self.target_date.isoformat()}, "
            f"and in what role?"
        )


@dataclass
class TaskStats:
    people_total: int = 0
    people_with_a_move: int = 0
    tasks: int = 0

    @property
    def retained_fraction(self) -> float:
        return self.people_with_a_move / self.people_total if self.people_total else 0.0


def build_tasks(rows: Iterable[AttestedTuple], index: CollisionIndex,
                min_gap_days: int = 180) -> tuple[list[Task], TaskStats]:
    """One task per person who moved.

    `min_gap_days` guards against two issuers filed in the same week, which is
    a concurrent directorship rather than a move - scoring an index for not
    "updating" to a second simultaneous board seat would measure nothing.
    """
    by_person: dict[str, list[AttestedTuple]] = defaultdict(list)
    for r in rows:
        by_person[r.person_cik].append(r)

    stats = TaskStats(people_total=len(by_person))
    tasks: list[Task] = []
    for cik, rs in by_person.items():
        rs.sort(key=lambda r: (r.period, r.filed, r.accession))
        anchor = rs[0]
        anchor_periods = [r.period for r in rs if r.issuer_cik == anchor.issuer_cik]
        last_at_anchor = max(anchor_periods)
        target = None
        for r in rs[1:]:
            if r.issuer_cik == anchor.issuer_cik:
                continue
            if (r.period - anchor.period).days < min_gap_days:
                continue
            # A move means they LEFT. Concurrent multi-board directorships are
            # the norm in this population, and without this check a director who
            # joins board B while still sitting on board A generates a task whose
            # ground truth says "B" - so a provider answering "A" is scored STALE
            # for being factually right, contaminating H1's staleness signal.
            if r.period <= last_at_anchor:
                continue
            target = r
            break
        if target is None:
            continue
        stats.people_with_a_move += 1
        tasks.append(Task(
            person_name_raw=anchor.person_name_raw,
            anchor_issuer_cik=anchor.issuer_cik,
            anchor_issuer_name=anchor.issuer_name_raw,
            anchor_title_class=anchor.title_class,
            anchor_date=anchor.period,
            target_date=target.period,
            person_cik=cik,
            truth_issuer_cik=target.issuer_cik,
            truth_issuer_name=target.issuer_name_raw,
            truth_title_class=target.title_class,
            truth_period=target.period,
            truth_filed=target.filed,
            truth_accession=target.accession,
            collision_degree=index.degree(anchor.person_name_norm),
        ))
    stats.tasks = len(tasks)
    return tasks, stats


def band_distribution(tasks: Sequence[Task]) -> dict[str, int]:
    out: dict[str, int] = {}
    for t in tasks:
        out[t.collision_band] = out.get(t.collision_band, 0) + 1
    return out
