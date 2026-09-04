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
    """Cited paths that are legitimately absent from a clean checkout.

    Three kinds, declared separately so the reason stays visible:
      PLANNED-PATHS    - promised by a later wave
      EXTERNAL-PATHS   - live in a sibling repository
      GITIGNORED-PATHS - generated locally and never committed

    The third was added after CI failed on a clean clone while the same gate
    passed locally, because the author's machine had the generated files. A
    gate that only passes where its author sits is not a gate.
    """
    return (_declared("PLANNED-PATHS.txt") | _declared("EXTERNAL-PATHS.txt")
            | _declared("GITIGNORED-PATHS.txt"))


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
# CITATION.cff shipped orcid: 0000-0000-0000-0000 to the public repo. The gate
# read only SPINE .md/.txt, so a fabricated identifier in a citation file was
# invisible to it. An all-zero identifier is a placeholder wearing a real
# format.
NULL_ID = re.compile(r"\b0000-0000-0000-000[0-9X]\b|\b10\.0000/\b")
PLACEHOLDER_FILES = SPINE + ["CITATION.cff"]


def gate_no_placeholders() -> None:
    """Unknowns are named open questions with a resolving trigger, never TBDs."""
    for rel in PLACEHOLDER_FILES:
        p = ROOT / rel
        if p.suffix not in {".md", ".txt", ".cff"} or not p.is_file():
            continue
        for i, line in enumerate(p.read_text().splitlines(), 1):
            if PLACEHOLDER.search(line):
                fail("placeholder", f"{rel}:{i} contains a placeholder token")
            if NULL_ID.search(line):
                fail("placeholder",
                     f"{rel}:{i} carries an all-zero identifier, which is a "
                     f"fabricated ORCID/DOI, not an absent one")


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


SUITE_RE = re.compile(r"(\d[\d,]*)\s+tests?\s+green", re.I)


def gate_advertised_suite_size() -> None:
    """A test count quoted in the docs must equal what pytest actually collects.

    Ported from assay. The point is that ADDING A TEST REDDENS THE BUILD on
    purpose: a suite size is a claim like any other, and a stale one is a claim
    that quietly stopped being true. Without this, "238 tests green" could sit
    in a README forever while the suite drifted.
    """
    quoted: list[tuple[str, int]] = []
    for rel in SPINE + ["docs/BENCHMARK.md"]:
        p = ROOT / rel
        if p.suffix not in {".md", ".txt"} or not p.is_file():
            continue
        for m in SUITE_RE.finditer(p.read_text()):
            quoted.append((rel, int(m.group(1).replace(",", ""))))
    if not quoted:
        return

    out = subprocess.run(
        ["uv", "run", "--extra", "dev", "pytest", "--collect-only", "-q", "tests"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    m = re.search(r"(\d+)\s+tests? collected", out.stdout) or \
        re.search(r"^(\d+)\s*$", out.stdout.strip().splitlines()[-1] if out.stdout.strip() else "")
    if not m:
        fail("suite-size", "could not read a collected-test count from pytest; "
                           f"stdout tail: {out.stdout.strip()[-200:]!r}")
        return
    collected = int(m.group(1))
    for rel, n in quoted:
        if n != collected:
            fail("suite-size",
                 f"{rel} advertises {n} tests but pytest collects {collected}. "
                 "A suite size is a claim; update the doc or explain the gap.")


def gate_redteam_tally() -> None:
    """An advertised attack count must match the headings it advertises.

    README, llms.txt and RUBRIC each said "8 carried LIVE" for twenty commits
    after A12 was downgraded to BOUNDED by the control tier. Three documents,
    one number, no gate.
    """
    rt = (ROOT / "docs" / "RED-TEAM.md").read_text()
    heads = re.findall(r"^## A\d+\..*?·\s*(\w+)", rt, re.M)
    total, live = len(heads), heads.count("LIVE")
    for rel in ["README.md", "llms.txt", "docs/RUBRIC.md"]:
        text = (ROOT / rel).read_text()
        for claimed, actual, what in (
                (re.search(r"(\d+) attacks", text), total, "attacks"),
                (re.search(r"(\d+) carried LIVE", text), live, "carried LIVE")):
            if claimed and int(claimed.group(1)) != actual:
                fail("redteam-tally",
                     f"{rel} advertises {claimed.group(1)} {what}; "
                     f"RED-TEAM.md headings show {actual}")


def gate_card_honest() -> None:
    """A card that always exits zero is decoration."""
    import json
    card = json.loads((ROOT / "MEASUREMENT_CARD.json").read_text())
    if card["verdict"] == "VERIFIED" and card.get("unmet_claims"):
        fail("card", "verdict is VERIFIED while unmet_claims is non-empty")
    if card["verdict"] == "NOT_VERIFIED" and not card.get("unmet_claims"):
        fail("card", "verdict is NOT_VERIFIED but no unmet claim is named")


def _collected_tests() -> int | None:
    out = subprocess.run(
        ["uv", "run", "--extra", "dev", "pytest", "--collect-only", "-q", "tests"],
        cwd=ROOT, capture_output=True, text=True, check=False)
    m = re.search(r"(\d+)\s+tests? collected", out.stdout)
    return int(m.group(1)) if m else None


def _live_loc() -> int:
    n = 0
    for d in ("src", "tests", "scripts"):
        for p in (ROOT / d).rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            n += sum(1 for _ in p.open(errors="replace"))
    return n


def gate_card_fresh() -> None:
    """The measurement card is a claim, and it went eight commits stale.

    It ended up asserting that SEC was blocked and no archive had been
    downloaded - against 4.2M built rows - while every gate stayed green,
    because the suite-size gate reads prose and never looked at JSON. That is a
    gate measuring the wrong surface, and it is the third time in this
    repository that a probe could not observe the thing it was meant to watch.

    Regenerate with scripts/refresh_card.py rather than editing by hand.
    """
    import json as _json
    card = _json.loads((ROOT / "MEASUREMENT_CARD.json").read_text())
    cs = card.get("code_state") or {}

    collected = _collected_tests()
    if collected is None:
        # Silently skipping here would make this gate a no-op in exactly the
        # environment it most needs to work. Every other gate in this file
        # fails loudly when it cannot do its job.
        fail("card-fresh", "could not collect a test count, so the card's "
                           "tests_passing is unchecked. Refusing to pass a gate "
                           "that did not run.")
    elif cs.get("tests_passing") != collected:
        fail("card-fresh", f"card says tests_passing={cs.get('tests_passing')} but "
                           f"pytest collects {collected}. Run scripts/refresh_card.py.")

    loc = _live_loc()
    if cs.get("python_loc") and abs(cs["python_loc"] - loc) > max(50, loc * 0.02):
        fail("card-fresh", f"card says python_loc={cs['python_loc']}, live count is "
                           f"{loc}. Run scripts/refresh_card.py.")

    spent = sum(v for k, v in (card.get("spend_usd") or {}).items() if k != "total")
    if card.get("blocked_on") and spent > 0:
        fail("card-fresh", f"card carries blocked_on while recording ${spent:.2f} of "
                           "spend. Both cannot be true; the block was cleared.")

    gen = card.get("generated", "")
    newest = subprocess.run(["git", "log", "-1", "--format=%cs", "--", "results"],
                            cwd=ROOT, capture_output=True, text=True,
                            check=False).stdout.strip()
    if gen and newest and gen < newest:
        fail("card-fresh", f"card generated {gen} but results/ last changed {newest}. "
                           "The card is describing an older repository.")


#: Present-tense status assertions, each with the check that disproves it.
#: Historical references ("committed at W0, before any measurement existed") are
#: deliberately NOT matched - only claims about the current state.
def _has_retractions() -> bool:
    return bool(re.search(r"^## R\d{3}",
                          (ROOT / "docs" / "RETRACTIONS.md").read_text(), re.M))


STALE_STATUS = [
    ("src/ is empty", lambda: any(
        p.stat().st_size > 0 for p in (ROOT / "src" / "titer").rglob("*.py"))),
    ("no result exists", lambda: any((ROOT / "results").glob("*.json"))),
    ("No result exists", lambda: any((ROOT / "results").glob("*.json"))),
    ("Nothing to reproduce yet", lambda: any((ROOT / "results").glob("*.json"))),
    ("nothing to reproduce yet", lambda: any((ROOT / "results").glob("*.json"))),
    ("reads NOT_VERIFIED", lambda: _card_verdict() != "NOT_VERIFIED"),
    ("reads `NOT_VERIFIED`", lambda: _card_verdict() != "NOT_VERIFIED"),
    # llms.txt described RETRACTIONS.md as "empty, on purpose" for 20 commits
    # after R001 and R002 were filed, in the same file whose status line named
    # two retractions. The machine-readable summary was the last thing checked.
    ("empty, on purpose", _has_retractions),
    ("no retractions", _has_retractions),
    ("No retractions", _has_retractions),
]


def _card_verdict() -> str:
    import json as _json
    return _json.loads((ROOT / "MEASUREMENT_CARD.json").read_text()).get("verdict", "")


def gate_no_stale_status() -> None:
    """A doc must not assert a state the repository disproves.

    REPRODUCTION.md opened with "Nothing to reproduce yet - src/ is empty by
    design at W0" while being linked from the README as THE reproduction guide,
    and AGENTS.md told every agent that no result exists. Both were true once.
    Neither was true when a reader found them.
    """
    for rel in SPINE + ["docs/BENCHMARK.md"]:
        p = ROOT / rel
        if p.suffix not in {".md", ".txt"} or not p.is_file():
            continue
        text = p.read_text()
        for phrase, contradicted in STALE_STATUS:
            if phrase in text and contradicted():
                fail("stale-status",
                     f"{rel} asserts {phrase!r}, which the repository disproves.")


def main() -> int:
    for gate in (gate_spine, gate_privacy, gate_cited_paths,
                 gate_no_placeholders, gate_prereg_frozen, gate_card_honest,
                 gate_advertised_suite_size, gate_card_fresh,
                 gate_no_stale_status, gate_redteam_tally):
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
