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


def normalize_presented(name_raw: str | None) -> str:
    """The name a provider actually faces.

    `normalize` keeps single-letter tokens, because dropping an initial merges
    "John A Smith" into "John Smith" and would manufacture a collision that never
    happened. That is right for RESOLUTION - it is the conservative direction.

    It is wrong for DIFFICULTY. SEC filings carry middle initials; a recruiter
    or a sales tool searching for a person usually does not. Measured over the
    full corpus (2026-09-03): keeping initials, 1.24% of names collide and the
    maximum degree is 7. Dropping them, 5.45% collide and the maximum degree is
    28 - a 4.4x difference in the ambiguity a provider is actually handed.

    So the two are separated on purpose, and both are published:

      * `normalize`           -> resolution. Conservative. Never invents a merge.
      * `normalize_presented` -> difficulty. Realistic. Never used to resolve.

    See docs/DECISIONS.md D027.
    """
    if not name_raw:
        return ""
    canon = _WS.sub(" ", _PUNCT.sub(" ", _TIGHT.sub("", name_raw))).strip().lower()
    tokens = [t for t in canon.split() if len(t) > 1 and t not in _SUFFIXES]
    return " ".join(sorted(tokens))


# Section 16 reporting owners are not all humans. Ten-percent owners are
# routinely funds, LLCs and partnerships, and 419 of the 23,015 built tasks
# (1.82%) name one. A people-search index cannot return a current employer for
# "Permira V L.P.", so every such task is a guaranteed MISS that looks exactly
# like a damning finding about the provider's coverage. Three of the 40 tasks in
# the seed-11 draw were entities: 7.5 points of fabricated error rate.
#
# Caught by running one task through the wire and reading it before spending,
# which is the rule docs/RETRACTIONS.md R001 established after the same class of
# defect cost an entire budget.
#
# Matching is deliberately conservative. Bare HOLDING, TRUST, BANKS, CHURCH and
# PARISH are NOT markers: "HOLDING FRANK B JR" and "TRUST MARTIN" are real
# filers with those surnames, and excluding them would trade a false finding
# about a vendor for a silent narrowing of the population.
ENTITY_NAME = re.compile(
    r"(\b(L\.?L\.?C|L\.?L\.?P|L\.?P|PLC|GMBH|N\.?V|S\.?A|S\.?A\.?R\.?L|PTE|PTY|AB|AG|BV|SARL)\b\.?"
    r"|\b(INC|INCORPORATED|CORP|CORPORATION|LTD|LIMITED|COMPANY|CO)\b\.?\s*$"
    r"|\b(PARTNERS|PARTNERSHIP|HOLDINGS|VENTURES?|ADVISORS?|ADVISERS?|MANAGEMENT|"
    r"CAPITAL|ASSOCIATES|BANCORP|FOUNDATION|PORTFOLIOS?|OFFSHORE)\b)", re.IGNORECASE)


def is_entity_name(name_raw: str | None) -> bool:
    """True when a Section 16 filer name is an organisation, not a person."""
    return bool(name_raw and ENTITY_NAME.search(name_raw))


_NAME_PARTICLES = frozenset({
    "van", "von", "de", "del", "della", "der", "den", "di", "da", "das", "dos",
    "du", "la", "le", "les", "mac", "mc", "st", "ter", "ten", "bin", "ibn",
    "af", "al", "abu", "op", "ver", "vander", "vanden",
})


def presented_query_name(name_raw: str | None) -> str:
    """The name in the order a person actually writes it: "Nima Kelly".

    Distinct from `normalize_presented`, which SORTS its tokens. Sorting is
    right for a collision key, where "REYES GEORGE" and "George Reyes" must
    land on one bucket regardless of order. It is wrong for a provider query,
    and it was silently wrong for **53.4% of the task set**: the sort happens
    to reproduce given-name-first order only when the given name sorts before
    the surname. "REYES GEORGE" -> "George Reyes" is correct by luck (G < R),
    and it is the single example the docstring carried.

    EDGAR conformed names are LAST FIRST MIDDLE, so the surname is token 0.
    """
    if not name_raw:
        return ""
    canon = _WS.sub(" ", _PUNCT.sub(" ", _TIGHT.sub("", name_raw))).strip().lower()
    tokens = [t for t in canon.split() if len(t) > 1 and t not in _SUFFIXES]
    if len(tokens) < 2:
        return " ".join(w.capitalize() for w in tokens)
    # A surname is not always one token. EDGAR files "Van Dask Kristin Lea";
    # taking token 0 as the whole surname yields "Dask Kristin Lea Van". A
    # leading particle absorbs the token after it.
    cut = 0
    while cut < len(tokens) - 1 and tokens[cut] in _NAME_PARTICLES:
        cut += 1
    cut = min(cut + 1, len(tokens) - 1)
    surname, given = tokens[:cut], tokens[cut:]
    # Middle tokens are dropped, for the reason `normalize_presented` already
    # gives above: SEC filings carry them and a person searching for someone
    # does not. Verified live - "Kristin Lea Van Dask Prospect Capital" returns
    # no Van Dask at all, while the same query without the middle name returns
    # her. This is the corpus's own documented difficulty model applied to the
    # query, not a knob turned until the number improved.
    given = given[:1]
    return " ".join(w.capitalize() for w in given + surname)
