"""The seed rule. Not advisory.

`reconforge` published a headline whose across-seed standard deviation was
2.86x the claimed margin, and retracted it in its own README. The rule that
came out of it: **no margin is quoted without its across-seed spread, and if
the spread exceeds the margin there is no claim.**

This module makes that a function that returns a verdict, so a claim cannot be
written down without one.
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from typing import Sequence

MIN_SEEDS = 4


@dataclass(frozen=True, slots=True)
class SeedVerdict:
    arm: str
    seeds: int
    mean: float
    sd: float
    baseline: float
    margin: float
    ratio: float
    claimable: bool
    reason: str

    def __str__(self) -> str:
        head = "CLAIM" if self.claimable else "NO CLAIM"
        return (f"[{head}] {self.arm}: mean {self.mean:.4f} vs baseline "
                f"{self.baseline:.4f}, margin {self.margin:.4f}, across-seed SD "
                f"{self.sd:.4f} ({self.ratio:.2f}x the margin) over {self.seeds} "
                f"seeds - {self.reason}")


def verdict(arm: str, scores: Sequence[float], baseline: float,
            min_seeds: int = MIN_SEEDS) -> SeedVerdict:
    n = len(scores)
    mean = statistics.fmean(scores) if scores else 0.0
    sd = statistics.stdev(scores) if n >= 2 else float("inf")
    margin = mean - baseline
    ratio = (sd / abs(margin)) if margin else float("inf")

    if n < min_seeds:
        return SeedVerdict(arm, n, mean, sd, baseline, margin, ratio, False,
                           f"only {n} seeds; {min_seeds} is the minimum")
    if margin <= 0:
        return SeedVerdict(arm, n, mean, sd, baseline, margin, ratio, False,
                           "the arm does not beat the baseline on the mean")
    if sd >= margin:
        return SeedVerdict(arm, n, mean, sd, baseline, margin, ratio, False,
                           "across-seed SD equals or exceeds the margin, so the "
                           "margin is seed noise - this is the reconforge failure")
    return SeedVerdict(arm, n, mean, sd, baseline, margin, ratio, True,
                       "margin exceeds the across-seed spread")


def format_report(verdicts: Sequence[SeedVerdict]) -> str:
    return "\n".join(str(v) for v in verdicts)
