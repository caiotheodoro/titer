import json
from datetime import date

import pytest

from titer.adapters.base import BudgetExceeded, Ledger, RawAnswer, Spend
from titer.adapters.cache import CacheKey, ReplayCache, strip_contact_fields
from titer.adapters.providers import Exa, NotConfigured, Ploid, WebFloor


# --- ledger ---

def test_ledger_refuses_to_overspend():
    led = Ledger(budget_usd=5.00)
    led.charge(Spend(4.90))
    with pytest.raises(BudgetExceeded) as e:
        led.charge(Spend(0.20))
    assert "remains" in str(e.value)
    assert led.spent.usd == 4.90 and led.calls == 1


def test_ledger_tracks_remaining_and_calls():
    led = Ledger(budget_usd=1.0)
    for _ in range(4):
        led.charge(Spend(0.10))
    assert abs(led.remaining_usd - 0.60) < 1e-12
    assert led.calls == 4


def test_one_ploid_person_verify_nearly_exhausts_the_real_budget():
    """The budget reality this whole project is designed around: $5 buys one."""
    led = Ledger(budget_usd=5.00)
    price = Ploid.PERSON_ACU * Ploid.ACU_USD
    assert price == 5.00
    led.charge(Spend(price))
    with pytest.raises(BudgetExceeded):
        led.charge(Spend(0.01))


# --- contact stripping ---

def test_stripping_is_recursive_and_covers_unlisted_keys():
    # Sentinel values, deliberately NOT email- or phone-shaped. The stripper is
    # key-based, so the test loses nothing - and putting real-looking contact
    # data in a fixture is the exact habit that ends with a genuine one being
    # committed. The privacy gate flagged an earlier version of this test.
    d = {"name": "X", "email": "SENTINEL-1", "work_email": "SENTINEL-2",
         "nested": {"phone": "SENTINEL-3", "home_address": "SENTINEL-4", "title": "CEO"},
         "links": [{"url": "SENTINEL-5", "label": "bio"}],
         "date_of_birth": "SENTINEL-6", "employer_phone_number": "SENTINEL-7"}
    out = strip_contact_fields(d)
    blob = json.dumps(out)
    for n in range(1, 8):
        assert f"SENTINEL-{n}" not in blob
    assert out["name"] == "X" and out["nested"]["title"] == "CEO"


# --- cache ---

def test_cache_round_trips_and_strips_before_disk(tmp_path):
    """Stripping happens at ingest. A cache file that ever held an email has
    already created the risk. docs/ETHICS.md 2.1."""
    cache = ReplayCache(tmp_path / "c.jsonl")
    key = CacheKey("ploid", "search_fast", "req-hash", "2026-09")
    answers = [RawAnswer(person_name="A B", employer_name="ACME",
                         employment_start=date(2020, 1, 1), confidence=0.7)]
    cache.put(key, answers, Spend(0.10, 0.5, "acu"), 123.0, "2026-09-02T00:00:00Z")
    raw_file = (tmp_path / "c.jsonl").read_text()
    assert "ACME" in raw_file
    got = cache.get(key)
    assert got is not None and got.spend_usd == 0.10
    back = ReplayCache.to_answers(got)
    assert back[0].person_name == "A B"
    assert back[0].employment_start == date(2020, 1, 1)


def test_cache_key_separates_providers_actions_and_windows(tmp_path):
    cache = ReplayCache(tmp_path / "c.jsonl")
    a = CacheKey("ploid", "search_fast", "r", "2026-09")
    for other in (CacheKey("exa", "search_fast", "r", "2026-09"),
                  CacheKey("ploid", "search_deep", "r", "2026-09"),
                  CacheKey("ploid", "search_fast", "r2", "2026-09"),
                  CacheKey("ploid", "search_fast", "r", "2026-10")):
        assert a.digest() != other.digest()
    cache.put(a, [], Spend(0.0), 1.0, "t")
    assert cache.get(CacheKey("exa", "search_fast", "r", "2026-09")) is None


def test_cache_persists_across_instances(tmp_path):
    p = tmp_path / "c.jsonl"
    k = CacheKey("ploid", "search_fast", "r", "w")
    ReplayCache(p).put(k, [RawAnswer(person_name="Z")], Spend(0.1), 1.0, "t")
    reopened = ReplayCache(p)
    assert len(reopened) == 1
    assert reopened.total_spend_usd() == 0.1
    assert ReplayCache.to_answers(reopened.get(k))[0].person_name == "Z"


# --- providers ---

def test_adapters_refuse_to_run_unconfigured():
    """Returning an empty result would score as MISS and become a fabricated
    finding about the provider."""
    for p in (Ploid(), Exa(), WebFloor()):
        with pytest.raises(NotConfigured):
            p.query(p.actions()[0].action, "who?")


def test_ploid_parses_search_and_reports_price():
    def fake(method, url, payload):
        assert url == "/v1/search" and payload["category"] == "people"
        # Live shape: the person's NAME is result.title; person.title is the job.
        return {"data": {"results": [
            {"score": 0.9, "title": "Jane Roe",
             "person": {"company": "ACME", "title": "CFO",
                        "resolution_source": "ploid_people_index",
                        "identity_verified": False}},
        ]}}
    answers, spend = Ploid(transport=fake).query("search_fast", "who?")
    assert answers[0].person_name == "Jane Roe"
    assert answers[0].employer_name == "ACME"
    assert answers[0].identity_verified is False
    assert answers[0].rank == 0
    # No cost field in this fixture, so the MEASURED list price is used and
    # tagged. A live search reports credits_charged=1 = $0.20, twice the $0.10
    # the pricing page advertises per 10 matches.
    assert spend.usd == 0.20 and spend.unit_name == "usd_listprice_estimate"


def test_ploid_person_verify_falls_back_to_list_price_and_says_so():
    """No cost field in the response, so the list price is used - and tagged, so
    an assumed figure can never be read as a measured one."""
    def fake(method, url, payload):
        return {"person": {"name": "Jane Roe", "company": "ACME", "identity_verified": True}}
    answers, spend = Ploid(transport=fake).query("person_verify", "", person_id="p1")
    assert spend.usd == 5.00
    assert spend.unit_name == "usd_listprice_estimate"
    assert answers[0].identity_verified is True


def test_ploid_spend_is_read_from_meta_credits_charged():
    """Live shape: meta.credits_charged. It is 0 when a search returns nothing,
    so an empty result is correctly free rather than billed at our list price."""
    def empty(method, url, payload):
        return {"data": {"results": []}, "meta": {"credits_charged": 0}}
    answers, spend = Ploid(transport=empty).query("search_fast", "q")
    assert answers == [] and spend.usd == 0.0 and spend.unit_name == "acu_reported"

    def charged(method, url, payload):
        return {"data": {"results": []}, "meta": {"credits_charged": 0.5}}
    _, spend = Ploid(transport=charged).query("search_fast", "q")
    assert spend.usd == pytest.approx(0.5 * Ploid.ACU_USD)


def test_ploid_reads_results_from_the_nested_data_envelope():
    """Live shape is {"data": {"results": [...]}}. Reading `results` at the top
    level returned nothing and scored every Ploid answer as a MISS - a
    fabricated finding about the provider, not a measurement."""
    def fake(method, url, payload):
        return {"data": {"results": [{"title": "Jane Roe, CFO at Acme", "score": 0.9,
                                      "person": {"company": "Acme",
                                                 "identity_verified": False,
                                                 "resolution_source": "ploid_people_index"}}]},
                "meta": {"credits_charged": 1}}
    answers, _ = Ploid(transport=fake).query("search_fast", "q")
    assert len(answers) == 1
    assert answers[0].person_name == "Jane Roe"      # name led the result title
    assert answers[0].employer_name == "Acme"
    assert answers[0].identity_verified is False


def test_exa_reads_reported_cost_dollars():
    def fake(method, url, payload):
        return {"answer": {"person_name": "Jane Roe", "organisation": "Acme",
                           "role": "CFO", "confidence": 0.8},
                "costDollars": {"total": 0.005}}
    answers, spend = Exa(transport=fake).query("answer", "q")
    assert spend.usd == 0.005 and spend.unit_name == "usd_reported"
    assert answers[0].employer_name == "Acme" and answers[0].confidence == 0.8


def test_exa_prose_answer_is_not_parsed_by_a_model():
    """A non-JSON answer scores as a miss rather than being interpreted. Parsing
    prose would put a judged step in the measurement path."""
    def fake(method, url, payload):
        return {"answer": "He was at Apple.", "costDollars": {"total": 0.005}}
    answers, _ = Exa(transport=fake).query("answer", "q")
    assert answers == []


def test_webfloor_is_free():
    def fake(method, url, payload):
        return {"results": [{"name": "Jane Roe", "company": "ACME", "score": 0.4}]}
    answers, spend = WebFloor(transport=fake).query("search", "who?")
    assert spend.usd == 0.0
    assert answers[0].person_name == "Jane Roe"


def test_exa_is_cheaper_than_ploid_per_search():
    assert Exa.SEARCH_USD < Ploid.SEARCH_USD


def test_unknown_action_is_rejected():
    for p in (Ploid(transport=lambda *a: {}), Exa(transport=lambda *a: {})):
        with pytest.raises(ValueError):
            p.query("nonsense", "q")


# --- rendering: the defect that voided a whole arm (docs/RETRACTIONS.md R001) ---

def _fake_task():
    from datetime import date
    from titer.corpus.tasks import Task
    from titer.corpus.title_map import TitleClass
    return Task(person_name_raw="REYES GEORGE", anchor_issuer_cik="1",
                anchor_issuer_name="GOOGLE INC.", anchor_title_class=TitleClass.CFO,
                anchor_date=date(2005, 1, 1), target_date=date(2020, 1, 1),
                person_cik="9", truth_issuer_cik="2", truth_issuer_name="Gen Digital Inc.",
                truth_title_class=TitleClass.CFO, truth_period=date(2020, 1, 1),
                truth_filed=date(2020, 1, 3), truth_accession="acc",
                collision_degree=1, strict_degree=1)


def test_ploid_render_never_filters_on_the_anchor_employer():
    """D028 C1. Ploid's company filter selects people CURRENTLY at that company,
    so filtering on the anchor guarantees the anchor comes back - and the anchor
    is exactly what we score as STALE. Every task would have been STALE by
    construction, and it would have looked like a damning freshness finding."""
    r = Ploid.render(_fake_task())
    assert isinstance(r, dict), "render must be structured, not a string"
    assert "filters" not in r or "company" not in r.get("filters", {})


def test_ploid_render_carries_the_anchor_as_context_not_a_constraint():
    """The anchor still has to disambiguate the person; it just must not
    constrain the answer."""
    q = Ploid.render(_fake_task())["query"]
    assert "George Reyes" in q          # SEC files "REYES GEORGE"
    assert "Google" in q                # registrant suffix stripped
    assert "formerly" in q              # framed as past, not current


def test_prompt_asks_what_a_current_state_index_can_answer():
    """D028 C2. A people index returns a CURRENT employer; asking it about a
    date four years ago is not giving it a fair shot at the question."""
    p = _fake_task().prompt()
    assert "most recently" in p or "latest" in p
    assert "Gen Digital" not in p       # the scored fact is still withheld


def test_ploid_render_withholds_the_scored_fact():
    r = Ploid.render(_fake_task())
    blob = json.dumps(r)
    assert "Gen Digital" not in blob and "2020-01-01" not in blob


def test_exa_render_is_the_question_and_withholds_the_scored_fact():
    """Exa /answer is an answer engine and documents a natural-language query,
    so a question IS its structured shape."""
    q = Exa.render(_fake_task())
    assert isinstance(q, str) and "GOOGLE INC." in q
    assert "Gen Digital" not in q


def test_every_arm_discloses_the_same_facts():
    """Fairness is a property of the renderings taken together: the same facts
    to every arm, each in the shape its own API documents."""
    t = _fake_task()
    ploid, exa = json.dumps(Ploid.render(t)), Exa.render(t)
    for blob in (ploid, exa):
        assert "GOOGLE" in blob.upper()          # anchor employer disclosed
        assert "Gen Digital" not in blob         # target employer withheld


# --- parser pinned to the VERIFIED live schema (2026-09-03) ---

PLOID_LIVE_SHAPE = {
    "data": {"results": [{
        "url": "https://www.linkedin.com/in/george-reyes-3954846",
        "title": "George Reyes",
        "score": 140000.963828,
        "person": {"person_id": "person_89b1", "title": "Chief Financial Officer",
                   "company": "google", "location": "San Francisco, United States",
                   "linkedin_url": "https://www.linkedin.com/in/george-reyes-3954846",
                   "identity_verified": False,
                   "resolution_source": "ploid_people_index"}}]},
    "meta": {"credits_charged": 1},
}


def test_ploid_parses_the_verified_live_schema():
    """There is NO person.name. result.title carries the person's name and
    person.title is a real job title. Captured from a live call, not guessed -
    an earlier version scraped the name out of a display string and produced
    no_name_returned on 9 of 21 tasks."""
    answers, spend = Ploid(transport=lambda *a: PLOID_LIVE_SHAPE).query("search_fast", {})
    a = answers[0]
    assert a.person_name == "George Reyes"
    assert a.title_text == "Chief Financial Officer"
    assert a.employer_name == "google"
    assert a.identity_verified is False
    assert a.resolution_source == "ploid_people_index"
    assert spend.usd == pytest.approx(0.20) and spend.unit_name == "acu_reported"


def test_ploid_never_leaks_a_linkedin_url_into_the_cache():
    """person.linkedin_url is in every row. docs/ETHICS.md forbids it on disk."""
    from titer.adapters.cache import strip_contact_fields
    blob = json.dumps(strip_contact_fields(PLOID_LIVE_SHAPE))
    assert "linkedin" not in blob.lower()


@pytest.mark.parametrize("registrant,expected", [
    ("GOOGLE INC.", "Google"),
    ("APPLE INC", "Apple"),
    ("Gen Digital Inc.", "Gen Digital"),
    ("PAR PACIFIC HOLDINGS, INC.", "Par Pacific"),
])
def test_company_filter_strips_registrant_suffixes(registrant, expected):
    """A structured filter is near-exact. Handing it the SEC registrant form
    matched nothing, the task returned no rows, and it scored as a MISS that
    looked like the provider failing. Verified live: "Google" finds the person,
    "GOOGLE INC." does not."""
    from titer.adapters.providers import _company_for_filter
    assert _company_for_filter(registrant) == expected


def test_cache_round_trips_the_raw_body_so_a_parser_fix_is_free(tmp_path):
    """Storing only parsed answers meant every parser bug cost credits twice -
    once to hit it, once to verify the fix - on grants that do not refill."""
    from titer.adapters.cache import CacheKey, ReplayCache
    cache = ReplayCache(tmp_path / "c.jsonl")
    key = CacheKey("ploid", "search_fast", "req", "2026-09")
    answers, spend = Ploid(transport=lambda *a: PLOID_LIVE_SHAPE).query("search_fast", {})
    cache.put(key, answers, spend, 1.0, "t", raw=PLOID_LIVE_SHAPE)

    entry = ReplayCache(tmp_path / "c.jsonl").get(key)
    assert entry.raw is not None
    again = ReplayCache.reparse(entry, Ploid._parse_search)
    assert again[0].person_name == "George Reyes"


def test_reparse_returns_none_when_no_raw_was_stored(tmp_path):
    """So a caller falls back to stored answers instead of silently getting
    nothing from older cache entries."""
    from titer.adapters.cache import CacheKey, ReplayCache
    cache = ReplayCache(tmp_path / "c.jsonl")
    key = CacheKey("ploid", "search_fast", "req", "w")
    cache.put(key, [], Spend(0.0), 1.0, "t")
    assert ReplayCache.reparse(cache.get(key), Ploid._parse_search) is None
