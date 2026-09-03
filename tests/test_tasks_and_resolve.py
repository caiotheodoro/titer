from datetime import date, timedelta

import pytest

from titer.corpus.collision import build_index
from titer.corpus.schema import AttestedTuple, RoleClass
from titer.corpus.tasks import build_tasks
from titer.corpus.title_map import TitleClass
from titer.oracle.resolve import resolve


def _row(cik, name, issuer, period, title=TitleClass.CEO, acc=None):
    return AttestedTuple(
        accession=acc or f"acc-{cik}-{issuer}-{period}",
        person_cik=cik, person_name_raw=name,
        issuer_cik=issuer, issuer_name_raw=f"ISSUER {issuer}", issuer_ticker="T",
        role_class=frozenset({RoleClass.OFFICER}),
        title_raw=title.value, title_class=title,
        period=period, filed=period + timedelta(days=2),
    )


@pytest.fixture
def movers():
    """Two people who moved, one who never did, one same-week dual board seat."""
    return [
        _row("1", "SMITH JOHN", "A", date(2020, 1, 1)),
        _row("1", "SMITH JOHN", "B", date(2022, 6, 1)),      # a real move
        _row("2", "SMITH JOHN", "C", date(2020, 3, 1)),      # same name, other CIK
        _row("2", "SMITH JOHN", "D", date(2023, 3, 1)),
        _row("3", "NEVER MOVED", "E", date(2020, 1, 1)),
        _row("3", "NEVER MOVED", "E", date(2023, 1, 1)),     # same issuer, no move
        _row("4", "DUAL BOARD", "F", date(2021, 1, 1)),
        _row("4", "DUAL BOARD", "G", date(2021, 1, 20)),     # concurrent, not a move
    ]


def test_only_people_who_moved_generate_tasks(movers):
    idx = build_index(movers)
    tasks, stats = build_tasks(movers, idx)
    assert stats.people_total == 4
    assert stats.people_with_a_move == 2
    assert {t.person_cik for t in tasks} == {"1", "2"}


def test_concurrent_directorship_is_not_a_move(movers):
    """Two issuers filed 19 days apart is a second board seat, not a job change.
    Scoring an index for not 'updating' to it would measure nothing."""
    idx = build_index(movers)
    tasks, _ = build_tasks(movers, idx)
    assert "4" not in {t.person_cik for t in tasks}


def test_retained_fraction_is_measured(movers):
    idx = build_index(movers)
    _, stats = build_tasks(movers, idx)
    assert stats.retained_fraction == 0.5


def test_query_fact_and_scored_fact_are_different(movers):
    """D022: the anchor employer is shown, the target employer is scored."""
    idx = build_index(movers)
    tasks, _ = build_tasks(movers, idx)
    for t in tasks:
        assert t.anchor_issuer_cik != t.truth_issuer_cik
        assert t.truth_issuer_cik not in t.prompt()
        assert t.truth_issuer_name not in t.prompt()
        assert t.anchor_issuer_name in t.prompt()


def test_collision_degree_is_attached(movers):
    idx = build_index(movers)
    tasks, _ = build_tasks(movers, idx)
    for t in tasks:
        if t.person_name_raw == "SMITH JOHN":
            assert t.collision_degree == 2
            assert t.collision_band == "low"


def test_elapsed_days_uses_filing_date_not_period(movers):
    idx = build_index(movers)
    t = next(t for t in build_tasks(movers, idx)[0] if t.person_cik == "1")
    as_of = date(2024, 1, 1)
    assert t.elapsed_days(as_of) == (as_of - t.truth_filed).days
    assert t.truth_filed != t.truth_period


# --- resolution ---

def test_unique_name_resolves(movers):
    idx = build_index(movers)
    r = resolve("Never Moved", None, idx)
    assert r.person_cik == "3" and r.reason == "unique_name"


def test_colliding_name_without_employer_is_unresolvable(movers):
    idx = build_index(movers)
    r = resolve("John Smith", None, idx)
    assert not r.resolved and r.reason == "colliding_name_no_employer"


def test_colliding_name_narrowed_by_returned_employer(movers):
    """The employer is an independent signal because the query supplied a
    different one. D022."""
    idx = build_index(movers)
    assert resolve("John Smith", "B", idx).person_cik == "1"
    assert resolve("John Smith", "D", idx).person_cik == "2"


def test_unknown_name_is_unresolvable_not_guessed(movers):
    idx = build_index(movers)
    r = resolve("Nobody At All", "B", idx)
    assert not r.resolved and r.reason == "name_not_in_corpus"


def test_employer_matching_no_candidate_is_unresolvable(movers):
    idx = build_index(movers)
    r = resolve("John Smith", "ZZZ", idx)
    assert not r.resolved and r.reason == "employer_matches_no_candidate"


def test_empty_name_is_unresolvable(movers):
    idx = build_index(movers)
    assert not resolve("", "B", idx).resolved
    assert not resolve(None, "B", idx).resolved
