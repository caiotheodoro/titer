# REPRODUCTION

**Nothing to reproduce yet.** `src/` is empty by design at W0; this file records
the commands each wave must make work, so that a reproducer can tell whether a
wave actually landed.

## Prerequisites

- `uv`
- A `User-Agent` for SEC access: export `TITER_SEC_UA="titer research <contact>"`.
  The SEC blocks unclassified automated access; a missing UA is the first thing
  to check on a 403.
- Provider keys are **optional**. Every measurement after W2 replays from the
  cache, so the tables reproduce with no keys and no spend. Keys are needed only
  to regenerate the cache.

## Wave gates

```bash
# W0 - docs only. Works today.
make validate                       # spine + privacy gate + doc claim gates

# W1 - corpus
uv run python scripts/build_corpus.py --quarters 2003q3..2026q2
uv run python scripts/leak_probe.py         # 1.0 on intentional leak, 0.0 on clean split
uv run python scripts/oracle_selfcheck.py   # gold 1.0, noop 0.0, inverted labels collapse

# W2 - adapters and cache
uv run python scripts/measure_cost.py       # cost per task per provider -> results/cost_unit.json
uv run python scripts/power.py              # required n vs achievable n; selects the PRE-REG 3 branch

# W3/W4 - measurement
uv run python scripts/full_run.py --matched-n
uv run python scripts/intervals.py --resamples 10000 --seed 11 --out results/intervals.json
uv run python scripts/calibration.py

# W5 - environment
uv run python scripts/env_health.py         # no report, no training run

# W6 - training
uv run python -m titer.train.sft  --seed 11
uv run python -m titer.train.grpo --seed 11
uv run python scripts/seed_spread.py        # across-seed SD; must be < any claimed margin
```

## Footguns, inherited and local

- `intervals.py --profile X` without `--out` overwrites the research run.
  Always pass `--out`.
- Background slow runs need a trailing `| tail`, or the log buffers and stays
  empty for the whole run.
- Never run two `full_run.py` at once.
- A green run from a stale virtualenv proves nothing. Verify from a fresh tree.
- Quarterly SEC filenames are scraped, never generated — a generated recent
  quarter 404s and silently truncates the corpus.
- Check `git ls-files`, not `ls`, before believing a file ships.
