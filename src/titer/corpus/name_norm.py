"""name_norm/v1 - FROZEN.

Normalizes a filed person name for two purposes:

1. **Collision degree** - counting distinct RPTOWNERCIK that share a name.
2. **Identity-to-CIK mapping** - resolving what a provider returned back to a
   CIK, decided once and deterministically before any scoring.

Both uses are adversarial to over-normalization. Collapsing too aggressively
inflates collision degree and manufactures false merges that never happened;
collapsing too little misses real collisions and understates the risk. The rule
is therefore conservative: case, punctuation, suffixes and whitespace only.
Nicknames, initials and transliterations are deliberately NOT unified.

Changing anything here requires a new version string and a DECISIONS entry.
See CONTRACTS.md sections 4.1 and 8.
"""
from __future__ import annotations

import re

VERSION = "name_norm/v1"

# Generational and honorific suffixes carry no identity information and vary by
# filing agent. Professional suffixes (PhD, MD, CPA) are also stripped.
# "v" is deliberately ABSENT. It is both a generational suffix and a common
# middle initial, and stripping it merged "SMITH JOHN V" into "SMITH JOHN" -
# manufacturing a collision, which inflates d and therefore the false-merge
# rate that H2 reports. Losing a handful of genuine "V" suffixes is the safer
# direction: it splits one person into two, which shows up as UNRESOLVABLE
# rather than as a fabricated finding about a provider.
_SUFFIXES = {
    "jr", "sr", "ii", "iii", "iv",
    "phd", "md", "cpa", "esq", "jd", "mba", "dds", "dvm",
}
_TIGHT = re.compile(r"[.'\u2019-]")
_PUNCT = re.compile(r"[^\w\s]+")
_WS = re.compile(r"\s+")


def normalize(name_raw: str | None) -> str:
    """Return the canonical form used for collision counting and mapping.

    SEC files names as "LAST FIRST MIDDLE" while providers return "First Last".
    We therefore return a token *set* rendered in sorted order, so the two
    orderings collapse to the same string without us having to guess which
    convention a given row used.
    """
    if not name_raw:
        return ""
    # Periods are deleted, not spaced: "M.D." must reduce to the single suffix
    # token "md", not to two tokens "m" and "d" that no suffix rule can match.
    # Apostrophes and hyphens are deleted, not spaced: RPTOWNERNAME carries
    # "O'BRIEN JOHN" and "OBRIEN JOHN" for the same human, and spacing the
    # apostrophe split them into different people.
    canon = _WS.sub(" ", _PUNCT.sub(" ", _TIGHT.sub("", name_raw))).strip().lower()
    tokens = [t for t in canon.split() if t and t not in _SUFFIXES]
    # Single-letter tokens are initials; they are kept, because dropping them
    # would merge "John A Smith" into "John Smith" and inflate collisions.
    return " ".join(sorted(tokens))


# Corporate suffixes and noise words. An issuer is "MICROSOFT CORP" in EDGAR and
# "Microsoft Corporation" from a provider; running either through `normalize`
# left them distinct, and an unmatched employer resolved to None - which the
# judge then read as CORRECT. Every miss flattered the provider.
_CORP_NOISE = {
    "inc", "incorporated", "corp", "corporation", "co", "company", "llc", "llp",
    "lp", "ltd", "limited", "plc", "sa", "nv", "ag", "gmbh", "ab", "as", "oyj",
    "holdings", "holding", "group", "the", "and", "of", "trust", "reit",
    "partners", "capital", "class",
}


def normalize_company(name_raw: str | None) -> str:
    """Canonical form for an ISSUER name. Separate from `normalize` on purpose:
    person rules strip generational suffixes, company rules strip corporate
    forms, and applying either to the other kind of name is a defect."""
    if not name_raw:
        return ""
    canon = _WS.sub(" ", _PUNCT.sub(" ", _TIGHT.sub("", name_raw))).strip().lower()
    tokens = [t for t in canon.split() if t and t not in _CORP_NOISE]
    return " ".join(tokens) if tokens else canon
