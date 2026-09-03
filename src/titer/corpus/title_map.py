"""title_map/v1 - FROZEN.

Normalizes the free-text `RPTOWNER_TITLE` field into a closed class.

Three properties are load-bearing and are asserted by tests:

1. **Regex only.** No model is reachable from this module. It imports nothing
   beyond the standard library, on purpose.
2. **First match wins, in a fixed order.** The order is part of the frozen
   contract, because "President and CEO" matches two rules and the answer must
   not depend on dict iteration order.
3. **Unmatched becomes UNKNOWN, and UNKNOWN is never scored.** Scoring it in
   either direction would convert our own coverage gap into a provider's score.

Changing anything here requires a new version string, a DECISIONS entry and
measured evidence. See CONTRACTS.md section 3.2.
"""
from __future__ import annotations

import re
from enum import Enum

VERSION = "title_map/v1"


class TitleClass(str, Enum):
    CEO = "CEO"
    CFO = "CFO"
    COO = "COO"
    CTO_CIO = "CTO_CIO"
    PRESIDENT = "PRESIDENT"
    CHAIR = "CHAIR"
    GC_LEGAL = "GC_LEGAL"
    OFFICER_OTHER = "OFFICER_OTHER"
    UNKNOWN = "UNKNOWN"


# Ordered. First match wins. Rationale for the order, since it is a contract:
#
#   CEO before PRESIDENT   - "President and CEO" is a chief executive; the CEO
#                            signal is the more specific and more senior one.
#   CFO/COO/CTO before OFFICER_OTHER - specific chiefs before the catch-all.
#   CHAIR after the C-suite - "Chairman and CEO" resolves to CEO, because the
#                            executive role is what a people-search index is
#                            being asked to match, not the board seat.
#   GC_LEGAL before OFFICER_OTHER - "General Counsel" has no C-suite token.
#
# The classes are deliberately COARSE. CTO_CIO is the whole chief
# technology/information family, including CISO and Chief Digital Officer.
# Treasurer is OFFICER_OTHER, not CFO: they are distinct offices, and merging
# them would be a normalization judgement that silently biases a scored atom.
#
# Patterns run against the canonical form: periods deleted, other punctuation
# collapsed to single spaces. Abbreviations allow internal whitespace so that
# both "CEO" and an already-spaced "C E O" resolve identically.
_RULES: tuple[tuple[TitleClass, re.Pattern[str]], ...] = (
    (TitleClass.CEO, re.compile(
        r"\b(c\s*e\s*o|chief\s+exec\w*)\b", re.I)),
    (TitleClass.CFO, re.compile(
        r"\b(c\s*f\s*o|chief\s+financial|principal\s+financial"
        r"(\s+and\s+accounting)?\s+officer)\b", re.I)),
    (TitleClass.COO, re.compile(
        r"\b(c\s*o\s*o|chief\s+operating)\b", re.I)),
    # "Chief Investment Officer" is NOT this class - at insurers and asset
    # managers "CIO" means investment, and mapping the abbreviation here while
    # the spelled-out form fell to OFFICER_OTHER made the two halves of one
    # office disagree, failing the atom on a correct answer.
    (TitleClass.CTO_CIO, re.compile(
        r"\b(c\s*t\s*o|chief\s+(technology|technical|information|digital)"
        r"(\s+security)?\s*(officer)?)\b", re.I)),
    (TitleClass.GC_LEGAL, re.compile(
        r"\b(general\s+counsel|chief\s+legal|gen\s+counsel)\b", re.I)),
    # The lookbehinds are load-bearing: "Senior Vice President" is not the
    # President, and a bare \bpresident\b matches inside it. This was a real
    # defect, caught by smoke-testing before any data existed.
    (TitleClass.PRESIDENT, re.compile(
        r"(?<!vice )(?<!vice-)\bpresident\b", re.I)),
    # The vice/deputy guard was written for President and never applied here:
    # "Vice Chairman" and "Deputy Chairman" are not the Chair. A committee
    # chair is not the board Chair either.
    (TitleClass.CHAIR, re.compile(
        r"(?<!vice )(?<!deputy )(?<!co )\b(chairman|chairwoman|chairperson|chair)\b"
        r"(?!\s*,?\s*\w+\s+committee)", re.I)),
    (TitleClass.OFFICER_OTHER, re.compile(
        # Measured against the built corpus (2026-09-03): these are the real
        # filed strings that were falling to UNKNOWN. "Vice Chairman" is an
        # office, and excluding it from CHAIR (correctly) must not drop it out
        # of the taxonomy altogether.
        r"\b(chief\s+\w+\s+officer|officer|vice\s+president|v\s*p|evp|svp|sevp|"
        r"vice\s+chair(man|woman|person)?|deputy\s+chair(man|woman|person)?|"
        r"c\s*a\s*o|secretary|controller|treasurer|principal\s+accounting|"
        r"managing\s+director)\b", re.I)),
)

_DOT = re.compile(r"\.")
_PUNCT = re.compile(r"[^\w\s]+")
_WS = re.compile(r"\s+")


def _canon(raw: str) -> str:
    """Canonical form for matching.

    Periods are *deleted* rather than replaced with a space, so "C.E.O."
    becomes "CEO" and not "C E O". Every other punctuation mark becomes a
    space. Word content is otherwise untouched.
    """
    return _WS.sub(" ", _PUNCT.sub(" ", _DOT.sub("", raw))).strip()


def classify(title_raw: str | None) -> TitleClass:
    """Map a raw filed title to its closed class.

    An empty or unmatched title is UNKNOWN. UNKNOWN is excluded from the title
    atom rather than scored - see CONTRACTS.md section 3.2.
    """
    if not title_raw or not title_raw.strip():
        return TitleClass.UNKNOWN
    canon = _canon(title_raw)
    for cls, pattern in _RULES:
        if pattern.search(canon):
            return cls
    return TitleClass.UNKNOWN
