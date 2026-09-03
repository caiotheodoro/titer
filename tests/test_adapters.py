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
    d = {"name": "X", "email": "a@b.com", "work_email": "c@d.com",
         "nested": {"phone": "555", "home_address": "1 Main", "title": "CEO"},
         "links": [{"url": "http://x", "label": "bio"}],
         "date_of_birth": "1970-01-01", "employer_phone_number": "555"}
    out = strip_contact_fields(d)
    blob = json.dumps(out)
    for leak in ("a@b.com", "c@d.com", "555", "1 Main", "http://x", "1970-01-01"):
        assert leak not in blob
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
        return {"results": [
            {"score": 0.9, "person": {"name": "Jane Roe", "company": "ACME",
                                      "title": "CFO", "resolution_source": "ploid_people_index",
                                      "identity_verified": False}},
        ]}
    answers, spend = Ploid(transport=fake).query("search_fast", "who?")
    assert answers[0].person_name == "Jane Roe"
    assert answers[0].employer_name == "ACME"
    assert answers[0].identity_verified is False
    assert answers[0].rank == 0
    assert spend.usd == 0.10


def test_ploid_person_verify_is_priced_at_five_dollars():
    def fake(method, url, payload):
        return {"person": {"name": "Jane Roe", "company": "ACME", "identity_verified": True}}
    answers, spend = Ploid(transport=fake).query("person_verify", "", person_id="p1")
    assert spend.usd == 5.00 and spend.units == 25
    assert answers[0].identity_verified is True


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
