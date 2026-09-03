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
_SUFFIXES = {
    "jr", "sr", "ii", "iii", "iv", "v",
    "phd", "md", "cpa", "esq", "jd", "mba", "dds", "dvm",
}
_DOT = re.compile(r"\.")
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
    canon = _WS.sub(" ", _PUNCT.sub(" ", _DOT.sub("", name_raw))).strip().lower()
    tokens = [t for t in canon.split() if t and t not in _SUFFIXES]
    # Single-letter tokens are initials; they are kept, because dropping them
    # would merge "John A Smith" into "John Smith" and inflate collisions.
    return " ".join(sorted(tokens))
