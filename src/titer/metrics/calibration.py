"""Calibration of the free signals, and abstention under a loss matrix.

Two contract rules are enforced in code rather than trusted to discipline:

1. **Ten equal-width bins, and an empty bin is reported as empty.** Merging
   empty bins flatters calibration by removing the regions where the model has
   nothing to say. `ReliabilityDiagram.bins` always has ten entries.

2. **Coverage and floor are returned as a pair.** A caller cannot obtain one
   without the other, because a risk floor at an unstated coverage is
   meaningless - you can always drive risk to zero by answering nothing.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

N_BINS = 10


@dataclass(frozen=True, slots=True)
class Bin:
    lo: float
    hi: float
    n: int
    mean_confidence: float | None
    accuracy: float | None

    @property
    def empty(self) -> bool:
        return self.n == 0

    @property
    def gap(self) -> float:
        if self.empty:
            return 0.0
        return abs(self.mean_confidence - self.accuracy)


@dataclass(frozen=True, slots=True)
class ReliabilityDiagram:
    bins: list[Bin]
    n: int

    @property
    def empty_bins(self) -> int:
        return sum(1 for b in self.bins if b.empty)

    @property
    def ece(self) -> float:
        """Expected calibration error, weighted by bin occupancy.

        Empty bins contribute zero weight and zero error - they are neither
        merged away nor counted as perfectly calibrated.
        """
        if self.n == 0:
            return 0.0
        return sum(b.n / self.n * b.gap for b in self.bins if not b.empty)

    def as_dict(self) -> dict:
        return {
            "n": self.n,
            "n_bins": len(self.bins),
            "empty_bins": self.empty_bins,
            "ece": self.ece,
            "bins": [
                {"lo": b.lo, "hi": b.hi, "n": b.n,
                 "mean_confidence": b.mean_confidence, "accuracy": b.accuracy,
                 "empty": b.empty}
                for b in self.bins
            ],
        }


def reliability(confidences: Sequence[float], correct: Sequence[bool],
                n_bins: int = N_BINS) -> ReliabilityDiagram:
    if len(confidences) != len(correct):
        raise ValueError("confidences and correct must be the same length")
    # A confidence outside [0, 1] matches no bin, so it vanished from every bin
    # while still counting in `n`. The bin weights then no longer summed to 1
    # and ECE was silently biased LOW - a miscalibration measurement quietly
    # reporting better calibration than the data supports.
    bad = [c for c in confidences if not (0.0 <= c <= 1.0)]
    if bad:
        raise ValueError(
            f"{len(bad)} confidence value(s) outside [0, 1], e.g. {bad[:3]}. "
            "Refusing to bin them: they would drop out of every bin while still "
            "counting in n, biasing ECE low."
        )
    edges = [i / n_bins for i in range(n_bins + 1)]
    bins: list[Bin] = []
    for lo, hi in zip(edges, edges[1:]):
        # Last bin is closed on the right so confidence exactly 1.0 lands somewhere.
        last = hi == 1.0
        sel = [(c, k) for c, k in zip(confidences, correct)
               if (lo <= c <= hi) if last or c < hi]
        if not sel:
            bins.append(Bin(lo, hi, 0, None, None))
        else:
            bins.append(Bin(lo, hi, len(sel),
                            sum(c for c, _ in sel) / len(sel),
                            sum(1 for _, k in sel if k) / len(sel)))
    return ReliabilityDiagram(bins, len(confidences))


def brier(confidences: Sequence[float], correct: Sequence[bool]) -> float:
    if not confidences:
        return 0.0
    return sum((c - float(k)) ** 2 for c, k in zip(confidences, correct)) / len(confidences)


# --- isotonic recalibration (PAVA on confidence order) ---

def fit_isotonic(confidences: Sequence[float], correct: Sequence[bool]):
    """Fit a monotone recalibration map on a split disjoint from evaluation.

    Returns a callable. Fitting and applying on the same data would report a
    calibration improvement that does not exist.
    """
    pts = sorted(zip(confidences, correct), key=lambda t: t[0])
    if not pts:
        return lambda c: c
    blocks: list[list[float]] = []
    for c, k in pts:
        blocks.append([float(k), 1.0, c])
        while len(blocks) >= 2 and (blocks[-2][0] / blocks[-2][1]) > (blocks[-1][0] / blocks[-1][1]):
            last = blocks.pop()
            prev = blocks.pop()
            blocks.append([prev[0] + last[0], prev[1] + last[1], last[2]])
    xs = [b[2] for b in blocks]
    ys = [b[0] / b[1] for b in blocks]

    def apply(c: float) -> float:
        out = ys[0]
        for x, y in zip(xs, ys):
            if c >= x:
                out = y
            else:
                break
        return out

    return apply


# --- abstention ---

@dataclass(frozen=True, slots=True)
class CoverageFloor:
    """Deliberately a single object. See the module docstring."""

    threshold: float
    coverage: float
    risk: float
    n_answered: int
    n_total: int


def coverage_floor(confidences: Sequence[float], correct: Sequence[bool],
                   threshold: float) -> CoverageFloor:
    """Answer only above `threshold`; report what that buys AND what it costs."""
    n = len(confidences)
    kept = [(c, k) for c, k in zip(confidences, correct) if c >= threshold]
    if not kept:
        return CoverageFloor(threshold, 0.0, 0.0, 0, n)
    risk = sum(1 for _, k in kept if not k) / len(kept)
    return CoverageFloor(threshold, len(kept) / n if n else 0.0, risk, len(kept), n)


def risk_coverage_curve(confidences: Sequence[float], correct: Sequence[bool],
                        steps: int = 21) -> list[CoverageFloor]:
    return [coverage_floor(confidences, correct, i / (steps - 1)) for i in range(steps)]
