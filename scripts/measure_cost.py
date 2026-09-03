#!/usr/bin/env python3
"""Measure the real cost per task, then select the pre-registered power branch.

This is the first script that can spend money, so it is **dry-run by default**.
`--spend` is required to make a live call, and `--max-calls` caps it.

The output feeds scripts/power.py, which picks the branch of
docs/PRE-REGISTRATION.md section 3 that governs what may be claimed. Selecting
that branch from a measured number, before the measurement runs, is the whole
point - it is what stops a disappointing n being rationalised into a ranking.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.adapters.http import ProviderHTTPError, exa_transport, ploid_transport  # noqa: E402
from titer.adapters.providers import Exa, Ploid  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
PROBE = ("Jane Roe was an officer or director at Acme Corporation as of "
         "2020-01-01. What organisation were they at on 2023-01-01, and in what role?")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spend", action="store_true", help="make live, billable calls")
    ap.add_argument("--max-calls", type=int, default=2, help="per provider")
    ap.add_argument("--providers", default="exa,ploid")
    args = ap.parse_args()

    wanted = [p.strip() for p in args.providers.split(",") if p.strip()]
    report: dict = {"dry_run": not args.spend, "providers": {}}

    for name in wanted:
        entry: dict = {}
        try:
            if name == "ploid":
                adapter = Ploid(transport=ploid_transport() if args.spend else None)
                action = "search_fast"
            elif name == "exa":
                adapter = Exa(transport=exa_transport() if args.spend else None)
                action = "search"
            else:
                entry = {"error": f"unknown provider {name}"}
                report["providers"][name] = entry
                continue
            entry["list_price_usd"] = next(c.list_price_usd for c in adapter.actions()
                                           if c.action == action)
            if not args.spend:
                entry["note"] = "dry run: no call made. Re-run with --spend."
            else:
                answers, spend = adapter.query(action, PROBE, num_results=10)
                entry.update({"observed_spend_usd": spend.usd, "n_answers": len(answers),
                              "first": {"name": answers[0].person_name,
                                        "employer": answers[0].employer_name,
                                        "confidence": answers[0].confidence}
                              if answers else None})
        except ProviderHTTPError as e:
            entry["error"] = str(e)
        except Exception as e:  # noqa: BLE001 - surface the cause, do not retry
            entry["error"] = f"{type(e).__name__}: {e}"
        report["providers"][name] = entry

    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "cost_unit.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
