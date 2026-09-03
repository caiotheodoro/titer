#!/usr/bin/env python3
"""Build the Tier A expertise corpus from OpenAlex, with ORCID as identity spine.

Free: no API key, no spend. OpenAlex's polite pool wants a contact address in
the User-Agent (TITER_OPENALEX_MAILTO); anonymous use gets the slow shared pool.

Writes:
  data/scholar.jsonl          authors with their attested topics (gitignored)
  results/scholar_stats.json  exclusion counters, topic and domain distributions
"""
from __future__ import annotations

import argparse
import collections
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.corpus.scholar import (ADJACENCY_VERSION, OpenAlexError,  # noqa: E402
                                  ScholarCounts, fetch_topics, iter_authors,
                                  user_agent)

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--authors", type=int, default=20_000)
    ap.add_argument("--mailto", default=os.environ.get("TITER_OPENALEX_MAILTO", ""))
    args = ap.parse_args()

    try:
        ua = user_agent(args.mailto)
    except OpenAlexError as e:
        print(e, file=sys.stderr)
        return 2

    print("fetching the topic hierarchy...", flush=True)
    topics = fetch_topics(ua)
    doms = collections.Counter(t.domain for t in topics.values())
    print(f"  {len(topics):,} topics across {len(doms)} domains: {dict(doms)}")

    counts = ScholarCounts()
    (ROOT / "data").mkdir(exist_ok=True)
    out = ROOT / "data" / "scholar.jsonl"
    dom_hist: collections.Counter = collections.Counter()
    topics_per_author: list[int] = []

    with out.open("w") as fh:
        for i, a in enumerate(iter_authors(ua, counts, args.authors), 1):
            topics_per_author.append(len(a.attested))
            for t in a.attested:
                dom_hist[t.domain] += 1
            fh.write(json.dumps({
                "author_id": a.author_id, "orcid": a.orcid,
                "display_name": a.display_name, "works_count": a.works_count,
                "institution": a.institution,
                "attested": [{"topic_id": t.topic_id, "label": t.label,
                              "n_works": t.n_works, "subfield": t.subfield,
                              "field": t.field, "domain": t.domain}
                             for t in a.attested],
            }) + "\n")
            if i % 1000 == 0:
                print(f"  [{i}/{args.authors}] kept={counts.kept} "
                      f"dropped={counts.dropped}", flush=True)

    counts.reconcile()
    import statistics
    stats = {
        "contracts_version": "contracts/v1-expertise",
        "adjacency_version": ADJACENCY_VERSION,
        "topics_in_hierarchy": len(topics),
        "authors": counts.kept,
        "exclusions": counts.as_dict(),
        "attested_topics_per_author": {
            "median": statistics.median(topics_per_author) if topics_per_author else 0,
            "mean": round(statistics.fmean(topics_per_author), 2) if topics_per_author else 0,
        },
        "attested_topic_domain_distribution": dict(dom_hist),
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "scholar_stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
