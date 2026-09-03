#!/usr/bin/env python3
"""E1: does a provider affirm expertise that is not attested?

Stratified by polarity and negative tier, per PRE-REGISTRATION-EXPERTISE section
1. Simple random sampling is prohibited there and is not offered here.

Dry-run by default. Every response lands in the replay cache with its raw body,
so re-scoring after a parser change costs nothing.
"""
from __future__ import annotations

import argparse
import collections
import json
import random
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.adapters.base import BudgetExceeded, Ledger  # noqa: E402
from titer.adapters.cache import CacheKey, ReplayCache  # noqa: E402
from titer.adapters.http import ProviderHTTPError, exa_transport  # noqa: E402
from titer.adapters.providers import Exa  # noqa: E402
from titer.costs.profiles import REPORTABLE, accuracy, expected_loss  # noqa: E402
from titer.metrics.calibration import brier, reliability  # noqa: E402
from titer.metrics.intervals import wilson  # noqa: E402
from titer.oracle.outcome import Outcome, judge_expertise  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "data" / "expert_tasks.jsonl"


def strat(t: dict) -> str:
    return t["polarity"] if t["polarity"] == "ATTESTED" else f"FALSE_{t['negative_tier']}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spend", action="store_true")
    ap.add_argument("--per-stratum", type=int, default=400)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--budget-usd", type=float, default=8.0)
    ap.add_argument("--out", default="expertise_e1.json")
    args = ap.parse_args()

    tasks = [json.loads(l) for l in TASKS.open()]
    by: dict[str, list] = collections.defaultdict(list)
    for t in tasks:
        by[strat(t)].append(t)
    rng = random.Random(args.seed)
    sample, strata = [], {}
    for k in sorted(by):
        pick = rng.sample(by[k], min(args.per_stratum, len(by[k])))
        strata[k] = {"available": len(by[k]), "sampled": len(pick)}
        sample.extend(pick)
    rng.shuffle(sample)
    print(f"strata: {strata}\nsampled {len(sample)} tasks, seed {args.seed}", flush=True)

    adapter = Exa(transport=exa_transport() if args.spend else None)
    cache = ReplayCache(ROOT / "data" / "replay.jsonl")
    ledger = Ledger(args.budget_usd)
    window = datetime.now().strftime("%Y-%m")
    recs: list[dict] = []

    for i, t in enumerate(sample, 1):
        key = CacheKey("exa", "expertise", t["task_id"], window)
        entry = cache.get(key)
        if entry is None:
            if not args.spend:
                continue
            try:
                ans, sp = adapter.query("expertise", t["prompt"])
            except (ProviderHTTPError, Exception) as e:  # noqa: BLE001
                print(f"  [{i}] {type(e).__name__}: {str(e)[:110]}", file=sys.stderr)
                continue
            try:
                ledger.charge(sp)
            except BudgetExceeded as e:
                print(f"  budget exhausted at {i}: {e}", file=sys.stderr)
                break
            entry = cache.put(key, [], sp, 0.0, datetime.now().isoformat(),
                              raw=adapter.last_raw)
        ans = Exa._parse_expertise(entry.raw or {})
        recs.append({"task_id": t["task_id"], "stratum": strat(t),
                     "polarity": t["polarity"], "tier": t["negative_tier"],
                     "outcome": judge_expertise(ans, t["polarity"]).value,
                     "affirms": ans.affirms, "confidence": ans.confidence,
                     "spend_usd": entry.spend_usd})
        if i % 100 == 0:
            print(f"  [{i}/{len(sample)}] spent ${ledger.spent.usd:.3f}", flush=True)

    report = {"window": window, "seed": args.seed, "dry_run": not args.spend,
              "strata": strata, "n": len(recs),
              "spend_usd": round(sum(r["spend_usd"] for r in recs), 4),
              "pooling_rule": ("STRATIFIED and deliberately balanced 50/50 by "
                               "polarity. Per-stratum rates only; a pooled "
                               "marginal rate would describe the task design, "
                               "not any population."),
              "by_stratum": {}}
    for s in sorted({r["stratum"] for r in recs}):
        sub = [r for r in recs if r["stratum"] == s]
        outs = [Outcome(r["outcome"]) for r in sub]
        n = len(outs)
        report["by_stratum"][s] = {
            "n": n,
            "outcomes": {o.value: sum(1 for x in outs if x is o) for o in Outcome
                         if any(x is o for x in outs)},
            "accuracy": accuracy(outs),
            "correct": str(wilson(sum(1 for o in outs if o is Outcome.CORRECT), n)),
            "false_merge": str(wilson(sum(1 for o in outs if o is Outcome.FALSE_MERGE), n)),
            "expected_loss": {p: expected_loss(outs, prof)
                              for p, prof in REPORTABLE.items()},
        }
    if recs:
        confs = [r["confidence"] for r in recs]
        ok = [Outcome(r["outcome"]) is Outcome.CORRECT for r in recs]
        report["calibration"] = {"brier": brier(confs, ok),
                                 **reliability(confs, ok).as_dict()}
    (ROOT / "results" / args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "calibration"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
