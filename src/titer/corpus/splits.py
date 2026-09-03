"""Signature-disjoint splits, and the probe that proves they are disjoint.

The frozen test split is drawn once, by seed, and is never used for checkpoint
selection. Selection happens on the hill-climb split. See CONTRACTS.md 7.

The leak probe is the important part. A probe that cannot detect a deliberate
leak is not evidence of a clean split, so `leak_rate` is tested in both
directions: it must read 1.0 when the test set is copied from train, and 0.0
when the split is honest.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Sequence

from titer.corpus.schema import AttestedTuple

TRAIN, HILLCLIMB, TEST = "train", "hillclimb", "test"


@dataclass(frozen=True, slots=True)
class Splits:
    train: list[AttestedTuple]
    hillclimb: list[AttestedTuple]
    test: list[AttestedTuple]

    def counts(self) -> dict[str, int]:
        return {TRAIN: len(self.train), HILLCLIMB: len(self.hillclimb), TEST: len(self.test)}


def _bucket(signature: str, seed: int) -> int:
    """Deterministic bucket in [0, 100) from the signature and the seed.

    Hashing the signature rather than using Python's `hash` matters: `hash` is
    salted per process, so a split built on Monday would differ on Tuesday.
    """
    h = hashlib.sha256(f"{seed}|{signature}".encode()).hexdigest()
    return int(h[:8], 16) % 100


def split(rows: Iterable[AttestedTuple], seed: int = 11,
          hillclimb_pct: int = 15, test_pct: int = 15,
          by: str = "person") -> Splits:
    """Split by PERSON, not by signature and not by row.

    Signature bucketing satisfies CONTRACTS 7 literally - two filings of one
    attested fact share a signature and co-locate - but it leaves a real leak
    open, and made the leak probe unfalsifiable at the same time.

    The same executive generates many DIFFERENT signatures across a career:
    different issuers, titles and periods. Under signature bucketing those land
    in different splits, so a model can meet a person in training and be scored
    on that same person at test. Meanwhile `leak_rate` over signatures reads
    exactly 0.0 for any input, because the bucket is a pure function of the
    signature - it verified a property of the implementation, not of the corpus.

    Bucketing by `person_cik` closes the leak and is strictly stronger than
    signature-disjointness. `by="signature"` is retained ONLY so the probe can
    demonstrate it has power by measuring the leak the old scheme allowed.
    """
    assert 0 < hillclimb_pct + test_pct < 100
    train: list[AttestedTuple] = []
    hill: list[AttestedTuple] = []
    test: list[AttestedTuple] = []
    for r in rows:
        key = r.person_cik if by == "person" else r.signature()
        b = _bucket(key, seed)
        if b < test_pct:
            test.append(r)
        elif b < test_pct + hillclimb_pct:
            hill.append(r)
        else:
            train.append(r)
    return Splits(train=train, hillclimb=hill, test=test)


def leak_rate(train: Sequence[AttestedTuple], held_out: Sequence[AttestedTuple],
              level: str = "person") -> float:
    """Fraction of held-out items whose key also appears in train.

    `level="person"` is the informative one: it can be nonzero, and under
    signature bucketing it IS nonzero, which is what gives this probe power.
    `level="signature"` is the literal CONTRACTS 7 check.

    0.0 on an honest split. 1.0 when the held-out set was copied from train.
    Anything between is a partial leak and is a defect, not a warning.
    """
    if not held_out:
        return 0.0
    key = (lambda r: r.person_cik) if level == "person" else (lambda r: r.signature())
    train_keys = {key(r) for r in train}
    return sum(1 for r in held_out if key(r) in train_keys) / len(held_out)


def duplication_rates(rows: Sequence[AttestedTuple]) -> dict[str, float]:
    """Two different things, separated - they were previously conflated.

    An earlier version counted any repeat of (person, issuer) and called the
    result the near-duplicate rate. On the real corpus that reads 0.91, because
    an active insider files dozens of Form 4s a year at one employer. That is
    not near-duplication in any sense that matters: `signature()` already treats
    the same attested fact filed twice as ONE task.

    * `repeat_filing_rate` - rows beyond the first per (person, issuer, period).
      The same fact filed again. Collapsed by signature; harmless.
    * `near_duplicate_rate` - rows beyond the first per (person, issuer) at a
      DIFFERENT period. The same relationship re-attested later. This is the one
      worth watching, and the one the docstring always claimed to measure.
    """
    if not rows:
        return {"repeat_filing_rate": 0.0, "near_duplicate_rate": 0.0}
    seen_fact: set[tuple[str, str, str]] = set()
    seen_rel: set[tuple[str, str]] = set()
    repeat = near = 0
    for r in rows:
        fact = (r.person_cik, r.issuer_cik, r.period.isoformat())
        rel = (r.person_cik, r.issuer_cik)
        if fact in seen_fact:
            repeat += 1
        elif rel in seen_rel:
            near += 1
        seen_fact.add(fact)
        seen_rel.add(rel)
    n = len(rows)
    return {"repeat_filing_rate": repeat / n, "near_duplicate_rate": near / n}


def near_duplicate_rate(rows: Sequence[AttestedTuple]) -> float:
    return duplication_rates(rows)["near_duplicate_rate"]
