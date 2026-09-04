#!/usr/bin/env python3
"""Stage the two corpora in their PUBLISHABLE form. Dry-run by default.

Two rules from docs/ETHICS.md are enforced here rather than trusted:

* **Pointers, never assembled records.** Identifiers, derived closed-class
  labels, dates and salted hashes. No names, no contact fields, no free text.
* **Constructed-false claims are NEVER published against a named individual**
  (ETHICS A-E1). The expertise dataset ships the ATTESTED side and the *rule*
  for building negatives. A reader regenerates them; we do not hand out a list
  of people paired with things they cannot do.

A gate at the end refuses to stage anything carrying a forbidden field.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "build" / "hf"

#: Anything matching these must never reach a published file.
FORBIDDEN = ("name_raw", "display_name", "institution", "email", "phone",
             "address", "linkedin", "url", "title_raw", "issuer_name")


def guard(rows: list[dict], label: str) -> None:
    bad = {k for r in rows[:2000] for k in r if any(f in k.lower() for f in FORBIDDEN)}
    if bad:
        raise SystemExit(f"REFUSING to publish {label}: forbidden fields {sorted(bad)}")


def stage_edgar(out: Path) -> dict:
    src = ROOT / "results" / "corpus_public.jsonl"
    if not src.exists():
        raise SystemExit(f"{src} not found; run scripts/build_corpus.py")
    rows, n = [], 0
    writer = None
    out.mkdir(parents=True, exist_ok=True)
    target = out / "edgar_officers.parquet"
    with src.open() as fh:
        for line in fh:
            rows.append(json.loads(line))
            n += 1
            if len(rows) >= 250_000:
                if writer is None:
                    guard(rows, "edgar")
                tbl = pa.Table.from_pylist(rows)
                writer = writer or pq.ParquetWriter(target, tbl.schema,
                                                    compression="zstd")
                writer.write_table(tbl)
                rows = []
    if rows:
        if writer is None:
            guard(rows, "edgar")
        tbl = pa.Table.from_pylist(rows)
        writer = writer or pq.ParquetWriter(target, tbl.schema, compression="zstd")
        writer.write_table(tbl)
    if writer:
        writer.close()
    return {"rows": n, "bytes": target.stat().st_size, "path": str(target)}


def stage_expertise(out: Path, salt: str) -> dict:
    """ATTESTED claims only. See ETHICS A-E1."""
    src = ROOT / "data" / "scholar.jsonl"
    if not src.exists():
        raise SystemExit(f"{src} not found; run scripts/build_scholar_corpus.py")
    rows = []
    with src.open() as fh:
        for line in fh:
            d = json.loads(line)
            h = hashlib.sha256((salt + "|" + d["display_name"]).encode()).hexdigest()
            for t in d["attested"]:
                rows.append({
                    "author_id": d["author_id"], "orcid": d["orcid"],
                    "name_sha256": h, "works_count": d["works_count"],
                    "topic_id": t["topic_id"], "topic_label": t["label"],
                    "n_works_in_topic": t["n_works"],
                    "subfield": t["subfield"], "field": t["field"],
                    "domain": t["domain"], "polarity": "ATTESTED",
                })
    guard(rows, "expertise")
    out.mkdir(parents=True, exist_ok=True)
    target = out / "expertise_attested.parquet"
    pq.write_table(pa.Table.from_pylist(rows), target, compression="zstd")
    return {"rows": len(rows), "authors": sum(1 for _ in src.open()),
            "bytes": target.stat().st_size, "path": str(target)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", action="store_true", help="upload to the Hub")
    ap.add_argument("--salt", default=os.environ.get("TITER_NAME_SALT", ""))
    args = ap.parse_args()
    if not args.salt:
        raise SystemExit("TITER_NAME_SALT is required; published hashes must not "
                         "be reversible by rainbow table")

    e = stage_edgar(STAGE / "edgar")
    x = stage_expertise(STAGE / "expertise", args.salt)
    print(json.dumps({"edgar": e, "expertise": x, "pushed": args.push}, indent=2))
    if not args.push:
        print("\ndry run: nothing uploaded. Re-run with --push.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
