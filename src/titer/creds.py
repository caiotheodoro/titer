"""Load credentials from the gitignored .env, once, without a dependency.

Every credential-consuming path reads `os.environ`, which is correct - a
credential must never come from a tracked file. But it meant that running a
script from a plain shell, without `set -a; source .env`, **silently** used no
key at all.

That is not a small inconvenience. OpenAlex bills keyed and keyless requests
against different pools in practice: measured 2026-09-04, the keyless pool was
exhausted and returning 429 while the key had budget. So an unsourced shell did
not fail - it crawled, auditing 18 rows where the key would have done hundreds,
and reported "no key is set to fall back from" as if that were the environment's
fault rather than the loader's absence.

A tool that quietly does something weaker than asked is the defect class this
repository exists to name, so the loader is explicit and the absence is loud.
"""
from __future__ import annotations

import os
from pathlib import Path

_LOADED = False


def load_env(root: Path | None = None) -> dict[str, bool]:
    """Populate os.environ from .env for keys that are not already set.

    An already-exported value always wins, so an explicit
    `KEY=... python script.py` is never overridden.
    """
    global _LOADED
    if _LOADED:
        return {}
    _LOADED = True
    root = root or Path(__file__).resolve().parent.parent.parent
    p = root / ".env"
    seen: dict[str, bool] = {}
    if not p.is_file():
        return seen
    for line in p.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k, v = k.strip(), v.strip().strip('"').strip("'")
        if k and k not in os.environ:
            os.environ[k] = v
            seen[k] = True
    return seen
