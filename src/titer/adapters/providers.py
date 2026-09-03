"""Concrete arms: Ploid, Exa, and the free web floor.

Transport is injected. Nothing here opens a socket by itself, so the whole
adapter layer is testable with no keys, no network and no spend - and the
scoring path is identical whether the bytes came from a vendor or a fixture.

Prices are list prices recorded in docs/HANDOFF.md with their source and date.
They are used only to *predict* affordability; what a call actually cost is
whatever the adapter reports back, and that is what the ledger charges.

Operational constraint from docs/DECISIONS.md D019: the Exa adapter targets the
self-serve API only. Signing an Exa Order Form or MSA retroactively acquires
MSA 2.4(j)'s prohibition on publishing benchmark analysis.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from typing import Any, Callable, Protocol

from titer.adapters.base import Call, RawAnswer, Spend

Transport = Callable[[str, str, dict], dict]  # (method, url, payload) -> json


class NotConfigured(RuntimeError):
    """Raised when an adapter is used without credentials, rather than
    returning an empty result that would score as a MISS and quietly become a
    finding about the provider."""


@dataclass
class Ploid:
    """Ploid /v1/search and /v1/person.

    Pricing (live page, 2026-09-02): pay-as-you-go $0.20/ACU; search $0.10 per
    10 matches; /v1/person 25 ACU = $5.00 PAYG. The "$2.50 face value" in
    Ploid's docs is the Business seat rate of $0.10/ACU.
    """

    transport: Transport | None = None
    api_key: str | None = None
    name: str = "ploid"

    # MEASURED 2026-09-03, not the list price. The pricing page says $0.10 per
    # 10 matches; a live search reports meta.credits_charged = 1, which at the
    # published $0.20/ACU is $0.20 - twice the list figure. Spend is read from
    # the response, so this constant only predicts affordability.
    SEARCH_USD = 0.20
    PERSON_ACU = 25
    ACU_USD = 0.20

    def actions(self) -> list[Call]:
        return [
            Call(self.name, "search_instant", self.SEARCH_USD),
            Call(self.name, "search_fast", self.SEARCH_USD),
            Call(self.name, "search_auto", self.SEARCH_USD),
            Call(self.name, "search_deep", self.SEARCH_USD),
            Call(self.name, "person_verify", self.PERSON_ACU * self.ACU_USD),
        ]

    @staticmethod
    def render(task) -> dict:
        """Structured request, not a string. See docs/RETRACTIONS.md R001.

        An earlier version packed the name and the employer into one free-text
        `query`. Ploid documents structured `filters` - title, seniority,
        company, industry, location - and a company does not belong in the free
        text. That defect produced a 0/21 result that measured our wire format
        rather than their index, and it cost the entire budget before it was
        found.

        The facts disclosed are unchanged: person name plus the anchor employer.
        The scored fact - the employer at the target date - is still withheld.
        """
        return {"query": _presented_name(task.person_name_raw),
                "filters": {"company": task.anchor_issuer_name}}

    def query(self, action: str, prompt, **kw) -> tuple[list[RawAnswer], Spend]:
        if self.transport is None:
            raise NotConfigured("ploid adapter has no transport configured")
        if action.startswith("search_"):
            rendered = prompt if isinstance(prompt, dict) else {"query": prompt}
            body = {"category": "people", "type": action.split("_", 1)[1],
                    "num_results": kw.get("num_results", 10), **rendered}
            data = self.transport("POST", "/v1/search", body)
            return self._parse_search(data), _ploid_spend(data, self.SEARCH_USD)
        if action == "person_verify":
            data = self.transport("POST", "/v1/person", {"person_id": kw["person_id"]})
            return self._parse_person(data), _ploid_spend(
                data, self.PERSON_ACU * self.ACU_USD)
        raise ValueError(f"unknown ploid action {action!r}")

    @staticmethod
    def _parse_search(data: dict) -> list[RawAnswer]:
        # Live shape (2026-09-03): {"data": {"results": [...]}, "meta": {...}}.
        # Reading `results` at the top level - as an earlier version did -
        # yields nothing and scores every Ploid answer as a MISS, which is a
        # fabricated finding about the provider rather than a measurement.
        results = ((data.get("data") or {}).get("results")
                   or data.get("results") or [])
        out = []
        for i, r in enumerate(results):
            p = r.get("person", {}) or {}
            # `person.title` is the LinkedIn HEADLINE, not a role title - it
            # carries marketing prose. It is passed through unaltered and
            # title_map/v1 classifies it; a headline that names no office
            # becomes UNKNOWN and fails the title atom. That is the honest
            # result for a tier that does not return a role, and inferring one
            # from the headline would put a judged step in the scoring path.
            out.append(RawAnswer(
                person_name=p.get("name") or _name_from_title(r.get("title")),
                employer_name=p.get("company") or p.get("company_name"),
                title_text=p.get("title"),
                confidence=float(r.get("score", 0.0) or 0.0),
                rank=i,
                resolution_source=p.get("resolution_source"),
                identity_verified=p.get("identity_verified"),
            ))
        return out

    @staticmethod
    def _parse_person(data: dict) -> list[RawAnswer]:
        p = data.get("person", {}) or {}
        return [RawAnswer(
            person_name=p.get("name"), employer_name=p.get("company"),
            title_text=p.get("title"), confidence=1.0 if p.get("identity_verified") else 0.5,
            resolution_source=p.get("resolution_source"),
            identity_verified=p.get("identity_verified"),
        )]


ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "person_name": {"type": "string"},
        "organisation": {"type": "string"},
        "role": {"type": "string"},
        "confidence": {"type": "number"},
    },
    "required": ["person_name", "organisation", "role", "confidence"],
}


@dataclass
class Exa:
    """Exa. SELF-SERVE ONLY - see docs/DECISIONS.md D019.

    Two actions, and the distinction matters for fairness:

    * `answer` - POST /answer with an `outputSchema`, which returns structured
      JSON plus a self-reported confidence. This is the people-research arm.
    * `search` - POST /search returns only `id`, `title`, `url`. It is a WEB
      SEARCH, not a people index. Scoring it against Ploid's people index would
      manufacture a finding about Exa, so it is used as the free web floor and
      labelled as such, never as Exa's people product.

    Spend is read from the response's own `costDollars.total`, not from a list
    price. `base.py` requires it: an estimated price makes the whole
    value-of-information claim circular.
    """

    transport: Transport | None = None
    api_key: str | None = None
    name: str = "exa"

    ANSWER_USD = 0.005    # observed 2026-09-03; the response reports the real figure
    SEARCH_USD = 0.007

    @staticmethod
    def render(task) -> str:
        """Exa /answer is an answer engine: it takes the question as written."""
        return task.prompt() + " Give your confidence as a number between 0 and 1."

    def actions(self) -> list[Call]:
        return [Call(self.name, "answer", self.ANSWER_USD),
                Call(self.name, "search", self.SEARCH_USD)]

    def query(self, action: str, prompt: str, **kw) -> tuple[list[RawAnswer], Spend]:
        if self.transport is None:
            raise NotConfigured("exa adapter has no transport configured")
        if action == "answer":
            data = self.transport("POST", "/answer",
                                  {"query": prompt, "outputSchema": ANSWER_SCHEMA})
            return self._parse_answer(data), _spend_from(data, self.ANSWER_USD)
        if action == "search":
            data = self.transport("POST", "/search",
                                  {"query": prompt, "numResults": kw.get("num_results", 10)})
            out = []
            for i, r in enumerate(data.get("results", [])):
                person, employer, role = _parse_page_title(r.get("title"))
                out.append(RawAnswer(person_name=person, employer_name=employer,
                                     title_text=role, confidence=0.0, rank=i))
            return out, _spend_from(data, self.SEARCH_USD)
        raise ValueError(f"unknown exa action {action!r}")

    @staticmethod
    def _parse_answer(data: dict) -> list[RawAnswer]:
        raw = data.get("answer")
        if isinstance(raw, str):
            try:
                raw = json.loads(raw)
            except (ValueError, TypeError):
                # Prose rather than JSON. Refuse to parse it with a model - that
                # would put a judged step in the measurement path. Treat it as
                # no structured answer and let it score as a MISS.
                return []
        if not isinstance(raw, dict):
            return []
        conf = raw.get("confidence")
        try:
            conf = min(max(float(conf), 0.0), 1.0)
        except (TypeError, ValueError):
            conf = 0.0
        return [RawAnswer(
            person_name=raw.get("person_name") or None,
            employer_name=raw.get("organisation") or None,
            title_text=raw.get("role") or None,
            confidence=conf, rank=0,
        )]


@dataclass
class WebFloor:
    """The trivial floor: free web search. D020.

    The arm that must be beaten. If a paid people index cannot beat free search
    on a person named in a public filing, that is the headline finding.
    """

    transport: Transport | None = None
    name: str = "webfloor"

    def actions(self) -> list[Call]:
        return [Call(self.name, "search", 0.0)]

    def query(self, action: str, prompt: str, **kw) -> tuple[list[RawAnswer], Spend]:
        if self.transport is None:
            raise NotConfigured("webfloor adapter has no transport configured")
        data = self.transport("GET", "/search", {"q": prompt})
        out = []
        for i, r in enumerate(data.get("results", [])):
            out.append(RawAnswer(
                person_name=r.get("name"), employer_name=r.get("company"),
                title_text=r.get("title"),
                confidence=float(r.get("score", 0.0) or 0.0), rank=i,
            ))
        return out, Spend(0.0, 0.0, "free")


_SITE_SUFFIX = re.compile(r"\s*[|\u2013-]\s*(LinkedIn|Bloomberg|Crunchbase|ZoomInfo)\s*$", re.I)


def _ploid_spend(data: dict, fallback_usd: float) -> Spend:
    """Ploid reports the real charge in `meta.credits_charged`, and it is 0 when
    a search returns nothing. Reading it means an empty result is correctly
    free, rather than being billed at a list price we invented."""
    meta = (data or {}).get("meta") or {}
    credits = meta.get("credits_charged")
    if isinstance(credits, (int, float)):
        return Spend(float(credits) * Ploid.ACU_USD, float(credits), "acu_reported")
    return Spend(fallback_usd, 0.0, "usd_listprice_estimate")


def _presented_name(raw: str | None) -> str:
    """SEC files "REYES GEORGE"; a people index expects "George Reyes"."""
    from titer.corpus.name_norm import normalize_presented
    return " ".join(w.capitalize() for w in normalize_presented(raw).split())


def _name_from_title(title: str | None) -> str | None:
    """Ploid search results carry no `person.name`; the person's name leads the
    result `title` ("Geoff Bailey, Chief Executive Officer at Turmec")."""
    if not title:
        return None
    head = re.split(r"\s*[,|\u00a6]\s*|\s+-\s+", title.strip())[0]
    return head or None


def _spend_from(data: dict, fallback_usd: float) -> Spend:
    """Read the provider's own reported cost. Falls back to the list price only
    when the response carries none, and flags that in the unit name so a
    fabricated figure is never mistaken for a measured one."""
    cost = (data or {}).get("costDollars") or {}
    total = cost.get("total")
    if isinstance(total, (int, float)):
        return Spend(float(total), 1.0, "usd_reported")
    return Spend(fallback_usd, 1.0, "usd_listprice_estimate")


def _parse_page_title(title: str | None) -> tuple[str | None, str | None, str | None]:
    """Best-effort split of a web-page title into (person, employer, role).

    Deliberately conservative: anything that does not match the common
    "Name - Role - Company" shape yields the raw string as the name and None
    for the rest, so a parse failure degrades to a miss rather than to an
    invented employer.
    """
    if not title:
        return None, None, None
    cleaned = _SITE_SUFFIX.sub("", title).strip()
    parts = [s.strip() for s in cleaned.split(" - ") if s.strip()]
    if len(parts) >= 3:
        return parts[0], parts[2], parts[1]
    if len(parts) == 2:
        return parts[0], None, parts[1]
    return cleaned or None, None, None


def timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000.0
