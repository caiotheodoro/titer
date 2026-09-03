#!/usr/bin/env python3
"""Build the Tier A corpus from SEC Forms 3/4/5.

Writes three artifacts:

  data/corpus.jsonl          full rows, gitignored - names are needed to query
                             providers, and are never published
  results/corpus_public.jsonl the pointer form that IS published: accession,
                             CIKs, classes, dates, collision degree, name hash
  results/corpus_stats.json  exclusion counters, collision distribution and the
                             same-human-two-CIK contamination bound

Usage:
  export TITER_SEC_UA='titer-research <handle>@users.noreply.github.com'
  uv run python scripts/build_corpus.py --quarters 2003q3..2026q2
  uv run python scripts/build_corpus.py --list          # discover only, no download
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.corpus.build import build_quarter  # noqa: E402
from titer.corpus.collision import band, build_index  # noqa: E402
from titer.corpus.fetch import SecAccessError, discover_quarters, download  # noqa: E402
from titer.corpus.schema import ExclusionCounts  # noqa: E402
from titer.corpus.splits import duplication_rates  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
RESULTS = ROOT / "results"
_RANGE = re.compile(r"^(\d{4})q([1-4])\.\.(\d{4})q([1-4])$")


def parse_range(spec: str):
    m = _RANGE.match(spec)
    if not m:
        raise SystemExit(f"bad --quarters {spec!r}; expected e.g. 2003q3..2026q2")
    lo = (int(m.group(1)), int(m.group(2)))
    hi = (int(m.group(3)), int(m.group(4)))
    return lo, hi


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quarters", default="2003q3..2026q4")
    ap.add_argument("--list", action="store_true", help="discover quarters, download nothing")
    ap.add_argument("--salt", default=os.environ.get("TITER_NAME_SALT", ""))
    args = ap.parse_args()

    if not args.salt and not args.list:
        raise SystemExit(
            "Refusing to run without a name salt. Published name hashes must not be\n"
            "reversible by rainbow table. Set TITER_NAME_SALT or pass --salt."
        )

    try:
        quarters = discover_quarters()
    except SecAccessError as e:
        print(f"\n{e}\n", file=sys.stderr)
        return 2

    lo, hi = parse_range(args.quarters)
    selected = [q for q in quarters if lo <= (q.year, q.quarter) <= hi]
    print(f"discovered {len(quarters)} quarters on the landing page "
          f"({quarters[0].key} .. {quarters[-1].key}); {len(selected)} in range")
    if args.list:
        for q in quarters:
            print(" ", q.key, q.url)
        return 0

    counts = ExclusionCounts()
    rows = []
    for i, q in enumerate(selected, 1):
        try:
            path = download(q, DATA / "raw")
        except SecAccessError as e:
            print(f"\n{e}\n", file=sys.stderr)
            return 2
        got = build_quarter(path, counts)
        rows.extend(got)
        print(f"[{i}/{len(selected)}] {q.key}: +{len(got)} rows (total {len(rows)})", flush=True)

    counts.reconcile()
    idx = build_index(rows)

    DATA.mkdir(exist_ok=True)
    RESULTS.mkdir(exist_ok=True)
    with (DATA / "corpus.jsonl").open("w") as fh:
        for r in rows:
            fh.write(json.dumps({
                "accession": r.accession, "person_cik": r.person_cik,
                "person_name_raw": r.person_name_raw, "issuer_cik": r.issuer_cik,
                "issuer_name_raw": r.issuer_name_raw, "issuer_ticker": r.issuer_ticker,
                "role_class": sorted(x.value for x in r.role_class),
                "title_raw": r.title_raw, "title_class": r.title_class.value,
                "period": r.period.isoformat(), "filed": r.filed.isoformat(),
            }) + "\n")

    degrees = Counter()
    with (RESULTS / "corpus_public.jsonl").open("w") as fh:
        for r in rows:
            d = idx.presented_degree(r.person_name_raw)
            degrees[band(d)] += 1
            fh.write(json.dumps({
                "accession": r.accession, "person_cik": r.person_cik,
                "issuer_cik": r.issuer_cik, "issuer_ticker": r.issuer_ticker,
                "role_class": sorted(x.value for x in r.role_class),
                "title_class": r.title_class.value,
                "period": r.period.isoformat(), "filed": r.filed.isoformat(),
                "collision_degree": d, "collision_band": band(d),
                "strict_degree": idx.degree(r.person_name_norm),
                "name_sha256": r.name_hash(args.salt),
            }) + "\n")

    stats = {
        "contracts_version": "contracts/v1",
        "quarters": [q.key for q in selected],
        "rows": len(rows),
        "distinct_person_cik": len({r.person_cik for r in rows}),
        "distinct_issuer_cik": len({r.issuer_cik for r in rows}),
        "exclusions": counts.as_dict(),
        "title_unknown_rate": counts.title_unknown / max(counts.kept, 1),
        "collision_bands": dict(degrees),
        "contamination_bound": idx.contamination_bound(),
        **duplication_rates(rows),
    }
    (RESULTS / "corpus_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
