#!/usr/bin/env python3
"""Contamination probe over the built corpus.

Reads data/corpus.jsonl, splits by signature, and reports the leak rate in both
directions. A probe that cannot detect a deliberate leak is not evidence of a
clean split, so the deliberate-leak control runs every time.
"""
from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.corpus.schema import AttestedTuple, RoleClass  # noqa: E402
from titer.corpus.splits import leak_rate, near_duplicate_rate, split  # noqa: E402
from titer.corpus.title_map import TitleClass  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
CORPUS = ROOT / "data" / "corpus.jsonl"


def load() -> list[AttestedTuple]:
    if not CORPUS.exists():
        raise SystemExit(f"{CORPUS} not found. Run scripts/build_corpus.py first.")
    out = []
    with CORPUS.open() as fh:
        for line in fh:
            d = json.loads(line)
            out.append(AttestedTuple(
                accession=d["accession"], person_cik=d["person_cik"],
                person_name_raw=d["person_name_raw"], issuer_cik=d["issuer_cik"],
                issuer_name_raw=d["issuer_name_raw"], issuer_ticker=d["issuer_ticker"],
                role_class=frozenset(RoleClass(x) for x in d["role_class"]),
                title_raw=d["title_raw"], title_class=TitleClass(d["title_class"]),
                period=date.fromisoformat(d["period"]), filed=date.fromisoformat(d["filed"]),
            ))
    return out


def main() -> int:
    rows = load()
    s = split(rows, seed=11)
    counts = s.counts()
    if min(counts.values()) == 0:
        print(f"FAILED: a split bucket is empty {counts}; every probe below is vacuous",
              file=sys.stderr)
        return 1

    honest_test = leak_rate(s.train, s.test)
    honest_hill = leak_rate(s.train, s.hillclimb)
    control = leak_rate(s.train, s.train)   # deliberate leak, must read 1.0
    nd = near_duplicate_rate(rows)

    print(f"rows            {len(rows)}")
    print(f"splits          {counts}")
    print(f"leak train->test      {honest_test:.6f}   (must be 0.0)")
    print(f"leak train->hillclimb {honest_hill:.6f}   (must be 0.0)")
    print(f"control leak          {control:.6f}   (must be 1.0, proves the probe works)")
    print(f"near-duplicate rate   {nd:.6f}   (published, not assumed zero)")

    ok = honest_test == 0.0 and honest_hill == 0.0 and control == 1.0
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "leak_probe.json").write_text(json.dumps({
        "rows": len(rows), "splits": counts,
        "leak_train_to_test": honest_test, "leak_train_to_hillclimb": honest_hill,
        "control_leak": control, "near_duplicate_rate": nd, "pass": ok,
    }, indent=2) + "\n")
    if not ok:
        print("\nFAILED: contamination probe did not pass", file=sys.stderr)
        return 1
    print("\nleak_probe: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
