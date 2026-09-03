"""Map a provider's returned identity back to a CIK. Deterministic, no model.

This is a documented seam (docs/ARCHITECTURE.md). Two properties matter:

1. **It never uses a fact that was supplied in the query.** The task hands the
   provider the *anchor* employer and scores the *target* employer, so
   resolving on the returned employer keeps the signal independent. See D022.
2. **Ambiguity is recorded, not guessed.** An identity that cannot be pinned to
   exactly one CIK is UNRESOLVABLE and is excluded from scoring with the rate
   published. Guessing here would manufacture whichever outcome we guessed.
"""
from __future__ import annotations

from dataclasses import dataclass

from titer.corpus.collision import CollisionIndex
from titer.corpus.name_norm import normalize

UNRESOLVABLE = None


@dataclass(frozen=True, slots=True)
class Resolution:
    person_cik: str | None
    reason: str

    @property
    def resolved(self) -> bool:
        return self.person_cik is not None


def resolve(returned_name: str | None, returned_employer_cik: str | None,
            index: CollisionIndex) -> Resolution:
    """Resolve (name, employer) to a CIK, or explain why it cannot be done."""
    if not returned_name or not returned_name.strip():
        return Resolution(UNRESOLVABLE, "no_name_returned")

    norm = normalize(returned_name)
    candidates = index.ciks_by_name.get(norm, set())
    if not candidates:
        return Resolution(UNRESOLVABLE, "name_not_in_corpus")
    if len(candidates) == 1:
        return Resolution(next(iter(candidates)), "unique_name")

    # Collision. The returned employer is an independent signal because the
    # query supplied a *different* employer.
    if not returned_employer_cik:
        return Resolution(UNRESOLVABLE, "colliding_name_no_employer")
    narrowed = {c for c in candidates
                if returned_employer_cik in index.issuers_by_cik.get(c, set())}
    if len(narrowed) == 1:
        return Resolution(next(iter(narrowed)), "narrowed_by_employer")
    if not narrowed:
        return Resolution(UNRESOLVABLE, "employer_matches_no_candidate")
    return Resolution(UNRESOLVABLE, "still_ambiguous_after_employer")


def resolve_issuer(returned_employer: str | None,
                   issuer_index: dict[str, set[str]]) -> str | None:
    """Map a returned employer *name* to an issuer CIK.

    `issuer_index` maps a normalized issuer name to the CIKs filed under it.
    Ambiguous or unknown names return None rather than a guess: an invented
    employer CIK would flip an outcome between CORRECT and STALE.
    """
    if not returned_employer or not returned_employer.strip():
        return None
    key = normalize(returned_employer)
    ciks = issuer_index.get(key, set())
    return next(iter(ciks)) if len(ciks) == 1 else None


def build_issuer_index(rows) -> dict[str, set[str]]:
    from collections import defaultdict
    out: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        n = normalize(r.issuer_name_raw)
        if n:
            out[n].add(r.issuer_cik)
    return dict(out)
