#!/usr/bin/env python3
"""RED-TEAM A12, the free half: are affirmations backed by a real work?

A12 says the measured false-affirmation rate may be prompt interpretation
rather than error - the provider may read "has expertise in T" as "works near
T". The control tier bounded that from below (8.4 points no reading explains).
This bounds it from a different direction, and costs nothing.

Every one of the 2,388 cached `/answer` responses already carries citations,
mean 7.99 each. So for each AFFIRMATION we can ask, programmatically:

    does any cited title resolve to a work that OpenAlex says this person
    actually wrote?

An affirmation whose only support is a Google Scholar profile or a staff page
cites no attested work. That is not a judgement about the provider's reading of
the question - it is a fact about what it returned.

No model reads the evidence string. A model assigning that label is the
circularity D022 bans. OpenAlex is free; this spends nothing.
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from titer.adapters.cache import CacheKey
from titer.corpus.scholar import OpenAlexError, cited_work_by_author, user_agent, work_exists
from titer.metrics.intervals import wilson

TASK_FILES = ["expert_tasks_v2.jsonl", "expert_tasks_control.jsonl",
              "expert_tasks.jsonl"]


def load_tasks() -> dict[str, dict]:
    tasks: dict[str, dict] = {}
    for f in TASK_FILES:
        p = ROOT / "data" / f
        if p.exists():
            for line in p.open():
                t = json.loads(line)
                tasks.setdefault(t["task_id"], t)
    return tasks


def stratum(t: dict) -> str:
    return (t["polarity"] if t["polarity"] == "ATTESTED"
            else f"FALSE_{t['negative_tier']}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--citations", type=int, default=3,
                    help="titles checked per affirmation")
    ap.add_argument("--attested-sample", type=int, default=250)
    ap.add_argument("--out", default="a12_citation_audit.json")
    ap.add_argument("--interval", type=float, default=0.6,
                    help="extra seconds between affirmations. OpenAlex's polite "
                         "pool 429s under a burst; this is not a retry loop.")
    args = ap.parse_args()

    ua = user_agent(os.environ.get("TITER_OPENALEX_MAILTO", "titer-audit"))
    tasks = load_tasks()
    by_key = {}
    for line in (ROOT / "data" / "replay.jsonl").open():
        e = json.loads(line)
        if e.get("provider") == "exa" and e.get("action") == "expertise":
            by_key[e["key"]] = e

    # Collect affirmations, keeping every false one and a capped attested sample.
    work = []
    seen_attested = 0
    for tid, t in tasks.items():
        e = by_key.get(CacheKey("exa", "expertise", tid, "2026-09").digest())
        if e is None:
            continue
        a = (e.get("raw") or {}).get("answer")
        if isinstance(a, str):
            try:
                a = json.loads(a)
            except ValueError:
                a = None
        if not isinstance(a, dict) or a.get("affirms") is not True:
            continue
        st = stratum(t)
        if st == "ATTESTED":
            if seen_attested >= args.attested_sample:
                continue
            seen_attested += 1
        cites = [(c.get("title") or "") for c in (e["raw"].get("citations") or [])]
        work.append((st, t["author_id"], cites[:args.citations]))

    print(f"{len(work)} affirmations to audit "
          f"({collections.Counter(s for s, _, _ in work)})", flush=True)

    res: dict[str, dict] = collections.defaultdict(
        lambda: {"n": 0, "backed": 0, "title_exists_but_not_theirs": 0,
                 "no_resolvable_title": 0})
    # Checkpoint every 25. The first run lost 175 audited affirmations to an
    # exhausted OpenAlex key because results were only written at the end.
    ckpt = ROOT / "results" / (args.out.replace(".json", "_partial.json"))
    done: dict[str, dict] = {}
    if ckpt.exists():
        done = json.loads(ckpt.read_text())
        for st, b in done.items():
            res[st].update(b)
        print(f"resumed from checkpoint: {sum(b['n'] for b in done.values())} done")
    skip = sum(b["n"] for b in done.values())

    for i, (st, aid, cites) in enumerate(work, 1):
        if i <= skip:
            continue
        backed = False
        existed = False
        try:
            for title in cites:
                if cited_work_by_author(title, aid, ua) > 0:
                    backed = True
                    break
                if work_exists(title, ua) > 0:
                    existed = True
        except OpenAlexError as e:
            # Stop cleanly on a rate or budget wall. Checkpoint, report what
            # was actually audited, and say so. Grinding on would burn a
            # budget that is already gone, and a partial audit reported as
            # partial is worth more than a crash.
            print(f"\nstopped at {i}/{len(work)}: {e}", file=sys.stderr)
            ckpt.write_text(json.dumps({k: dict(v) for k, v in res.items()},
                                       indent=1))
            break
        time.sleep(args.interval)
        b = res[st]
        b["n"] += 1
        if backed:
            b["backed"] += 1
        elif existed:
            b["title_exists_but_not_theirs"] += 1
        else:
            b["no_resolvable_title"] += 1
        if i % 25 == 0:
            print(f"  {i}/{len(work)}", flush=True)
            ckpt.write_text(json.dumps({k: dict(v) for k, v in res.items()},
                                       indent=1))

    report = {"generated": __import__("datetime").date.today().isoformat(),
              "citations_checked_per_affirmation": args.citations,
              "spend_usd": 0.0,
              "audited": sum(b["n"] for b in res.values()),
              "requested": len(work),
              "method": ("For each affirmation, up to N cited titles are "
                         "resolved against OpenAlex. 'backed' means at least "
                         "one cited title is a work OpenAlex says this author "
                         "wrote. No model reads the evidence string."),
              "strata": {}}
    for st, b in sorted(res.items()):
        rate = b["backed"] / b["n"] if b["n"] else 0.0
        report["strata"][st] = {
            **b,
            "backed_rate": round(rate, 4),
            "backed_wilson": wilson(b["backed"], b["n"]),
        }
    (ROOT / "results" / args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["strata"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
