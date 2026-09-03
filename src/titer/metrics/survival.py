"""Reflection probability as a function of elapsed days. See D023.

Each task is observed exactly once: at elapsed time delta we see whether the
index reflects the move. That is **current status data** - the event time is
interval-censored at a single inspection point - not the right-censored
time-to-event data Kaplan-Meier estimates.

The nonparametric maximum likelihood estimator for current status data is
isotonic regression on the indicators ordered by delta, computed with the Pool
Adjacent Violators Algorithm. It is monotone by construction, which encodes the
only structural assumption we are willing to make: an index that has reflected
a change does not un-reflect it.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from titer.metrics.intervals import Interval, wilson


@dataclass(frozen=True, slots=True)
class Step:
    delta: int
    prob: float
    n: int


@dataclass(frozen=True, slots=True)
class ReflectionCurve:
    steps: list[Step]
    n: int

    def at(self, delta: int) -> float:
        """Estimated P(reflected) at an elapsed time."""
        out = 0.0
        for s in self.steps:
            if s.delta <= delta:
                out = s.prob
            else:
                break
        return out

    def median_lag(self) -> int | None:
        """Smallest elapsed day at which the estimate reaches 0.5.

        None means the curve never reaches 0.5 in the observed range - which is
        itself a result, and must be reported as "not reached within N days"
        rather than silently extrapolated.
        """
        for s in self.steps:
            if s.prob >= 0.5:
                return s.delta
        return None

    def is_monotone(self) -> bool:
        return all(a.prob <= b.prob + 1e-12 for a, b in zip(self.steps, self.steps[1:]))


def pava(observations: Sequence[tuple[int, bool]]) -> ReflectionCurve:
    """Pool Adjacent Violators. `observations` is (elapsed_days, reflected)."""
    if not observations:
        return ReflectionCurve([], 0)
    pts = sorted(observations, key=lambda o: o[0])

    # Collapse ties in delta into a single block first.
    blocks: list[list[float]] = []          # [sum, count, delta]
    for delta, hit in pts:
        if blocks and blocks[-1][2] == delta:
            blocks[-1][0] += float(hit)
            blocks[-1][1] += 1
        else:
            blocks.append([float(hit), 1.0, delta])

    # Pool while the sequence of block means decreases.
    merged: list[list[float]] = []
    for b in blocks:
        merged.append(b)
        while len(merged) >= 2 and (merged[-2][0] / merged[-2][1]) > (merged[-1][0] / merged[-1][1]):
            last = merged.pop()
            prev = merged.pop()
            merged.append([prev[0] + last[0], prev[1] + last[1], last[2]])

    steps = [Step(delta=int(d), prob=s / c, n=int(c)) for s, c, d in merged]
    return ReflectionCurve(steps, n=len(pts))


def binned_rates(observations: Sequence[tuple[int, bool]],
                 edges: Sequence[int] = (0, 30, 90, 180, 365, 730, 10_000)
                 ) -> list[tuple[str, Interval]]:
    """Reflection rate per elapsed-time bucket, each with a Wilson interval.

    Published alongside the isotonic curve because a step function is easy to
    over-read; the bucketed rates show how much data sits under each step.
    """
    out = []
    for lo, hi in zip(edges, edges[1:]):
        sel = [hit for d, hit in observations if lo <= d < hi]
        label = f"{lo}-{hi if hi < 10_000 else 'inf'}d"
        out.append((label, wilson(sum(sel), len(sel))))
    return out
