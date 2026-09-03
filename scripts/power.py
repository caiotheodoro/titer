#!/usr/bin/env python3
"""Power analysis. Run BEFORE any credit is spent.

Answers two questions and writes them down so they cannot be renegotiated later:

  1. What sample size would each hypothesis need?
  2. What sample size can this budget actually buy?

Then it selects the branch of docs/PRE-REGISTRATION.md section 3 that applies,
and records it. Committing to the branch before seeing results is the only thing
that stops a disappointing n being rationalised into a ranking afterwards.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.metrics.intervals import required_n, wilson  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "results"

# PRE-REGISTRATION section 3. Half-width thresholds and what each permits.
BRANCHES = [
    (0.05, "ranking", "Comparisons may be reported as rankings."),
    (0.10, "intervals_only",
     "Comparisons are reported as intervals only. No ranking language anywhere, "
     "including the README and any abstract."),
    (float("inf"), "cannot_separate",
     "This budget cannot separate the providers. Publish the intervals anyway, "
     "and publish the n each hypothesis would have required."),
]

# Rates we expect to be estimating. Deliberately pessimistic: p near 0.5
# maximises the required n, so a plan that works at these rates works at the
# rates we actually hope to see.
ASSUMED = {
    "H1 reflection rate per elapsed-time bucket": 0.50,
    "H2 false-merge rate": 0.15,
    "H3 calibration bucket occupancy": 0.10,
}


def branch_for(half_width: float):
    for threshold, name, note in BRANCHES:
        if half_width <= threshold:
            return name, note
    raise AssertionError("unreachable")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--budget-usd", type=float, default=5.0)
    ap.add_argument("--cost-per-task-usd", type=float, default=None,
                    help="measured by scripts/measure_cost.py; omit to sweep")
    args = ap.parse_args()

    report: dict = {
        "budget_usd": args.budget_usd,
        "required_n": {k: {f"hw={hw}": required_n(p, hw)
                           for hw in (0.14, 0.10, 0.07, 0.05, 0.035)}
                       for k, p in ASSUMED.items()},
        "assumed_rates": ASSUMED,
    }

    print("Required n (95% Wilson), by assumed rate and target half-width:")
    for name, p in ASSUMED.items():
        row = "  ".join(f"hw={hw:.3f}:n={required_n(p, hw):>5}"
                        for hw in (0.14, 0.10, 0.07, 0.05, 0.035))
        print(f"  p={p:.2f}  {name}\n           {row}")

    print("\nAchievable n at this budget:")
    costs = ([args.cost_per_task_usd] if args.cost_per_task_usd
             else [0.01, 0.02, 0.05, 0.10, 0.20, 0.50])
    achievable = {}
    for c in costs:
        n = int(args.budget_usd // c)
        hw = wilson(int(round(0.15 * n)), n).half_width if n else 1.0
        name, note = branch_for(hw)
        achievable[f"${c:.2f}/task"] = {"n": n, "half_width_at_p015": hw, "branch": name}
        flag = "  <-- measured" if args.cost_per_task_usd else ""
        print(f"  ${c:>5.2f}/task -> n={n:>4}  half-width@p=0.15 {hw:.4f}  branch={name}{flag}")
    report["achievable"] = achievable

    if args.cost_per_task_usd:
        n = int(args.budget_usd // args.cost_per_task_usd)
        hw = wilson(int(round(0.15 * n)), n).half_width if n else 1.0
        name, note = branch_for(hw)
        report["selected_branch"] = {"n": n, "half_width": hw, "branch": name, "note": note}
        print(f"\nSELECTED BRANCH: {name}\n  {note}")
    else:
        print("\nNo measured cost supplied, so no branch is selected yet.")
        print("Run scripts/measure_cost.py first, then re-run with --cost-per-task-usd.")

    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "power.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nwrote {RESULTS / 'power.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
