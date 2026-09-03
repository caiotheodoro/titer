#!/usr/bin/env python3
"""Build E1 expertise-verification tasks from the scholar corpus.

Each author yields a balanced pair: one ATTESTED claim (a topic they have
published in, >= MIN_WORKS_IN_TOPIC works) and one CONSTRUCTED_FALSE claim (a
topic they have provably never published in, drawn mechanically from the
OpenAlex hierarchy at a stated difficulty tier).

Balance is by construction, not by sampling luck, and the negative tier is
recorded per task so NEAR and FAR are never pooled (D031).
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import os
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.corpus.name_norm import normalize_presented  # noqa: E402
from titer.corpus.scholar import (FAR, NEAR, AttestedTopic,  # noqa: E402
                                  Author, adjacent_false_topic, fetch_topics,
                                  user_agent)

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "scholar.jsonl"
OUT = ROOT / "data" / "expert_tasks.jsonl"

ATTESTED, FALSE = "ATTESTED", "CONSTRUCTED_FALSE"


def load_authors():
    with CORPUS.open() as fh:
        for line in fh:
            d = json.loads(line)
            yield d, Author(
                author_id=d["author_id"], orcid=d["orcid"],
                display_name=d["display_name"], works_count=d["works_count"],
                institution=d["institution"],
                attested=tuple(AttestedTopic(t["topic_id"], t["label"], t["n_works"],
                                             t["subfield"], t["field"], t["domain"])
                               for t in d["attested"]))


def prompt(name: str, institution: str, topic: str) -> str:
    """The claim put to a provider. Discloses name, institution and topic; the
    scored fact - whether the person has published in it - is withheld."""
    return (f"Does {name}, affiliated with {institution}, have published "
            f"research expertise in {topic}?")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--mailto", default=os.environ.get("TITER_OPENALEX_MAILTO", ""))
    args = ap.parse_args()
    if not CORPUS.exists():
        raise SystemExit(f"{CORPUS} not found. Run scripts/build_scholar_corpus.py first.")

    topics = fetch_topics(user_agent(args.mailto))
    rng = random.Random(args.seed)

    # Collision degree over the corpus. D032: this is SAMPLE-relative and
    # under-counts the real world; E2 builds its colliding set by search.
    by_name: dict[str, set[str]] = collections.defaultdict(set)
    for d, _ in load_authors():
        k = normalize_presented(d["display_name"])
        if k:
            by_name[k].add(d["author_id"])

    n_written = 0
    tiers: collections.Counter = collections.Counter()
    pol: collections.Counter = collections.Counter()
    no_negative = 0

    with OUT.open("w") as out:
        for d, a in load_authors():
            top = max(a.attested, key=lambda t: t.n_works)
            # Tier is assigned per author by seed, 50/50. Always asking for NEAR
            # and falling back produced 19,978 NEAR against 22 FAR - the easy
            # control tier had no n at all, and its entire purpose (D031) is to
            # show the difficulty axis is doing work. Polarity stays balanced
            # 50/50 because each author still yields exactly one of each.
            want = NEAR if rng.random() < 0.5 else FAR
            got = adjacent_false_topic(a, topics, rng, want)
            if got is None:
                no_negative += 1
                continue
            false_topic, tier = got
            degree = len(by_name.get(normalize_presented(a.display_name), {a.author_id}))

            for polarity, t_id, t_label, t_field, t_sub, nw, ntier in (
                (ATTESTED, top.topic_id, top.label, top.field, top.subfield,
                 top.n_works, None),
                (FALSE, false_topic.id, false_topic.display_name, false_topic.field,
                 false_topic.subfield, 0, tier),
            ):
                task_id = hashlib.sha256(
                    f"{a.author_id}|{t_id}|{polarity}".encode()).hexdigest()[:16]
                out.write(json.dumps({
                    "task_id": task_id, "author_id": a.author_id, "orcid": a.orcid,
                    "display_name": a.display_name, "institution": a.institution,
                    "topic_id": t_id, "topic_label": t_label,
                    "topic_field": t_field, "topic_subfield": t_sub,
                    "polarity": polarity, "negative_tier": ntier,
                    "n_works_in_topic": nw,
                    "collision_degree": degree,
                    "prompt": prompt(a.display_name, a.institution, t_label),
                }) + "\n")
                n_written += 1
                pol[polarity] += 1
                if ntier:
                    tiers[ntier] += 1

    stats = {"tasks": n_written, "authors_used": n_written // 2,
             "authors_without_a_negative": no_negative,
             "polarity": dict(pol), "negative_tiers": dict(tiers),
             "balanced": pol[ATTESTED] == pol[FALSE],
             "collision_note": "sample-relative; see docs/DECISIONS.md D032"}
    (ROOT / "results" / "expert_task_stats.json").write_text(
        json.dumps(stats, indent=2) + "\n")
    print(json.dumps(stats, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
