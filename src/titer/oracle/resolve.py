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
from titer.corpus.name_norm import (normalize_company,
                                    normalize_presented)

UNRESOLVABLE = None


@dataclass(frozen=True, slots=True)
class Resolution:
    person_cik: str | None
    reason: str

    @property
    def resolved(self) -> bool:
        return self.person_cik is not None

    @property
    def independent_of_employer(self) -> bool:
        """True only when the NAME alone pinned the identity.

        Whenever a collision had to be broken by the returned employer, the
        identity atom carries no information the employer check does not
        already carry: state the right employer and you have, by construction,
        picked the right same-name person. Scoring both double-counts one
        signal, and it double-counts hardest at high collision degree - the
        exact axis H2 stratifies on. Only `unique_name` is independent evidence.
        """
        return self.reason == "unique_name"


def resolve(returned_name: str | None, returned_employer_cik: str | None,
            index: CollisionIndex, anchor_issuer_cik: str | None = None) -> Resolution:
    """Resolve (name, employer) to a CIK, or explain why it cannot be done.

    `anchor_issuer_cik` is the employer the PROMPT supplied. Narrowing on it
    still works - we need it to tell STALE from FALSE_MERGE - but the resolution
    is tagged `narrowed_by_anchor`, and the caller must then refuse to score the
    identity atom. Otherwise a provider that parrots back the name and employer
    it was handed is credited with having identified the person, and the credit
    grows with collision degree, which is the exact axis H2 stratifies on.
    """
    if not returned_name or not returned_name.strip():
        return Resolution(UNRESOLVABLE, "no_name_returned")

    # Keyed on the PRESENTED form, not the strict one. SEC files "SMITH MARK L"
    # and providers return "Mark Smith"; a strict lookup matches neither to the
    # other and returns name_not_in_corpus for every honest answer. Worse, it
    # was not symmetric: an arm that happened to ECHO our SEC-format name
    # resolved fine while one returning a normal human name did not, which
    # advantaged the parrot. Measured in the W3 pilot: 4/6 Ploid answers
    # unresolvable against 4/7 Exa answers resolving by unique_name largely
    # because Exa repeated the name from the prompt.
    norm = normalize_presented(returned_name)
    candidates = index.ciks_by_presented.get(norm, set()) if index.ciks_by_presented \
        else index.ciks_by_name.get(norm, set())
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
        reason = ("narrowed_by_anchor"
                  if anchor_issuer_cik is not None
                  and returned_employer_cik == anchor_issuer_cik
                  else "narrowed_by_employer")
        return Resolution(next(iter(narrowed)), reason)
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
    key = normalize_company(returned_employer)
    ciks = issuer_index.get(key, set())
    return next(iter(ciks)) if len(ciks) == 1 else None


def build_issuer_index(rows) -> dict[str, set[str]]:
    from collections import defaultdict
    out: dict[str, set[str]] = defaultdict(set)
    for r in rows:
        n = normalize_company(r.issuer_name_raw)
        if n:
            out[n].add(r.issuer_cik)
    return dict(out)
