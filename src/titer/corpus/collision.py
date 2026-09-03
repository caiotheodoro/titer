"""Name-collision degree, and the same-human-two-CIK contamination bound.

`d(name)` is the number of distinct RPTOWNERCIK sharing a normalized name. It
is a measured property of the corpus and it indexes the FALSE_MERGE failure
mode directly, which is why it is the difficulty axis (CONTRACTS.md section 8).

The contamination bound is the other half. A CIK is unique per *filer
registration*, not per human, so two CIKs sharing a name may be one person who
registered twice. Counting those as collisions would manufacture false merges
that never happened. We therefore estimate an upper bound - distinct CIKs
sharing a normalized name AND an overlapping issuer - and report FALSE_MERGE
both raw and net of it. See CONTRACTS.md section 4.2.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Iterable

from titer.corpus.schema import AttestedTuple


def band(d: int) -> str:
    if d <= 1:
        return "unique"
    if d <= 3:
        return "low"
    if d <= 9:
        return "medium"
    return "high"


@dataclass
class CollisionIndex:
    ciks_by_name: dict[str, set[str]]
    issuers_by_cik: dict[str, set[str]]

    def degree(self, name_norm: str) -> int:
        return len(self.ciks_by_name.get(name_norm, ()))

    def band_of(self, name_norm: str) -> str:
        return band(self.degree(name_norm))

    def contamination_bound(self) -> dict[str, float | int]:
        """Upper bound on same-human-two-CIK pairs.

        A pair of distinct CIKs that share a normalized name *and* at least one
        issuer is far more likely to be one human registered twice than two
        different humans who happen to share a name and an employer. This is an
        upper bound on contamination, not an estimate of it: some such pairs are
        genuinely two people (a father and son at a family firm, say).
        """
        suspect_names = 0
        suspect_pairs = 0
        colliding_names = 0
        for name, ciks in self.ciks_by_name.items():
            if len(ciks) < 2:
                continue
            colliding_names += 1
            ordered = sorted(ciks)
            hit = False
            for i, a in enumerate(ordered):
                for b in ordered[i + 1:]:
                    if self.issuers_by_cik.get(a, set()) & self.issuers_by_cik.get(b, set()):
                        suspect_pairs += 1
                        hit = True
            if hit:
                suspect_names += 1
        return {
            "colliding_names": colliding_names,
            "suspect_names": suspect_names,
            "suspect_pairs": suspect_pairs,
            "suspect_name_rate": (suspect_names / colliding_names) if colliding_names else 0.0,
        }


def build_index(rows: Iterable[AttestedTuple]) -> CollisionIndex:
    ciks_by_name: dict[str, set[str]] = defaultdict(set)
    issuers_by_cik: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        n = r.person_name_norm
        if n:
            ciks_by_name[n].add(r.person_cik)
        issuers_by_cik[r.person_cik].add(r.issuer_cik)
    return CollisionIndex(dict(ciks_by_name), dict(issuers_by_cik))
