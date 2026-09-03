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
          hillclimb_pct: int = 15, test_pct: int = 15) -> Splits:
    """Split by *signature*, not by row.

    Two filings of the same attested fact share a signature and therefore land
    in the same split. Splitting by row would put them on opposite sides and
    leak the answer.
    """
    assert 0 < hillclimb_pct + test_pct < 100
    train: list[AttestedTuple] = []
    hill: list[AttestedTuple] = []
    test: list[AttestedTuple] = []
    for r in rows:
        b = _bucket(r.signature(), seed)
        if b < test_pct:
            test.append(r)
        elif b < test_pct + hillclimb_pct:
            hill.append(r)
        else:
            train.append(r)
    return Splits(train=train, hillclimb=hill, test=test)


def leak_rate(train: Sequence[AttestedTuple], held_out: Sequence[AttestedTuple]) -> float:
    """Fraction of held-out signatures that also appear in train.

    0.0 on an honest split. 1.0 when the held-out set was copied from train.
    Anything in between is a partial leak and is a defect, not a warning.
    """
    if not held_out:
        return 0.0
    train_sigs = {r.signature() for r in train}
    hit = sum(1 for r in held_out if r.signature() in train_sigs)
    return hit / len(held_out)


def near_duplicate_rate(rows: Sequence[AttestedTuple]) -> float:
    """Same person at the same issuer in a different quarter.

    Published rather than assumed to be zero: a corpus spanning 20 years of
    quarterly filings is full of the same executive filing again and again.
    """
    if not rows:
        return 0.0
    seen: set[tuple[str, str]] = set()
    dup = 0
    for r in rows:
        key = (r.person_cik, r.issuer_cik)
        if key in seen:
            dup += 1
        else:
            seen.add(key)
    return dup / len(rows)
