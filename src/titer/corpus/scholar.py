"""OpenAlex / ORCID corpus: attested expertise, and constructible non-expertise.

The scholarly population is stronger than the employment one in exactly one way,
and it is the way that matters: **a false claim can be constructed rather than
judged.** A person's attested topics come from their authored works, so a false
expertise claim is a topic with zero attested works - drawn mechanically from an
adjacent field, never hand-picked, never absurd.

Attestation chain: OpenAlex work-to-author linkage, backed by Crossref DOIs,
with ORCID as the identity spine. A researcher cannot self-assert a DOI into
existence, which is why CONTRACTS A1 promotes this above ORCID's self-reported
affiliations (reversing D003 only for expertise).

No model participates anywhere in this module. Adjacency is a set operation over
the OpenAlex topic hierarchy, versioned as `topic_adjacency/v1`.
"""
from __future__ import annotations

import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Iterator

API = "https://api.openalex.org"
ADJACENCY_VERSION = "topic_adjacency/v1"

#: A human's plausible publication range. The lower bound keeps the ATTESTED
#: side from being dominated by people with one paper; the upper bound excludes
#: OpenAlex author records that have merged many humans - "T. Kobayashi" with
#: 2.4M works and 42 affiliations is a real record. Measured on a random sample
#: of 200 ORCID authors above the lower bound: median 49, p90 184, max 737, and
#: zero records above 2000. The band retains ~3.66M ORCID authors.
MIN_WORKS_TOTAL, MAX_WORKS_TOTAL = 20, 500

#: Attested works in a topic before the claim counts. CONTRACTS A4.
MIN_WORKS_IN_TOPIC = 3

MIN_INTERVAL_S = 0.15   # OpenAlex polite pool: 10/s, 100k/day


class OpenAlexError(RuntimeError):
    pass


def user_agent(mailto: str) -> str:
    """OpenAlex's polite pool wants a contact address. Read from the caller so
    no address is committed - the privacy gate rejects email-shaped strings in
    tracked files."""
    if not mailto:
        raise OpenAlexError(
            "No contact address. OpenAlex's polite pool needs one; set "
            "TITER_OPENALEX_MAILTO. Anonymous use gets the slow shared pool."
        )
    return f"titer-research (mailto:{mailto})"


_last = 0.0


def _auth_headers() -> dict[str, str]:
    """OpenAlex premium key, as a header rather than an `api_key` query param.

    Both are accepted. The header is used because a query param would land in
    log lines, error messages and cache keys - `CacheKey` hashes the request
    string - and a credential does not belong in any of those.
    """
    import os
    key = os.environ.get("OPENALEX_API_KEY", "").strip()
    return {"Authorization": f"Bearer {key}"} if key else {}


def _get(url: str, ua: str, timeout: int = 60) -> dict:
    global _last
    wait = MIN_INTERVAL_S - (time.monotonic() - _last)
    if wait > 0:
        time.sleep(wait)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": ua,
                                                   "Accept": "application/json",
                                                   **_auth_headers()})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read()[:200]
        if e.code == 429 and b"Insufficient budget" in body:
            raise OpenAlexError(
                "OpenAlex daily budget exhausted. It resets at midnight UTC. "
                "Set OPENALEX_API_KEY for a premium key, which lifts the cap. "
                "Do NOT loop - each retry burns budget you do not have."
            ) from e
        raise OpenAlexError(f"OpenAlex {e.code} for {url}: {body!r}") from e
    finally:
        _last = time.monotonic()


# --------------------------------------------------------------------------
# Topic hierarchy
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class Topic:
    id: str
    display_name: str
    subfield: str
    field: str
    domain: str


def fetch_topics(ua: str) -> dict[str, Topic]:
    """The full OpenAlex topic hierarchy, ~4.5k topics over ~23 requests."""
    out: dict[str, Topic] = {}
    cursor = "*"
    while cursor:
        d = _get(f"{API}/topics?per-page=200&cursor={urllib.parse.quote(cursor)}", ua)
        for t in d["results"]:
            out[t["id"]] = Topic(
                id=t["id"], display_name=t["display_name"],
                subfield=(t.get("subfield") or {}).get("display_name", ""),
                field=(t.get("field") or {}).get("display_name", ""),
                domain=(t.get("domain") or {}).get("display_name", ""),
            )
        cursor = d["meta"].get("next_cursor")
        if not d["results"]:
            break
    return out


# --------------------------------------------------------------------------
# Authors
# --------------------------------------------------------------------------

@dataclass(frozen=True, slots=True)
class AttestedTopic:
    topic_id: str
    label: str
    n_works: int
    subfield: str
    field: str
    domain: str


@dataclass(frozen=True, slots=True)
class Author:
    author_id: str
    orcid: str
    display_name: str
    works_count: int
    institution: str
    attested: tuple[AttestedTopic, ...]

    @property
    def domains(self) -> set[str]:
        return {t.domain for t in self.attested if t.domain}

    @property
    def fields(self) -> set[str]:
        return {t.field for t in self.attested if t.field}

    @property
    def topic_ids(self) -> set[str]:
        return {t.topic_id for t in self.attested}


@dataclass
class ScholarCounts:
    """Every rule that drops an author increments a counter. Same contract as
    the employment corpus: a row cannot leave silently."""

    seen: int = 0
    kept: int = 0
    no_orcid: int = 0
    works_out_of_band: int = 0
    no_attested_topic: int = 0
    no_institution: int = 0
    detail: dict = field(default_factory=dict)

    @property
    def dropped(self) -> int:
        return (self.no_orcid + self.works_out_of_band
                + self.no_attested_topic + self.no_institution)

    def reconcile(self) -> None:
        if self.kept + self.dropped != self.seen:
            raise AssertionError(
                f"counters do not reconcile: kept={self.kept} + dropped={self.dropped}"
                f" != seen={self.seen}. An author was dropped without being counted, "
                "which is an unpublished coverage gap."
            )

    def as_dict(self) -> dict[str, int]:
        d = {k: v for k, v in self.__dict__.items() if isinstance(v, int)}
        d["dropped"] = self.dropped
        return d


def parse_author(a: dict, counts: ScholarCounts) -> Author | None:
    counts.seen += 1
    orcid = (a.get("orcid") or "").strip()
    if not orcid:
        counts.no_orcid += 1
        return None
    wc = a.get("works_count") or 0
    if not (MIN_WORKS_TOTAL <= wc <= MAX_WORKS_TOTAL):
        counts.works_out_of_band += 1
        return None

    attested = tuple(
        AttestedTopic(
            topic_id=t["id"], label=t["display_name"], n_works=t.get("count", 0),
            subfield=(t.get("subfield") or {}).get("display_name", ""),
            field=(t.get("field") or {}).get("display_name", ""),
            domain=(t.get("domain") or {}).get("display_name", ""),
        )
        for t in (a.get("topics") or []) if t.get("count", 0) >= MIN_WORKS_IN_TOPIC
    )
    if not attested:
        counts.no_attested_topic += 1
        return None

    insts = a.get("last_known_institutions") or []
    inst = (insts[0].get("display_name") if insts else "") or ""
    if not inst:
        counts.no_institution += 1
        return None

    counts.kept += 1
    return Author(author_id=a["id"], orcid=orcid, display_name=a["display_name"],
                  works_count=wc, institution=inst, attested=attested)


def iter_authors(ua: str, counts: ScholarCounts, target: int,
                 per_page: int = 200) -> Iterator[Author]:
    """Page through the sane band. Cursor paging, not offset - OpenAlex caps
    deep offset paging and would silently truncate."""
    cursor = "*"
    filt = (f"has_orcid:true,works_count:{MIN_WORKS_TOTAL}-{MAX_WORKS_TOTAL}")
    yielded = 0
    while cursor and yielded < target:
        d = _get(f"{API}/authors?per-page={per_page}&filter={filt}"
                 f"&cursor={urllib.parse.quote(cursor)}", ua)
        if not d["results"]:
            return
        for raw in d["results"]:
            got = parse_author(raw, counts)
            if got is not None:
                yield got
                yielded += 1
                if yielded >= target:
                    return
        cursor = d["meta"].get("next_cursor")


# --------------------------------------------------------------------------
# topic_adjacency/v1 - the constructed-false claim
# --------------------------------------------------------------------------

#: Negative difficulty. Measured, not assumed - see docs/DECISIONS.md D031.
#: "Same domain, different field" alone produced negatives ranging from genuinely
#: hard (a dermatologist asked about dental education) to trivially rejectable
#: (a diabetes researcher asked about Hemiptera insect studies; an organometallic
#: chemist asked about approximation theory), because a domain like Physical
#: Sciences spans chemistry to pure mathematics. A benchmark built only on the
#: easy ones would report a false-affirmation rate near zero that means nothing.
NEAR, FAR, FAR_DOMAIN = "near", "far", "far_domain"


# Catch-all topic labels. OpenAlex carries a handful of unfalsifiable buckets
# ("Diverse Scientific Research Studies") that almost any researcher could be
# argued into. They appeared among the first false claims a provider affirmed,
# and a negative nobody can be wrong about measures nothing.
_CATCHALL = ("diverse", "various", "miscellaneous", "interdisciplinary studies",
             "research studies", "scientific studies", "and applications")


def is_catchall(label: str) -> bool:
    low = label.lower()
    return any(tok in low for tok in _CATCHALL)


def has_works_in_topic(author_id: str, topic_id: str, ua: str) -> int:
    """Authoritative count of an author's works in a topic.

    **This is the check the first corpus was missing, and it voided a whole
    study.** An author object's `topics` field is a TOP-N SUMMARY - median 5
    topics for authors with ~120 works - not an exhaustive record. Treating
    "absent from the top-5 list" as "never published in" made 13.3% of the
    constructed-false claims actually true, and that contamination was the same
    size as the effect being measured.

    `/works` filtered by author and topic is exhaustive. It is free, and one
    call per candidate negative is the entire cost of not repeating this.
    """
    aid = author_id.rsplit("/", 1)[-1]
    tid = topic_id.rsplit("/", 1)[-1]
    d = _get(f"{API}/works?filter=authorships.author.id:{aid},topics.id:{tid}"
             f"&per-page=1", ua)
    return d["meta"]["count"]


def adjacent_false_topic(author: Author, topics: dict[str, Topic],
                         rng: random.Random, difficulty: str = NEAR,
                         verify=None, max_verify: int = 8
                         ) -> tuple[Topic, str] | None:
    """A topic the author has provably never published in. CONTRACTS A3, D031.

    Two mechanical tiers, both reported separately and never pooled:

    * ``NEAR`` - **same field, different subfield.** An immunologist asked about
      a different immunology subfield. Hard, and the one that carries the signal.
    * ``FAR``  - **same domain, different field.** Plausible but easier.
    * ``FAR_DOMAIN`` - **a wholly different domain.** A chemist asked about
      medieval poetry. This is a **CONTROL, not a difficulty tier**: it should be
      rejected close to 100%. NEAR and FAR failed to separate (D031 falsified),
      which leaves two readings - the tiers were too close together, or topic
      distance does not affect the rate at all. Only a tier that is obviously
      absurd distinguishes them. If it is affirmed at the same ~15% as the
      others, the provider affirms almost anything at a fixed rate independent
      of distance, which is a stronger finding than a gradient.

    Both require zero attested works in the topic. No model participates; this
    is a set operation over the OpenAlex hierarchy.

    `verify` is a callable ``(author_id, topic_id) -> int`` returning the
    author's true work count in that topic. **Pass it.** Without it the negative
    means only "absent from the author's top-N topic summary", which is a
    different and much weaker claim - it made 13.3% of the first corpus's
    negatives actually true, at the same magnitude as the effect measured.
    """
    if not author.attested:
        return None
    subfields = {t.subfield for t in author.attested if t.subfield}

    def pool_for(tier: str) -> list[Topic]:
        if tier == NEAR:
            return [t for t in topics.values()
                    if t.field in author.fields
                    and t.subfield not in subfields
                    and t.id not in author.topic_ids]
        if tier == FAR_DOMAIN:
            return [t for t in topics.values()
                    if t.domain not in author.domains
                    and t.id not in author.topic_ids]
        return [t for t in topics.values()
                if t.domain in author.domains
                and t.field not in author.fields
                and t.id not in author.topic_ids]

    order = {NEAR: [NEAR, FAR], FAR: [FAR, NEAR],
             FAR_DOMAIN: [FAR_DOMAIN]}[difficulty]
    for tier in order:
        pool = [t for t in pool_for(tier) if not is_catchall(t.display_name)]
        if not pool:
            continue
        # Sorted before choice so the corpus rebuilds identically from the seed
        # alone, without storing which topic was picked.
        ordered = sorted(pool, key=lambda t: t.id)
        rng.shuffle(ordered)
        if verify is None:
            return ordered[0], tier
        # Verify against /works until one is genuinely false. Without this the
        # negative is only "absent from a top-N summary", which is not the same
        # thing and cost an entire study.
        for cand in ordered[:max_verify]:
            if verify(author.author_id, cand.id) == 0:
                return cand, tier
    return None
