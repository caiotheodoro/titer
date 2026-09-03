#!/usr/bin/env python3
"""Repository gates. A nonzero exit code is the product.

Run via `make validate`. Every gate here is a test, not a diagnostic.
"""
from __future__ import annotations

import hashlib
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FAILURES: list[str] = []


def fail(gate: str, msg: str) -> None:
    FAILURES.append(f"[{gate}] {msg}")


def tracked_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=False
    )
    return [ROOT / p for p in out.stdout.split() if p]


SPINE = [
    "README.md", "AGENTS.md", "CONTRACTS.md", "llms.txt", "LICENSE",
    "MEASUREMENT_CARD.json", "pyproject.toml",
    "docs/ARCHITECTURE.md", "docs/BENCHMARK.md", "docs/COVERAGE.md",
    "docs/DATASET_CARD.md", "docs/DECISIONS.md", "docs/ETHICS.md",
    "docs/EVALS_CARD.md", "docs/HANDOFF.md", "docs/LINEAGE.md",
    "docs/METHOD.md", "docs/MODEL_CARD.md", "docs/PRE-REGISTRATION.md",
    "docs/PRE-REGISTRATION-EXPERTISE.md",
    "docs/RED-TEAM.md", "docs/REPRODUCTION.md", "docs/RETRACTIONS.md",
    "docs/RUBRIC.md", "docs/SURVEY.md", "docs/WAVES.md", "docs/methodology.md",
]


def gate_spine() -> None:
    for rel in SPINE:
        if not (ROOT / rel).is_file():
            fail("spine", f"missing {rel}")


EMAIL = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE = re.compile(r"(?<!\d)(?:\+?\d{1,2}[ .-]?)?\(?\d{3}\)?[ .-]\d{3}[ .-]\d{4}(?!\d)")
FORBIDDEN_PATH = re.compile(r"(^|/)(docs/private|\.cache|cache)(/|$)")
SCAN_EXT = {".md", ".txt", ".json", ".py", ".toml", ".csv", ".tsv", ".jsonl"}
# Placeholders that are documentation of a format, not a real contact.
ALLOW_EMAIL = {"AdminContact@example.com", "you@example.com"}


def gate_privacy() -> None:
    """Contact fields must never reach a tracked file. Enforced, not asserted."""
    for path in tracked_files():
        rel = path.relative_to(ROOT).as_posix()
        if FORBIDDEN_PATH.search(rel):
            fail("privacy", f"{rel} is tracked but must never be committed")
        if path.suffix not in SCAN_EXT or not path.is_file():
            continue
        text = path.read_text(errors="replace")
        for m in EMAIL.findall(text):
            if m not in ALLOW_EMAIL:
                fail("privacy", f"{rel} contains an email-shaped string: {m}")
        for m in PHONE.findall(text):
            fail("privacy", f"{rel} contains a phone-shaped string: {m}")


CITED = re.compile(r"`([^`\n]+)`")
LINKED = re.compile(r"\]\(([^)\s]+)\)")


def _declared(filename: str) -> set[str]:
    f = ROOT / filename
    if not f.is_file():
        return set()
    out = set()
    for line in f.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.add(line.split()[0])
    return out


def planned() -> set[str]:
    """Paths promised by a later wave, plus paths in sibling repositories."""
    return _declared("PLANNED-PATHS.txt") | _declared("EXTERNAL-PATHS.txt")


def gate_cited_paths() -> None:
    """Every cited path with a directory component must resolve, or be declared
    in PLANNED-PATHS.txt with the wave that creates it."""
    allow = planned()
    docs = [ROOT / p for p in SPINE if p.endswith((".md", ".txt"))]
    for doc in docs:
        text = doc.read_text()
        cands = set(CITED.findall(text)) | set(LINKED.findall(text))
        for c in cands:
            c = c.strip()
            if c.startswith(("http://", "https://", "#", "/", "./")):
                continue  # URLs, anchors, and API endpoint paths are not repo paths
            if "/" not in c or " " in c:
                continue
            if not re.match(r"^[\w./-]+$", c):
                continue
            # A repo path either names a directory (trailing /) or a file (has a
            # suffix). "reset/step/state" is a protocol triple, not a path.
            if not (c.endswith("/") or Path(c).suffix):
                continue
            if c in allow or c.rstrip("/") + "/" in allow:
                continue
            if not (ROOT / c).exists():
                fail("cited-path", f"{doc.relative_to(ROOT)} cites {c!r} which does not exist "
                                   f"and is not declared in PLANNED-PATHS.txt")


PLACEHOLDER = re.compile(r"\b(TBD|TODO|FIXME|XXX)\b")


def gate_no_placeholders() -> None:
    """Unknowns are named open questions with a resolving trigger, never TBDs."""
    for rel in SPINE:
        p = ROOT / rel
        if p.suffix not in {".md", ".txt"}:
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if PLACEHOLDER.search(line):
                fail("placeholder", f"{rel}:{i} contains a placeholder token")


PREREGS = ["docs/PRE-REGISTRATION.md", "docs/PRE-REGISTRATION-EXPERTISE.md"]


def gate_prereg_frozen() -> None:
    """Every pre-registration hash is recorded once and never changes silently.

    Both are gated. A second study does not get a softer rule than the first,
    and adding one must not create a document that is frozen in name only.
    """
    for rel in PREREGS:
        prereg = ROOT / rel
        if not prereg.is_file():
            fail("prereg", f"{rel} is listed as a pre-registration but does not exist")
            continue
        lock = prereg.with_suffix(".sha256")
        digest = hashlib.sha256(prereg.read_bytes()).hexdigest()
        if not lock.is_file():
            lock.write_text(digest + "\n")
            print(f"  {rel} frozen at {digest[:16]}...")
            continue
        recorded = lock.read_text().strip()
        if recorded != digest:
            fail("prereg", f"{rel} changed after freeze. It is never edited; supersede it "
                           "with a dated DECISIONS entry carrying a reversal clause. "
                           f"recorded={recorded[:16]}... actual={digest[:16]}...")


def gate_card_honest() -> None:
    """A card that always exits zero is decoration."""
    import json
    card = json.loads((ROOT / "MEASUREMENT_CARD.json").read_text())
    if card["verdict"] == "VERIFIED" and card.get("unmet_claims"):
        fail("card", "verdict is VERIFIED while unmet_claims is non-empty")
    if card["verdict"] == "NOT_VERIFIED" and not card.get("unmet_claims"):
        fail("card", "verdict is NOT_VERIFIED but no unmet claim is named")


def main() -> int:
    for gate in (gate_spine, gate_privacy, gate_cited_paths,
                 gate_no_placeholders, gate_prereg_frozen, gate_card_honest):
        gate()
    if FAILURES:
        print(f"FAILED {len(FAILURES)} check(s):\n", file=sys.stderr)
        for f in FAILURES:
            print("  " + f, file=sys.stderr)
        return 1
    print("validate: all gates green")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
