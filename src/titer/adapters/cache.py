"""Record-replay cache. The unit of reproducibility.

Every measurement after W2 reads this cache rather than a live API, so the
published tables regenerate with no keys and no spend. A result that cannot be
regenerated from the cache is not a result.

Contact fields are removed **at ingest**, before anything touches disk. A cache
that ever held an email address has already created the risk that stripping at
publication time was supposed to prevent. See docs/ETHICS.md section 2.1.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from titer.adapters.base import CONTACT_KEYS, RawAnswer, Spend


def strip_contact_fields(obj: Any) -> Any:
    """Recursively drop anything that looks like a contact field.

    Key-based, and deliberately aggressive: a key we do not recognise but which
    contains 'email', 'phone' or 'address' is dropped too. Over-stripping costs
    us a signal; under-stripping publishes someone's phone number.
    """
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            key = str(k).lower()
            if key in CONTACT_KEYS:
                continue
            if any(tok in key for tok in ("email", "phone", "address", "postal", "birth")):
                continue
            out[k] = strip_contact_fields(v)
        return out
    if isinstance(obj, list):
        return [strip_contact_fields(v) for v in obj]
    return obj


def _iso(v):
    return v.isoformat() if isinstance(v, date) else v


@dataclass(frozen=True, slots=True)
class CacheKey:
    provider: str
    action: str
    request: str
    window: str

    def digest(self) -> str:
        raw = "|".join([self.provider, self.action, self.request, self.window])
        return hashlib.sha256(raw.encode()).hexdigest()


@dataclass
class CacheEntry:
    key: str
    provider: str
    action: str
    window: str
    answers: list[dict]
    spend_usd: float
    spend_units: float
    latency_ms: float
    recorded_at: str
    raw: dict | None = None
    """The provider's own response body, contact-stripped.

    Storing only parsed answers was a real design defect: every parser bug then
    cost credits to discover AND credits to verify a fix, on grants that do not
    refill. The cache is meant to be the unit of reproducibility - if a result
    cannot be regenerated from it, it is not reproducible - and a parser is part
    of what needs regenerating. Contact fields are stripped before this reaches
    disk, exactly as for `answers`.
    """


class ReplayCache:
    """Append-only JSONL. Never committed - .gitignore and the privacy gate
    both enforce that, and the gate fails the build if a cache file is tracked.
    """

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._index: dict[str, CacheEntry] = {}
        if self.path.exists():
            for line in self.path.read_text().splitlines():
                if line.strip():
                    d = json.loads(line)
                    self._index[d["key"]] = CacheEntry(**d)

    def __len__(self) -> int:
        return len(self._index)

    def __iter__(self) -> Iterator[CacheEntry]:
        return iter(self._index.values())

    def get(self, key: CacheKey) -> CacheEntry | None:
        return self._index.get(key.digest())

    def put(self, key: CacheKey, answers: list[RawAnswer], spend: Spend,
            latency_ms: float, recorded_at: str,
            raw: dict | None = None) -> CacheEntry:
        payload = [strip_contact_fields({k: _iso(v) for k, v in asdict(a).items()})
                   for a in answers]
        entry = CacheEntry(
            key=key.digest(), provider=key.provider, action=key.action,
            window=key.window, answers=payload, spend_usd=spend.usd,
            spend_units=spend.units, latency_ms=latency_ms, recorded_at=recorded_at,
            raw=strip_contact_fields(raw) if raw is not None else None,
        )
        self._index[entry.key] = entry
        with self.path.open("a") as fh:
            fh.write(json.dumps(asdict(entry)) + "\n")
        return entry

    @staticmethod
    def reparse(entry: CacheEntry, parser) -> list[RawAnswer] | None:
        """Re-derive answers from the stored raw body with a (possibly fixed)
        parser. Returns None when no raw body was recorded, so a caller can fall
        back to the stored answers rather than silently getting nothing."""
        if entry.raw is None:
            return None
        return parser(entry.raw)

    @staticmethod
    def to_answers(entry: CacheEntry) -> list[RawAnswer]:
        out = []
        for d in entry.answers:
            d = dict(d)
            for f in ("employment_start", "employment_end", "last_seen"):
                if d.get(f):
                    d[f] = date.fromisoformat(d[f])
            out.append(RawAnswer(**{k: v for k, v in d.items()
                                    if k in RawAnswer.__slots__}))
        return out

    def total_spend_usd(self) -> float:
        return sum(e.spend_usd for e in self._index.values())
