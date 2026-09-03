#!/usr/bin/env python3
"""Run the measurement: R1 staleness and R2 false merge, paired across arms.

Every arm receives the IDENTICAL task set in the IDENTICAL order, and each
renders it into the shape its own API documents (D025). Differences are computed
within-task, which is what makes a small n worth anything.

Dry-run by default. `--spend` is required to make billable calls, and a
per-provider Ledger raises rather than overspending.

Responses are written to the replay cache, so every table below regenerates
afterwards with no keys and no spend.
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.adapters.base import BudgetExceeded, Ledger  # noqa: E402
from titer.adapters.cache import CacheKey, ReplayCache  # noqa: E402
from titer.adapters.http import ProviderHTTPError, exa_transport, ploid_transport  # noqa: E402
from titer.adapters.providers import Exa, Ploid  # noqa: E402
from titer.corpus.collision import CollisionIndex  # noqa: E402
from titer.corpus.schema import AttestedTuple, RoleClass  # noqa: E402
from titer.corpus.tasks import Task, band_distribution  # noqa: E402
from titer.corpus.title_map import TitleClass, classify  # noqa: E402
from titer.costs.profiles import REPORTABLE, accuracy, expected_loss  # noqa: E402
from titer.metrics.intervals import wilson  # noqa: E402
from titer.metrics.survival import binned_rates, pava  # noqa: E402
from titer.oracle.outcome import Answer, Outcome, atoms, judge  # noqa: E402
from titer.oracle.resolve import resolve, resolve_issuer  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
TASKS = ROOT / "data" / "tasks.jsonl"
RINDEX = ROOT / "data" / "resolve_index.json"
RESULTS = ROOT / "results"


def load_tasks() -> list[Task]:
    """Read the materialised task set. Built once by scripts/build_tasks.py -
    loading 4.2M corpus rows per run costs gigabytes and buys nothing."""
    if not TASKS.exists():
        raise SystemExit(f"{TASKS} not found. Run scripts/build_tasks.py first.")
    out = []
    with TASKS.open() as fh:
        for line in fh:
            d = json.loads(line)
            out.append(Task(
                person_name_raw=d["person_name_raw"],
                anchor_issuer_cik=d["anchor_issuer_cik"],
                anchor_issuer_name=d["anchor_issuer_name"],
                anchor_title_class=TitleClass(d["anchor_title_class"]),
                anchor_date=date.fromisoformat(d["anchor_date"]),
                target_date=date.fromisoformat(d["target_date"]),
                person_cik=d["person_cik"],
                truth_issuer_cik=d["truth_issuer_cik"],
                truth_issuer_name=d["truth_issuer_name"],
                truth_title_class=TitleClass(d["truth_title_class"]),
                truth_period=date.fromisoformat(d["truth_period"]),
                truth_filed=date.fromisoformat(d["truth_filed"]),
                truth_accession=d["truth_accession"],
                collision_degree=d["collision_degree"],
                strict_degree=d.get("strict_degree", 1),
            ))
    return out


def load_indices():
    d = json.loads(RINDEX.read_text())
    index = CollisionIndex(
        ciks_by_name={k: set(v) for k, v in d["ciks_by_name"].items()},
        issuers_by_cik={k: set(v) for k, v in d["issuers_by_cik"].items()},
        ciks_by_presented={k: set(v) for k, v in d.get("ciks_by_presented", {}).items()},
    )
    issuer_index = {k: set(v) for k, v in d["ciks_by_company"].items()}
    return index, issuer_index


def build_arms(spend: bool):
    arms = {}
    try:
        arms["ploid"] = (Ploid(transport=ploid_transport() if spend else None), "search_fast")
    except RuntimeError as e:
        print(f"  ploid unavailable: {e}", file=sys.stderr)
    try:
        arms["exa"] = (Exa(transport=exa_transport() if spend else None), "answer")
        arms["webfloor"] = (Exa(transport=exa_transport() if spend else None), "search")
    except RuntimeError as e:
        print(f"  exa unavailable: {e}", file=sys.stderr)
    return arms


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spend", action="store_true")
    ap.add_argument("--n", type=int, default=40, help="matched n across arms")
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--budget-usd", type=float, default=1.0, help="per provider")
    ap.add_argument("--strategy", choices=("random", "stratified"), default="random",
                    help="random for R1 (a claim about the population); "
                         "stratified for R2 (colliding names are 15%% of movers "
                         "and simple random sampling finds almost none)")
    args = ap.parse_args()

    print("loading task set and resolution index...", flush=True)
    tasks = load_tasks()
    index, issuer_index = load_indices()
    print(f"  {len(tasks):,} tasks; bands {band_distribution(tasks)}")

    rng = random.Random(args.seed)
    if args.strategy == "random":
        sample = rng.sample(tasks, min(args.n, len(tasks)))
        strata = None
    else:
        # Equal allocation across bands, so the hard cells are actually
        # populated. Strata are reported SEPARATELY and never pooled into a
        # marginal rate - a pooled figure over a deliberately unrepresentative
        # sample would misstate the population. See docs/DECISIONS.md D027.
        by_band: dict[str, list] = {}
        for t_ in tasks:
            by_band.setdefault(t_.collision_band, []).append(t_)
        present = [b for b in ("unique", "low", "medium", "high") if by_band.get(b)]
        per = max(1, args.n // max(len(present), 1))
        sample, strata = [], {}
        for b in present:
            pick = rng.sample(by_band[b], min(per, len(by_band[b])))
            strata[b] = {"available": len(by_band[b]), "sampled": len(pick)}
            sample.extend(pick)
        rng.shuffle(sample)
    print(f"  strategy={args.strategy}, sampled {len(sample)} tasks, seed {args.seed}")
    if strata:
        print(f"  strata: {strata}")

    window = datetime.now().strftime("%Y-%m")
    as_of = date.today()
    cache = ReplayCache(ROOT / "data" / "replay.jsonl")
    arms = build_arms(args.spend)
    ledgers = {k: Ledger(args.budget_usd) for k in arms}
    records: dict[str, list[dict]] = {k: [] for k in arms}

    for i, task in enumerate(sample, 1):
        for arm, (adapter, action) in arms.items():
            rendered = adapter.render(task)
            key = CacheKey(arm, action, f"{task.task_id}|{rendered}", window)
            entry = cache.get(key)
            if entry is None:
                if not args.spend:
                    continue
                try:
                    answers, sp = adapter.query(action, rendered)
                except (ProviderHTTPError, Exception) as e:  # noqa: BLE001
                    print(f"  [{i}] {arm}: {type(e).__name__}: {str(e)[:120]}", file=sys.stderr)
                    continue
                try:
                    ledgers[arm].charge(sp)
                except BudgetExceeded as e:
                    print(f"  [{i}] {arm} budget exhausted: {e}", file=sys.stderr)
                    continue
                entry = cache.put(key, answers, sp, 0.0, datetime.now().isoformat())
            got = ReplayCache.to_answers(entry)
            top = got[0] if got else None
            emp_cik = resolve_issuer(top.employer_name if top else None, issuer_index)
            res = resolve(top.person_name if top else None, emp_cik, index,
                          anchor_issuer_cik=task.anchor_issuer_cik)
            ans = Answer(person_cik=res.person_cik,
                         confidence=top.confidence if top else 0.0,
                         employer_cik=emp_cik,
                         title_class=classify(top.title_text) if top and top.title_text else None)
            truth = AttestedTuple(
                accession=task.truth_accession, person_cik=task.person_cik,
                person_name_raw=task.person_name_raw, issuer_cik=task.truth_issuer_cik,
                issuer_name_raw=task.truth_issuer_name, issuer_ticker="",
                role_class=frozenset({RoleClass.OFFICER}), title_raw="",
                title_class=task.truth_title_class, period=task.truth_period,
                filed=task.truth_filed)
            outcome = judge(ans, truth)
            records[arm].append({
                "task_id": task.task_id, "outcome": outcome.value,
                "atoms": atoms(ans, truth,
                               identity_scored=res.independent_of_employer).total,
                "band": task.collision_band, "degree": task.collision_degree,
                "elapsed_days": task.elapsed_days(as_of),
                "resolution_reason": res.reason,
                "confidence": ans.confidence, "spend_usd": entry.spend_usd,
            })
        if i % 10 == 0:
            print(f"  [{i}/{len(sample)}] spend so far: "
                  + ", ".join(f"{k}=${v.spent.usd:.3f}" for k, v in ledgers.items()),
                  flush=True)

    report = {"window": window, "as_of": as_of.isoformat(), "seed": args.seed,
              "requested_n": args.n, "dry_run": not args.spend,
              "strategy": args.strategy, "strata": strata,
              "pooling_rule": (
                  "STRATIFIED: per-band rates only. A pooled marginal rate over "
                  "this sample would misstate the population and must not be "
                  "reported." if strata else
                  "RANDOM: marginal rates are population estimates."),
              "corpus": json.loads((RESULTS / "task_stats.json").read_text())
              if (RESULTS / "task_stats.json").exists() else {},
              "arms": {}}
    matched = min((len(v) for v in records.values() if v), default=0)
    report["matched_n"] = matched
    for arm, recs in records.items():
        if not recs:
            report["arms"][arm] = {"n": 0, "note": "no observations"}
            continue
        outs = [Outcome(r["outcome"]) for r in recs]
        n = len(outs)
        report["arms"][arm] = {
            "n": n,
            "spend_usd": round(sum(r["spend_usd"] for r in recs), 4),
            "outcomes": {o.value: sum(1 for x in outs if x is o) for o in Outcome},
            "accuracy": accuracy(outs),
            "correct": str(wilson(sum(1 for o in outs if o is Outcome.CORRECT), n)),
            "false_merge": str(wilson(sum(1 for o in outs if o is Outcome.FALSE_MERGE), n)),
            "stale": str(wilson(sum(1 for o in outs if o is Outcome.STALE), n)),
            "expected_loss": {p: expected_loss(outs, prof)
                              for p, prof in REPORTABLE.items()},
            "mean_atoms": sum(r["atoms"] for r in recs) / n,
            "reflection_by_elapsed": [
                (lab, str(iv)) for lab, iv in binned_rates(
                    [(r["elapsed_days"], Outcome(r["outcome"]) is Outcome.CORRECT)
                     for r in recs])],
            "median_reflection_lag_days": pava(
                [(r["elapsed_days"], Outcome(r["outcome"]) is Outcome.CORRECT)
                 for r in recs]).median_lag(),
            "by_band": {b: {"n": sum(1 for r in recs if r["band"] == b),
                            "false_merge": sum(1 for r in recs if r["band"] == b
                                               and r["outcome"] == "FALSE_MERGE")}
                        for b in ("unique", "low", "medium", "high")},
            "resolution_reasons": {rr: sum(1 for r in recs if r["resolution_reason"] == rr)
                                   for rr in {r["resolution_reason"] for r in recs}},
        }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / "full_run.json").write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps(report, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
