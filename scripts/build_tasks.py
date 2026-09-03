#!/usr/bin/env python3
"""Materialise the measurement task set once, streaming.

The corpus is 4.2M rows; loading it as dataclasses for every run costs gigabytes
and minutes. Tasks are one per person who moved (~46k), so they are built once
here and every later script reads data/tasks.jsonl instead.

Streaming also keeps the two normalizations honest: the collision index is built
from the whole corpus (a name's ambiguity is a property of the population, not
of the sample), while only light tuples are held per person.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.corpus.collision import band  # noqa: E402
from titer.corpus.name_norm import (normalize, normalize_company,  # noqa: E402
                                    normalize_presented)

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus.jsonl"
OUT = ROOT / "data" / "tasks.jsonl"
MIN_GAP_DAYS = 180


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min-gap-days", type=int, default=MIN_GAP_DAYS)
    ap.add_argument("--require-last-employer", action="store_true",
                    help="D028 C2: keep only tasks whose target IS the person's "
                         "last attested employer, so 'where are they now' is the "
                         "honest question for a current-state index")
    ap.add_argument("--max-age-years", type=float, default=None,
                    help="drop tasks whose last filing is older than this; the "
                         "corpus cannot see moves it never recorded")
    args = ap.parse_args()
    if not CORPUS.exists():
        raise SystemExit(f"{CORPUS} not found. Run scripts/build_corpus.py first.")

    by_presented: dict[str, set[str]] = collections.defaultdict(set)
    by_strict: dict[str, set[str]] = collections.defaultdict(set)
    hist: dict[str, list] = collections.defaultdict(list)
    names: dict[str, str] = {}
    issuer_name: dict[str, str] = {}
    issuers_by_cik: dict[str, set[str]] = collections.defaultdict(set)
    ciks_by_company: dict[str, set[str]] = collections.defaultdict(set)

    n = 0
    with CORPUS.open() as fh:
        for line in fh:
            d = json.loads(line)
            n += 1
            cik, raw = d["person_cik"], d["person_name_raw"]
            names[cik] = raw
            issuer_name[d["issuer_cik"]] = d["issuer_name_raw"]
            p, s = normalize_presented(raw), normalize(raw)
            if p:
                by_presented[p].add(cik)
            if s:
                by_strict[s].add(cik)
            issuers_by_cik[cik].add(d["issuer_cik"])
            cn = normalize_company(d["issuer_name_raw"])
            if cn:
                ciks_by_company[cn].add(d["issuer_cik"])
            hist[cik].append((d["period"], d["issuer_cik"], d["title_class"],
                              d["accession"], d["filed"]))
    print(f"streamed {n:,} rows, {len(hist):,} people", flush=True)

    written = 0
    bands: collections.Counter = collections.Counter()
    with OUT.open("w") as out:
        for cik, rows in hist.items():
            rows.sort()
            a_period, a_iss, a_title, a_acc, a_filed = rows[0]
            last_at_anchor = max(p for p, i, *_ in rows if i == a_iss)
            target = None
            for p, i, ti, acc, fl in rows[1:]:
                if i == a_iss or p <= last_at_anchor:
                    continue
                if (date.fromisoformat(p) - date.fromisoformat(a_period)).days < args.min_gap_days:
                    continue
                target = (p, i, ti, acc, fl)
                break
            if target is None:
                continue
            last_issuer = rows[-1][1]
            is_last = target[1] == last_issuer
            age_days = (date.today() - date.fromisoformat(rows[-1][4])).days
            if args.require_last_employer and not is_last:
                continue
            if args.max_age_years is not None and age_days > args.max_age_years * 365.25:
                continue
            raw = names[cik]
            deg = len(by_presented.get(normalize_presented(raw), ()))
            strict = len(by_strict.get(normalize(raw), ()))
            bands[band(deg)] += 1
            out.write(json.dumps({
                "person_cik": cik, "person_name_raw": raw,
                "anchor_issuer_cik": a_iss, "anchor_issuer_name": issuer_name.get(a_iss, ""),
                "anchor_title_class": a_title, "anchor_date": a_period,
                "target_date": target[0], "truth_issuer_cik": target[1],
                "truth_issuer_name": issuer_name.get(target[1], ""),
                "truth_title_class": target[2], "truth_accession": target[3],
                "truth_filed": target[4], "truth_period": target[0],
                "collision_degree": deg, "collision_band": band(deg),
                "strict_degree": strict,
                "target_is_last_employer": is_last,
                "last_filing_age_days": age_days,
            }) + "\n")
            written += 1

    # The resolution index, so later scripts never load 4.2M rows again.
    # Keyed on the STRICT normalization: resolution is the conservative side.
    (ROOT / "data" / "resolve_index.json").write_text(json.dumps({
        "ciks_by_name": {k: sorted(v) for k, v in by_strict.items()},
        "ciks_by_presented": {k: sorted(v) for k, v in by_presented.items()},
        "issuers_by_cik": {k: sorted(v) for k, v in issuers_by_cik.items()},
        "ciks_by_company": {k: sorted(v) for k, v in ciks_by_company.items()},
    }))
    print(f"wrote resolution index: {len(by_strict):,} names, "
          f"{len(ciks_by_company):,} company names", flush=True)

    stats = {"rows_streamed": n, "people": len(hist), "tasks": written,
             "retained_fraction": written / len(hist), "bands": dict(bands),
             "min_gap_days": args.min_gap_days,
             "require_last_employer": args.require_last_employer,
             "max_age_years": args.max_age_years}
    (ROOT / "results" / "task_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
