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

**Scoring resolves to an ID, never a string** (D038). Each population is
resolved against the registry IT attests: an SEC employer to a CIK via
`resolve_issuer`, a scholar affiliation to an OpenAlex institution id, with that
registry's own hierarchy allowed. The method is symmetric even though the
registries differ. A normalised string match was tried first and rejected: truth
`Manipal Academy of Higher Education` against a returned `Kasturba Medical
College, Manipal University` scored WRONG, and the college is inside the
academy.

**Two asymmetries remain, and neither is fixed by the scorer.**

1. **The oracles differ in strength.** SEC truth is a filing an officer signed.
   Scholar truth is OpenAlex `last_known_institutions`, derived from publication
   affiliations, which lags a move. A gap is (index coverage x oracle
   freshness) and cannot be split without a second scholarly oracle.
2. **Only one registry publishes hierarchy.** OpenAlex gives an explicit
   `lineage`, so a scholar named at a sub-unit of the right body counts correct.
   EDGAR publishes no parent/subsidiary lineage, so an executive named at a
   subsidiary of the right issuer counts WRONG. That asymmetry favours the
   scholar arm, and it is stated rather than corrected.
"""
from __future__ import annotations

import argparse
import json
import os
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
from titer.corpus.name_norm import presented_query_name
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
                    "truth": r["truth_issuer_name"],
                    "truth_cik": r["truth_issuer_cik"]})
    return out


def matches_sec(returned: str | None, truth_cik: str, issuer_index) -> bool:
    """Resolve the returned employer to a CIK and compare. No model, no fuzz."""
    from titer.oracle.resolve import resolve_issuer
    if not returned:
        return False
    return resolve_issuer(returned, issuer_index) == truth_cik


#: Institution resolutions, persisted. Without this every run started from
#: nothing, so a run that got 203 of 250 scholar rows scored and then hit the
#: OpenAlex wall threw all 203 lookups away, and the next run re-bought them
#: from a budget that was already gone. Now each run keeps what it resolved and
#: the next one continues, which is the same checkpoint discipline the A12
#: audit needed for the same reason.
_INST_PATH = ROOT / "data" / "institution_cache.json"
_INST_CACHE: dict = (json.loads(_INST_PATH.read_text())
                     if _INST_PATH.is_file() else {})


def _save_inst_cache() -> None:
    _INST_PATH.write_text(json.dumps(_INST_CACHE, indent=0, sort_keys=True))


def matches_scholar(returned: str | None, truth: str, ua: str) -> bool | None:
    """Resolve both to OpenAlex institution ids, allowing lineage containment.

    Returns None when OpenAlex cannot be reached, so a quota wall costs the
    SCORE and never the Exa spend: the provider responses are already cached
    and re-score for free. An earlier version raised, and the whole run died on
    its first scholar row.

    Institution lookups are memoised - the same handful of large institutions
    recur constantly across a scholar sample.
    """
    from titer.corpus.scholar import OpenAlexError, resolve_institution

    def look(name):
        key = name or ""
        if key not in _INST_CACHE:
            rid, lin = resolve_institution(name, ua)
            _INST_CACHE[key] = [rid, lin]
            if len(_INST_CACHE) % 20 == 0:
                _save_inst_cache()
        v = _INST_CACHE[key]
        return (v[0], v[1]) if isinstance(v, list) else v

    try:
        rid, rlin = look(returned)
        if rid is None:
            return False
        tid, tlin = look(truth)
        if tid is None:
            return False
        return rid == tid or tid in rlin or rid in tlin
    except OpenAlexError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spend", action="store_true")
    ap.add_argument("--n", type=int, default=250, help="per population")
    ap.add_argument("--seed", type=int, default=23)
    ap.add_argument("--budget-usd", type=float, default=3.0)
    ap.add_argument("--max-calls", type=int, default=520)
    ap.add_argument("--out", default="e4_coverage.json")
    args = ap.parse_args()

    from titer.corpus.scholar import user_agent
    from titer.oracle.resolve import build_issuer_index  # noqa: F401
    ua = user_agent(os.environ.get("TITER_OPENALEX_MAILTO", "titer-audit"))
    idx = json.loads((ROOT / "data" / "resolve_index.json").read_text())
    issuer_index = {k: set(v) for k, v in idx["ciks_by_company"].items()}

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
        correct = (matches_sec(emp, t["truth_cik"], issuer_index)
                   if t["population"] == "sec"
                   else matches_scholar(emp, t["truth"], ua))
        recs.append({"population": t["population"], "task_id": t["task_id"],
                     "returned": emp, "truth": t["truth"],
                     "named_someone": bool(emp),
                     "correct": correct,
                     "confidence": top.confidence if top else 0.0,
                     "spend_usd": entry.spend_usd})
        if i % 50 == 0:
            print(f"  {i}/{len(tasks)}  live={live}  spend=${ledger.spent.usd:.2f}",
                  flush=True)

    report = {"generated": datetime.now().date().isoformat(),
              "instrument": "name-only; identical string for both populations",
              "scoring": ("resolved to an ID, not a string: SEC employer -> CIK; "
                          "scholar affiliation -> OpenAlex institution id with "
                          "lineage containment. Only OpenAlex publishes "
                          "hierarchy, which favours the scholar arm."),
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
        scored = [r for r in rs if r["correct"] is not None]
        n, ns = len(rs), len(scored)
        report["populations"][pop] = {
            "n_returned": n,
            "n_scored": ns,
            "unscored_openalex_unavailable": n - ns,
            "named_someone": str(wilson(sum(r["named_someone"] for r in rs), n)),
            "correct": str(wilson(sum(r["correct"] for r in scored), ns)) if ns else None,
            "correct_rate": round(sum(r["correct"] for r in scored) / ns, 4) if ns else None,
        }
    # Unpaired: the two populations are different people, so the difference is
    # a between-population contrast, not a within-task one. Resampling each arm
    # independently is correct HERE and would be wrong for E2, where the arms
    # see the identical tasks and the pairing is what buys the precision.
    # A verdict needs an arm, not a token. The first version of this guard only
    # checked n_scored was non-zero, and on a run where OpenAlex scored 2 of 250
    # scholar rows it emitted "E4 SUPPORTED: the interval excludes zero" from a
    # 250-versus-2 comparison. A confident verdict computed from nothing is the
    # defect this repository is about, so the floor is explicit.
    MIN_SCORED = 100
    pops = report["populations"]
    thin = {k: v.get("n_scored", 0) for k, v in pops.items()
            if (v.get("n_scored") or 0) < MIN_SCORED}
    if thin:
        report["difference_scholar_minus_sec"] = {
            "verdict": "NO VERDICT",
            "reason": (f"arms scored too thin for a between-population claim: "
                       f"{thin}, minimum {MIN_SCORED}. Scoring the scholar arm "
                       f"needs OpenAlex; re-run when its budget resets. The "
                       f"provider responses are cached, so it costs $0."),
            "scored": {k: v.get("n_scored") for k, v in pops.items()}}
    elif len(pops) == 2:
        import statistics as _st
        rng2 = random.Random(11)
        arms = {}
        for pop in ("sec", "scholar"):
            rs = [r for r in recs if r["population"] == pop and r["correct"] is not None]
            arms[pop] = [1.0 if r["correct"] else 0.0 for r in rs]
        diffs = []
        for _ in range(10_000):
            d = []
            for pop in ("scholar", "sec"):
                v = arms[pop]
                d.append(_st.fmean([v[rng2.randrange(len(v))] for _ in range(len(v))]))
            diffs.append(d[0] - d[1])
        diffs.sort()
        lo, hi = diffs[250], diffs[9750]
        point = _st.fmean(arms["scholar"]) - _st.fmean(arms["sec"])
        report["difference_scholar_minus_sec"] = {
            "point": round(point, 4), "ci": [round(lo, 4), round(hi, 4)],
            "resamples": 10_000, "seed": 11,
            "contains_zero": bool(lo <= 0.0 <= hi),
            "verdict": ("E4 FALSIFIED: the difference interval contains zero, so "
                        "the same provider resolves the two populations at rates "
                        "this design cannot distinguish."
                        if lo <= 0.0 <= hi else
                        "E4 SUPPORTED: the interval excludes zero.")}
    _save_inst_cache()
    (ROOT / "results" / args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report["populations"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
