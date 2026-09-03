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

    SEARCH_USD = 0.10          # per call returning up to 10 matches
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

    def query(self, action: str, prompt: str, **kw) -> tuple[list[RawAnswer], Spend]:
        if self.transport is None:
            raise NotConfigured("ploid adapter has no transport configured")
        if action.startswith("search_"):
            body = {"query": prompt, "category": "people",
                    "type": action.split("_", 1)[1],
                    "num_results": kw.get("num_results", 10)}
            data = self.transport("POST", "/v1/search", body)
            return self._parse_search(data), Spend(self.SEARCH_USD, 0.5, "acu")
        if action == "person_verify":
            data = self.transport("POST", "/v1/person", {"person_id": kw["person_id"]})
            return self._parse_person(data), Spend(self.PERSON_ACU * self.ACU_USD,
                                                   self.PERSON_ACU, "acu")
        raise ValueError(f"unknown ploid action {action!r}")

    @staticmethod
    def _parse_search(data: dict) -> list[RawAnswer]:
        out = []
        for i, r in enumerate(data.get("results", [])):
            p = r.get("person", {}) or {}
            out.append(RawAnswer(
                person_name=p.get("name"),
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


@dataclass
class Exa:
    """Exa search. SELF-SERVE ONLY - see D019."""

    transport: Transport | None = None
    api_key: str | None = None
    name: str = "exa"

    SEARCH_USD = 0.007         # $7 per 1k requests, <=10 results

    def actions(self) -> list[Call]:
        return [Call(self.name, "search", self.SEARCH_USD)]

    def query(self, action: str, prompt: str, **kw) -> tuple[list[RawAnswer], Spend]:
        if self.transport is None:
            raise NotConfigured("exa adapter has no transport configured")
        if action != "search":
            raise ValueError(f"unknown exa action {action!r}")
        data = self.transport("POST", "/search",
                              {"query": prompt, "numResults": kw.get("num_results", 10)})
        out = []
        for i, r in enumerate(data.get("results", [])):
            out.append(RawAnswer(
                person_name=r.get("title"), employer_name=r.get("company"),
                title_text=r.get("role"), confidence=float(r.get("score", 0.0) or 0.0),
                rank=i,
            ))
        return out, Spend(self.SEARCH_USD, 1.0, "request")


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


def timed(fn: Callable[[], Any]) -> tuple[Any, float]:
    t0 = time.perf_counter()
    out = fn()
    return out, (time.perf_counter() - t0) * 1000.0
