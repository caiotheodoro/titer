from datetime import date

from titer.corpus.build import CONTACT_FIELDS, build_quarter
from titer.corpus.collision import build_index
from titer.corpus.schema import ExclusionCounts, RoleClass
from titer.corpus.title_map import TitleClass


def test_every_counter_reconciles(quarter_zip):
    """A row cannot be dropped without being counted."""
    counts = ExclusionCounts()
    build_quarter(quarter_zip, counts)
    counts.reconcile()
    assert counts.input_rows == 11
    assert counts.kept == 4


def test_each_exclusion_rule_fires(quarter_zip):
    counts = ExclusionCounts()
    build_quarter(quarter_zip, counts)
    assert counts.entity_not_human == 1        # TenPercentOwner-only
    assert counts.no_officer_or_director == 1  # Other-only
    assert counts.unparseable_date == 1
    assert counts.period_after_filed == 1
    assert counts.quarter_before_2003q3 == 1
    assert counts.bad_person_cik == 1
    assert counts.unjoined_accession == 1


def test_contact_fields_never_survive_ingest(quarter_zip):
    """docs/ETHICS.md 2.1: stripped at ingest, not at publication."""
    rows = build_quarter(quarter_zip, ExclusionCounts())
    for r in rows:
        blob = repr(r)
        for token in ("Main St", "Springfield", "62701", "Suite 5", "ILLINOIS"):
            assert token not in blob
    for f in CONTACT_FIELDS:
        assert "STREET" in f or "CITY" in f or "STATE" in f or "ZIP" in f


def test_fields_are_carried_faithfully(quarter_zip):
    rows = build_quarter(quarter_zip, ExclusionCounts())
    ceo = next(r for r in rows if r.person_cik == "1000001")
    assert ceo.issuer_cik == "320193"
    assert ceo.issuer_ticker == "AAPL"
    assert ceo.title_class is TitleClass.CEO
    assert ceo.title_raw == "Chief Executive Officer"   # raw retained beside class
    assert ceo.period == date(2025, 2, 13)
    assert ceo.filed == date(2025, 2, 15)
    assert ceo.role_class == frozenset({RoleClass.OFFICER})


def test_unknown_title_is_counted_but_kept(quarter_zip):
    """CONTRACTS 3.2: UNKNOWN is excluded from the title *atom*, not the corpus."""
    counts = ExclusionCounts()
    rows = build_quarter(quarter_zip, counts)
    assert counts.title_unknown == 1
    assert any(r.title_class is TitleClass.UNKNOWN for r in rows)


def test_signature_is_accession_independent(quarter_zip):
    """Two filings of the same fact are one task and must not straddle a split."""
    rows = build_quarter(quarter_zip, ExclusionCounts())
    a = rows[0]
    import dataclasses
    b = dataclasses.replace(a, accession="9999-99-999999")
    assert a.signature() == b.signature()


def test_signature_separates_different_facts(quarter_zip):
    rows = build_quarter(quarter_zip, ExclusionCounts())
    sigs = {r.signature() for r in rows}
    assert len(sigs) == len(rows)


def test_collision_degree_and_contamination_bound(quarter_zip):
    rows = build_quarter(quarter_zip, ExclusionCounts())
    idx = build_index(rows)
    smith = next(r for r in rows if r.person_cik == "1000001")
    # three distinct CIKs file under the same normalized name
    assert idx.degree(smith.person_name_norm) == 3
    assert idx.band_of(smith.person_name_norm) == "low"

    b = idx.contamination_bound()
    assert b["colliding_names"] == 1
    # 1000001 and 1000009 share issuer 320193 -> one suspect pair
    assert b["suspect_pairs"] == 1
    assert b["suspect_names"] == 1


def test_name_hash_is_salted_and_stable(quarter_zip):
    rows = build_quarter(quarter_zip, ExclusionCounts())
    r = rows[0]
    assert r.name_hash("salt-a") != r.name_hash("salt-b")
    assert r.name_hash("salt-a") == r.name_hash("salt-a")
    assert r.person_name_raw not in r.name_hash("salt-a")
