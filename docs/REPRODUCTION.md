# REPRODUCTION

Every published number regenerates from the replay cache **with no API key and
no spend**. The cache stores raw provider bodies, so even a parser fix replays
free.

## Prerequisites

- `uv`
- Nothing else for the tables below. Keys are needed only to *regenerate* the
  cache, which you should not need to do.

Optional, for rebuilding corpora from source:

```bash
export TITER_SEC_UA="Your Name you@example.com"     # SEC requires a CONTACTABLE address
export TITER_OPENALEX_MAILTO="you@example.com"      # OpenAlex polite pool
export TITER_NAME_SALT="<random hex>"               # published name hashes
```

## Gates — run these first

```bash
make validate                        # 9 gates. A nonzero exit is the product.
uv run --extra dev pytest tests      # unit + contract tests
```

## Reproduce the published results

```bash
# Verifier integrity: gold 1.0, no-op 0.0, inverted collapses, flat probe.
uv run --extra dev python scripts/oracle_selfcheck.py

# The R4 environment, fitted to the REAL replay cache. Reports the solve-rate
# band and the three floor policies. No network.
uv run --extra dev python scripts/env_health.py --real

# E1 + E3 (expertise). Replays from cache; --spend is required for live calls.
uv run --extra dev python scripts/run_expertise.py \
    --tasks expert_tasks_v2.jsonl --out expertise_e1_v2.json --per-stratum 250

# Employment identity, stratified by elapsed time (H1).
uv run --extra dev python scripts/full_run.py \
    --providers exa --strategy elapsed --n 500 --out h1_elapsed.json
```

Each writes to `results/`. Without `--spend` nothing is billed and anything not
already cached is skipped, so a fresh clone reproduces exactly the cached
subset — which is every number in `docs/BENCHMARK.md`.

## Rebuild the corpora from source (slow, free, needs the env vars)

```bash
uv run --extra corpus python scripts/build_corpus.py --quarters 2003q3..2026q4
uv run --extra dev  python scripts/build_tasks.py --require-last-employer --max-age-years 10
uv run --extra dev  python scripts/leak_probe.py          # 1.0 on an intentional leak, 0.0 clean
uv run --extra dev  python scripts/build_scholar_corpus.py --authors 20000
uv run --extra dev  python scripts/build_expert_tasks.py --limit 1600 --out expert_tasks_v2.jsonl
```

`build_expert_tasks.py` verifies every constructed-false claim against OpenAlex
`/works` before it enters the corpus. Skipping that check is what voided the
first expertise run (`docs/RETRACTIONS.md` R002).

## Regenerate the measurement card

```bash
uv run --extra dev python scripts/refresh_card.py
```

**Do not hand-edit `MEASUREMENT_CARD.json`.** It went eight commits stale that
way and ended up asserting SEC was blocked against 4.2M built rows.
`gate_card_fresh` now refuses to let it drift.

## Footguns, all of them paid for

- **SEC needs a *contactable* address.** A GitHub `users.noreply` address gets a
  403 — and SEC's 403 page is titled "Request Rate Threshold Exceeded"
  regardless of cause, so do not diagnose from the page title.
- **SEC throttles on burst**, well below its documented 10 req/s. Space requests;
  do not loop on a 403.
- **Scrape SEC quarterly filenames, never generate them.** The newest quarter
  lives under a different path prefix and a generator silently drops it.
- **`intervals.py --profile X` without `--out`** overwrites the research run.
- **Background slow runs need a trailing `| tail`** or the log buffers empty.
- **Verify a green from a fresh tree**, not a possibly-stale venv.
- **`git ls-files`, not `ls`**, before believing a file ships.
