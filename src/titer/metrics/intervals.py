"""Intervals. Every reported rate carries one; a rate without one is a defect.

Deliberately stdlib-only. These are small, exact, and auditable, and a reviewer
should be able to check them against a textbook without installing anything.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Callable, Sequence, TypeVar

T = TypeVar("T")
Z95 = 1.959963984540054


@dataclass(frozen=True, slots=True)
class Interval:
    point: float | None
    lo: float
    hi: float
    n: int

    @property
    def half_width(self) -> float:
        return (self.hi - self.lo) / 2

    def __str__(self) -> str:
        pt = "empty" if self.point is None else f"{self.point:.4f}"
        return f"{pt} [{self.lo:.4f}, {self.hi:.4f}] n={self.n}"


def wilson(successes: int, n: int, z: float = Z95) -> Interval:
    """Wilson score interval.

    Used rather than the normal approximation because at our sample sizes the
    normal interval misbehaves badly near 0 and 1 - and rates near 0 (a
    false-merge rate, say) are exactly what we expect to be reporting.
    """
    if n == 0:
        # `point=None`, never 0.0. A bin with no data must render as empty; a
        # hard zero on a chart is a claim that the rate IS zero.
        return Interval(None, 0.0, 1.0, 0)
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return Interval(p, max(0.0, centre - margin), min(1.0, centre + margin), n)


def required_n(p: float, half_width: float, z: float = Z95) -> int:
    """Sample size for a target half-width at an assumed rate.

    Reported when the achievable n is too small, so that "we could not tell"
    comes with "here is what it would have taken". PRE-REGISTRATION section 3.
    """
    p = min(max(p, 1e-6), 1 - 1e-6)
    return math.ceil((z * z * p * (1 - p)) / (half_width * half_width))


def paired_bootstrap(
    a: Sequence[T],
    b: Sequence[T],
    statistic: Callable[[Sequence[T]], float],
    resamples: int = 10_000,
    seed: int = 11,
    z: float = Z95,
) -> Interval:
    """Percentile bootstrap CI for statistic(a) - statistic(b), resampling the
    *task index* so both arms are resampled together.

    Pairing is what makes a small n worth anything: the arms saw the identical
    tasks in the identical order, so the between-task variance cancels. Resample
    the arms independently and you throw that away.
    """
    if len(a) != len(b):
        raise ValueError(f"paired bootstrap needs equal lengths, got {len(a)} and {len(b)}")
    n = len(a)
    if n == 0:
        return Interval(0.0, 0.0, 0.0, 0)
    point = statistic(a) - statistic(b)
    rng = random.Random(seed)
    diffs = []
    for _ in range(resamples):
        idx = [rng.randrange(n) for _ in range(n)]
        diffs.append(statistic([a[i] for i in idx]) - statistic([b[i] for i in idx]))
    diffs.sort()
    lo = diffs[int(0.025 * resamples)]
    hi = diffs[min(int(0.975 * resamples), resamples - 1)]
    return Interval(point, lo, hi, n)


def separates(interval: Interval) -> bool:
    """Does a difference interval exclude zero? The only ranking test we use."""
    return interval.lo > 0 or interval.hi < 0
