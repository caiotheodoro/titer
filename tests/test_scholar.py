"""The expertise corpus, and the construction of its negatives.

The negative control is the reason this population is stronger than the
employment one, so it gets the most adversarial tests in the suite.
"""
import random

import pytest

from titer.corpus.scholar import (FAR, MAX_WORKS_TOTAL, MIN_WORKS_IN_TOPIC,
                                  MIN_WORKS_TOTAL, NEAR, AttestedTopic, Author,
                                  ScholarCounts, Topic, adjacent_false_topic,
                                  parse_author, user_agent)


def _t(tid, label, sub, field, dom):
    return Topic(tid, label, sub, field, dom)


@pytest.fixture
def topics():
    return {t.id: t for t in [
        _t("T1", "Immunotherapy", "Immunology", "Immunology and Microbiology", "Life"),
        _t("T2", "Vaccine design", "Immunology", "Immunology and Microbiology", "Life"),
        _t("T3", "Microbial ecology", "Microbiology", "Immunology and Microbiology", "Life"),
        _t("T4", "Hemiptera insects", "Ecology", "Agricultural Sciences", "Life"),
        _t("T5", "Approximation theory", "Analysis", "Mathematics", "Physical"),
    ]}


@pytest.fixture
def immunologist():
    return Author("A1", "0000-0001", "Jane Roe", 120, "Univ", (
        AttestedTopic("T1", "Immunotherapy", 40, "Immunology",
                      "Immunology and Microbiology", "Life"),))


# --- the negative construction ---

def test_near_is_same_field_different_subfield(topics, immunologist):
    """The hard tier, and the one that carries the signal."""
    topic, tier = adjacent_false_topic(immunologist, topics, random.Random(11), NEAR)
    assert tier == NEAR
    assert topic.field == "Immunology and Microbiology"    # same field
    assert topic.subfield != "Immunology"                  # different subfield
    assert topic.id == "T3"


def test_far_is_same_domain_different_field(topics, immunologist):
    topic, tier = adjacent_false_topic(immunologist, topics, random.Random(11), FAR)
    assert tier == FAR
    assert topic.domain == "Life" and topic.field != "Immunology and Microbiology"


def test_a_false_topic_is_never_one_the_author_publishes_in(topics, immunologist):
    """The whole construction rests on this. If it can pick an attested topic,
    the 'false' claim is true and the benchmark is inverted."""
    for tier in (NEAR, FAR):
        for seed in range(30):
            got = adjacent_false_topic(immunologist, topics, random.Random(seed), tier)
            if got:
                assert got[0].id not in immunologist.topic_ids


def test_same_subfield_is_never_offered_as_false_at_near(topics, immunologist):
    """T2 shares the author's subfield. Calling it 'not their expertise' would
    be a near-synonym of what they do, and arguably untrue."""
    for seed in range(30):
        got = adjacent_false_topic(immunologist, topics, random.Random(seed), NEAR)
        assert got is None or got[0].id != "T2"


def test_construction_is_deterministic_under_a_seed(topics, immunologist):
    """The corpus must rebuild identically without storing which topic was
    chosen; otherwise the negatives are unreproducible."""
    a = adjacent_false_topic(immunologist, topics, random.Random(7), NEAR)
    b = adjacent_false_topic(immunologist, topics, random.Random(7), NEAR)
    assert a[0].id == b[0].id


def test_falls_back_to_the_other_tier_rather_than_returning_nothing(immunologist):
    """An author with no same-field alternative must still get a negative, and
    the tier it came from must be reported so it is never silently pooled."""
    only_far = {"T9": _t("T9", "Hemiptera", "Ecology", "Agricultural Sciences", "Life")}
    got = adjacent_false_topic(immunologist, only_far, random.Random(1), NEAR)
    assert got is not None and got[1] == FAR


def test_no_topics_at_all_returns_none_rather_than_guessing(immunologist):
    assert adjacent_false_topic(immunologist, {}, random.Random(1), NEAR) is None


def test_author_with_no_attested_topics_gets_no_negative(topics):
    empty = Author("A2", "0000-0002", "No Topics", 50, "Univ", ())
    assert adjacent_false_topic(empty, topics, random.Random(1), NEAR) is None


def test_no_model_is_reachable_from_the_construction():
    """CONTRACTS A3: adjacency is a set operation, never a judgement."""
    import titer.corpus.scholar as m
    src = open(m.__file__).read()
    for banned in ("openai", "anthropic", "transformers", "torch", "llm"):
        assert banned not in src.lower()


# --- inclusion rules ---

def _raw(**kw):
    base = {"id": "A1", "orcid": "https://orcid.org/0000-0001",
            "display_name": "Jane Roe", "works_count": 100,
            "last_known_institutions": [{"display_name": "Univ"}],
            "topics": [{"id": "T1", "display_name": "Immunotherapy", "count": 10,
                        "subfield": {"display_name": "Immunology"},
                        "field": {"display_name": "Immunology and Microbiology"},
                        "domain": {"display_name": "Life"}}]}
    base.update(kw)
    return base


def test_counters_reconcile_and_every_rule_fires():
    c = ScholarCounts()
    assert parse_author(_raw(), c) is not None
    assert parse_author(_raw(orcid=""), c) is None
    assert parse_author(_raw(works_count=MAX_WORKS_TOTAL + 1), c) is None
    assert parse_author(_raw(works_count=MIN_WORKS_TOTAL - 1), c) is None
    assert parse_author(_raw(topics=[]), c) is None
    assert parse_author(_raw(last_known_institutions=[]), c) is None
    c.reconcile()
    assert c.seen == 6 and c.kept == 1
    assert c.no_orcid == 1 and c.works_out_of_band == 2
    assert c.no_attested_topic == 1 and c.no_institution == 1


def test_merged_author_records_are_excluded():
    """OpenAlex has author records that merge many humans - one real example
    carries 2.4M works across 42 affiliations. A measured sample of 200 ORCID
    authors in band had max 737, so the upper bound excludes merges without
    excluding prolific people."""
    c = ScholarCounts()
    assert parse_author(_raw(works_count=2_429_357), c) is None
    assert c.works_out_of_band == 1


def test_a_topic_below_the_threshold_is_not_attested():
    """CONTRACTS A4: one paper in a topic is a dabble, not expertise."""
    c = ScholarCounts()
    thin = _raw(topics=[{**_raw()["topics"][0], "count": MIN_WORKS_IN_TOPIC - 1}])
    assert parse_author(thin, c) is None and c.no_attested_topic == 1


def test_contact_address_is_required_and_not_committed():
    with pytest.raises(Exception):
        user_agent("")
    assert "mailto:x@y.z" in user_agent("x@y.z")


# --- the check whose absence voided a whole study (R002) ---

def test_verify_is_used_and_a_contaminated_candidate_is_rejected(topics, immunologist):
    """An author's `topics` field is a TOP-N SUMMARY, not an exhaustive record.
    Treating 'absent from the top-5' as 'never published in' made 13.3% of the
    first corpus's negatives actually true - the same size as the effect being
    measured. `verify` hits /works, which is exhaustive."""
    seen = []

    def verify(author_id, topic_id):
        seen.append(topic_id)
        return 5 if topic_id == "T3" else 0      # T3 is contaminated

    got = adjacent_false_topic(immunologist, topics, random.Random(11), NEAR,
                               verify=verify)
    assert seen, "verify was never called"
    assert got is None or got[0].id != "T3"


def test_no_clean_candidate_returns_none_rather_than_a_contaminated_one(topics,
                                                                       immunologist):
    """If every candidate is contaminated the author yields NO task. Falling
    back to a contaminated negative is what produced the void result."""
    got = adjacent_false_topic(immunologist, topics, random.Random(11), NEAR,
                               verify=lambda a, t: 3)
    assert got is None


def test_catchall_topics_are_excluded(immunologist):
    """OpenAlex carries unfalsifiable buckets. 'Diverse Scientific Research
    Studies' was among the first false claims a provider affirmed, and a
    negative nobody can be wrong about measures nothing."""
    from titer.corpus.scholar import is_catchall
    assert is_catchall("Diverse Historical and Scientific Studies")
    assert is_catchall("Diverse Scientific Research Studies")
    assert not is_catchall("Cutaneous Melanoma Detection and Management")

    junk = {"T9": _t("T9", "Diverse Scientific Research Studies", "Other",
                     "Immunology and Microbiology", "Life")}
    assert adjacent_false_topic(immunologist, junk, random.Random(1), NEAR,
                                verify=lambda a, t: 0) is None


def test_unverified_construction_is_still_possible_but_must_be_explicit():
    """verify=None is the old behaviour. It stays available for offline tests,
    and the docstring says plainly what it costs."""
    import inspect

    from titer.corpus import scholar
    src = inspect.getsource(scholar.adjacent_false_topic)
    assert "verify" in src and "top-n" in src.lower()


def test_far_domain_is_a_wholly_different_domain(topics, immunologist):
    """The CONTROL tier. NEAR and FAR did not separate, which leaves two
    readings: the tiers were too close, or topic distance does not matter at
    all. Only an obviously absurd negative distinguishes them."""
    from titer.corpus.scholar import FAR_DOMAIN
    got = adjacent_false_topic(immunologist, topics, random.Random(11), FAR_DOMAIN,
                               verify=lambda a, t: 0)
    assert got is not None
    topic, tier = got
    assert tier == FAR_DOMAIN
    assert topic.domain not in immunologist.domains
    assert topic.id == "T5"          # Mathematics / Physical, the only one


def test_far_domain_does_not_silently_fall_back(immunologist):
    """A control that quietly degrades into an adjacent tier measures the wrong
    thing and would look like a result."""
    from titer.corpus.scholar import FAR_DOMAIN
    same_domain_only = {"T7": _t("T7", "Microbial ecology", "Microbiology",
                                 "Immunology and Microbiology", "Life")}
    assert adjacent_false_topic(immunologist, same_domain_only, random.Random(1),
                                FAR_DOMAIN, verify=lambda a, t: 0) is None


def test_exhausted_premium_key_falls_back_to_the_polite_pool():
    """An exhausted OpenAlex key must not disable free verification. D037 C6.

    `_auth_headers()` attaches the key unconditionally, so an invalid or
    revoked key stops every OpenAlex call - including `has_works_in_topic`, the
    exhaustive check that exists because skipping it voided a whole study
    (R002). One unauthenticated retry covers that case.

    It does NOT cover an exhausted account: measured 2026-09-04, authenticated
    and unauthenticated requests bill the same budget, and once it read
    "$0 remaining" both paths 429ed until midnight UTC.
    """
    import titer.corpus.scholar as sch
    src = open(sch.__file__).read()
    body = src[src.index("def _get("):src.index("def fetch_topics")]
    assert "Insufficient budget" in body
    assert "_auth_headers()" in body.split("Insufficient budget")[1], (
        "the 429 branch must check for a key and retry once unauthenticated")


class TestInstitutionResolver:
    """D038's blocker: a string match cannot see institutional hierarchy.

    Truth `Manipal Academy of Higher Education` against a returned `Kasturba
    Medical College, Manipal University` scored WRONG, and the college is
    inside the academy. OpenAlex publishes `lineage`, an explicit ancestor
    list, so containment becomes set membership rather than a judgement.
    """

    def test_resolver_tries_comma_clauses_not_just_the_whole_string(self):
        import titer.corpus.scholar as sch
        src = open(sch.__file__).read()
        body = src[src.index("def resolve_institution"):src.index("def same_institution")]
        assert 'split(",")' in body, (
            "recall matters as much as precision: an unresolvable name scores "
            "wrong, so a weak resolver measures itself")

    def test_containment_is_checked_in_both_directions(self):
        import titer.corpus.scholar as sch
        src = open(sch.__file__).read()
        body = src[src.index("def same_institution"):]
        body = body[:body.index("\ndef ")]
        assert "tid in rlin" in body and "rid in tlin" in body

    def test_same_institution_needs_both_sides_resolved(self):
        """An unresolved name must be False, never a silent True."""
        from titer.corpus.scholar import same_institution
        assert same_institution(None, "University of Bern", "ua") is False
        assert same_institution("", "University of Bern", "ua") is False
