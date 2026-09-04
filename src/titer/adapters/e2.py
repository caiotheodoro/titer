"""E2 / D029 renderings: four ways to ask about the same person.

E2 asks whether a capability constraint disambiguates a colliding name. Every
arm receives the identical task in the identical order; the ONLY difference is
how much biographical context the query carries. Differences are within-task.

The arms are D029's:

    A  name alone                        baseline ambiguity
    B  name + a current-state filter     what today's filters buy   (Ploid only)
    C  name + history in free text       whether the index uses it
    D  name + history, oracle-supplied   the ceiling

Supported if C ~= A and D > B: the index cannot exploit history even when it is
handed it. Falsified if C > A, which would mean the semantic query field already
absorbs biographical context.

Every arm withholds the scored fact - the employer at the target date. Arms
deliberately differ in DISCLOSURE, which is the experiment; they do not differ
in what is being asked.
"""
from __future__ import annotations

from titer.adapters.providers import _company_for_filter
from titer.corpus.name_norm import presented_query_name

QUESTION = ("What organisation are they at most recently, and in what role? "
            "Answer for their latest known position.")
CONF = " Give your confidence as a number between 0 and 1."


def exa_name_only(task) -> str:
    """A. The name and nothing else."""
    return f"{presented_query_name(task.person_name_raw)}. {QUESTION}{CONF}"


def exa_anchor_freetext(task) -> str:
    """C. The name plus a past employer, stated as history in free text."""
    return (f"{presented_query_name(task.person_name_raw)}, who previously "
            f"worked at {_company_for_filter(task.anchor_issuer_name)}. "
            f"{QUESTION}{CONF}")


def exa_full_context(task) -> str:
    """D. The ceiling: every attested anchor-side fact a caller could hold.

    Role, employer and date. Never the target employer, which is the answer.
    """
    return (f"{presented_query_name(task.person_name_raw)} was an officer or "
            f"director at {task.anchor_issuer_name} as of "
            f"{task.anchor_date.isoformat()}, with the role "
            f"{task.anchor_title_class.value}. {QUESTION}{CONF}")


def ploid_company_filter(task) -> dict:
    """B. The structured filter the API documents.

    D028 C1 established that this filter selects people CURRENTLY at that
    company, so it tends to return the anchor - which is the point of the arm.
    It measures what a current-state filter buys on a colliding name, and the
    answer being 'the anchor' is a finding about the filter, not a defect.
    """
    return {"query": presented_query_name(task.person_name_raw),
            "filters": {"company": _company_for_filter(task.anchor_issuer_name)}}
