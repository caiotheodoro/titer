#!/usr/bin/env python3
"""E4 - does the same provider know the two populations equally well?

Pre-registration: "The same provider resolves the academic population and the
SEC executive population at materially different rates. Identical instruments
over both corpora, reported side by side, never pooled. Falsified if the paired
difference interval contains zero."

The identical instrument is the **name-only** question - the E2 arm-A rendering
- asked of both populations:

    "<name>. What organisation are they at most recently, and in what role?"

Name-only is the one rendering both populations can receive unchanged. Anything
richer would need an anchor, and the scholar corpus carries no affiliation
history to anchor on, so a richer prompt would not be the same instrument.

**The oracles are not equally strong, and that is a limit, not a detail.** SEC
truth is a filing an officer signed. Scholar truth is OpenAlex
`last_known_institutions`, derived from publication affiliations, which lags a
move and can be stale. A gap in this measurement is therefore a gap in
(index coverage x oracle freshness), and it cannot be split without a second
scholarly oracle. Reported both ways round rather than resolved.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from titer.adapters.base import BudgetExceeded, Ledger
from titer.adapters.cache import CacheKey, ReplayCache
from titer.adapters.http import ProviderHTTPError, exa_transport
from titer.adapters.providers import Exa
from titer.corpus.name_norm import normalize_company, presented_query_name
from titer.metrics.intervals import wilson

QUESTION = ("What organisation are they at most recently, and in what role? "
            "Answer for their latest known position."
            " Give your confidence as a number between 0 and 1.")


def render(name: str) -> str:
    return f"{name}. {QUESTION}"


def scholar_tasks(n: int, rng: random.Random) -> list[dict]:
    rows = [json.loads(l) for l in (ROOT / "data" / "scholar.jsonl").open()]
    rows = [r for r in rows if r.get("institution") and r.get("display_name")]
    return [{"population": "scholar", "task_id": f"sch-{r['author_id'].rsplit('/', 1)[-1]}",
             "name": r["display_name"], "truth": r["institution"]}
            for r in rng.sample(rows, min(n, len(rows)))]


def sec_tasks(n: int, rng: random.Random) -> list[dict]:
    rows = [json.loads(l) for l in (ROOT / "data" / "tasks.jsonl").open()]
    rows = [r for r in rows if r["collision_band"] == "unique"]
    out = []
    for r in rng.sample(rows, min(n, len(rows))):
        out.append({"population": "sec", "task_id": f"sec-{r['person_cik']}",
                    "name": presented_query_name(r["person_name_raw"]),
                    "truth": r["truth_issuer_name"]})
    return out


def matches(returned: str | None, truth: str) -> bool:
    """Deterministic normalised organisation match. No model, no fuzzy score."""
    if not returned:
        return False
    a, b = normalize_company(returned), normalize_company(truth)
    if not a or not b:
        return False
    return a == b or a in b or b in a


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spend", action="store_true")
    ap.add_argument("--n", type=int, default=250, help="per population")
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--budget-usd", type=float, default=3.0)
    ap.add_argument("--max-calls", type=int, default=520)
    ap.add_argument("--out", default="e4_coverage.json")
    args = ap.parse_args()

    rng = random.Random(args.seed)
    tasks = sec_tasks(args.n, rng) + scholar_tasks(args.n, rng)
    rng.shuffle(tasks)

    adapter = Exa(transport=exa_transport() if args.spend else None)
    cache = ReplayCache(ROOT / "data" / "replay.jsonl")
    ledger = Ledger(args.budget_usd)
    window = datetime.now().strftime("%Y-%m")
    live = 0
    recs: list[dict] = []

    for i, t in enumerate(tasks, 1):
        prompt = render(t["name"])
        key = CacheKey("exa", "e4_answer", f"{t['task_id']}|{prompt}", window)
        entry = cache.get(key)
        if entry is None:
            if not args.spend:
                continue
            if live >= args.max_calls:
                print(f"  call cap reached at {i}", file=sys.stderr)
                break
            try:
                answers, sp = adapter.query("answer", prompt)
            except (ProviderHTTPError, Exception) as e:  # noqa: BLE001
                print(f"  [{i}] {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
                continue
            try:
                ledger.charge(sp)
            except BudgetExceeded as e:
                print(f"  budget exhausted at {i}: {e}", file=sys.stderr)
                break
            live += 1
            entry = cache.put(key, answers, sp, 0.0, datetime.now().isoformat(),
                              raw=getattr(adapter, "last_raw", None))
        got = ReplayCache.to_answers(entry)
        top = got[0] if got else None
        emp = top.employer_name if top else None
        recs.append({"population": t["population"], "task_id": t["task_id"],
                     "returned": emp, "truth": t["truth"],
                     "named_someone": bool(emp),
                     "correct": matches(emp, t["truth"]),
                     "confidence": top.confidence if top else 0.0,
                     "spend_usd": entry.spend_usd})
        if i % 50 == 0:
            print(f"  {i}/{len(tasks)}  live={live}  spend=${ledger.spent.usd:.2f}",
                  flush=True)

    report = {"generated": datetime.now().date().isoformat(),
              "instrument": "name-only; identical string for both populations",
              "n_requested_per_population": args.n,
              "live_calls": live,
              "spend_usd": round(sum(r["spend_usd"] for r in recs), 4),
              "pooling_rule": ("Reported per population and NEVER pooled. The "
                               "two oracles differ in strength: a filing versus "
                               "OpenAlex last_known_institutions, which lags a "
                               "move. A gap is coverage x oracle freshness."),
              "populations": {}}
    for pop in ("sec", "scholar"):
        rs = [r for r in recs if r["population"] == pop]
        if not rs:
            continue
        n = len(rs)
        report["populations"][pop] = {
            "n": n,
            "named_someone": str(wilson(sum(r["named_someone"] for r in rs), n)),
            "correct": str(wilson(sum(r["correct"] for r in rs), n)),
            "correct_rate": round(sum(r["correct"] for r in rs) / n, 4),
        }
    # Unpaired: the two populations are different people, so the difference is
    # a between-population contrast, not a within-task one. No paired bootstrap.
    (ROOT / "results" / args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["populations"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
