# ARCHITECTURE

Modules and the seams between them. A seam exists where a wrong decision would
otherwise leak across a boundary.

```
SEC quarterly TSV zips ──► corpus/ ──► AttestedTuple rows ──► tasks
                                 │                              │
                                 └── collision degree d ────────┤
                                                                ▼
                            adapters/ ◄── replay cache ◄── providers + web floor
                                 │
                                 ▼
                            oracle/  (program checks only)
                                 │
                    ┌────────────┼────────────┐
                    ▼            ▼            ▼
                metrics/      costs/       sim/  ──► env/ ──► train/
                    │            │                    │
                    └────► results/ ◄─────────────────┘
```

## `src/titer/corpus/` - build the oracle

Downloads the quarterly `form345.zip` files, joins `REPORTINGOWNER` to
`SUBMISSION` on `ACCESSION_NUMBER`, applies the inclusion rules, derives
`role_class` and `title_class`, and computes name-collision degree.

**Seam: link discovery.** Quarterly filenames are *scraped from the SEC landing
page*, never generated. A generated `2026q2` name returns 404 while the landing
page advertises coverage through that quarter, so a generator would silently
truncate the corpus at a boundary nobody would notice.

**Seam: title normalization.** `title_map/v1` is regex-only and frozen. The raw
string is retained on every row. A model must not be reachable from this module,
and the module exports no hook that would let one in.

**Seam: exclusion accounting.** Every rule that drops a row increments a counter
that is written to `docs/COVERAGE.md`. A row cannot be dropped silently; the
builder fails if the counters do not reconcile against the input row count.

## `src/titer/oracle/` - decide correctness

Given a provider response and an `AttestedTuple`, returns exactly one outcome
class and the three reward atoms.

**Seam: identity-to-CIK mapping.** Providers do not return CIKs. The mapping is
made once, deterministically, by `name_norm/v1` against the SEC's own
`cik-lookup-data.txt`, and is computed **before** any scoring so it cannot be
tuned to a result. Ambiguous mappings are `UNRESOLVABLE` and excluded with the
rate published.

**Seam: the contamination bound.** The oracle exposes `false_merge_raw` and
`false_merge_net` as a pair. A caller cannot obtain one without the other,
because a raw false-merge rate without the same-human-two-CIK bound overstates
provider error by an unknown amount.

## `src/titer/adapters/` - talk to providers

One module per arm: `ploid`, `exa`, `webfloor`. Each exposes the same call
surface and reports what it spent.

**Seam: contact-field stripping at ingest.** Emails, phones, addresses, social
handles and profile URLs are removed **before** the response reaches disk, not
before publication. A cache that ever held them has already created the risk.

**Seam: the replay cache is the unit of reproducibility.** Every measurement
after W2 reads the cache, never the live API. A result that cannot be
regenerated from the cache is not a result. Cache keys include the provider,
the endpoint, the request body hash, and the measurement window.

**Seam: cost accounting is per-call and adapter-owned.** The env must never
estimate a price; it reads what the adapter recorded. Estimated costs would make
the whole value-of-information claim circular.

**Operational constraint, from `docs/DECISIONS.md` D019.** The Exa adapter is
built against the self-serve API only. Signing an Exa Order Form or MSA
retroactively acquires a contractual ban on publishing benchmark analysis. This
is recorded in `docs/HANDOFF.md` as a do-not-do.

## `src/titer/costs/` - price the errors

The four profiles plus `flat`. Severity is a property of the error; cost is a
property of the caller. Shape reused from the sibling `lossbench` cost registry
rather than re-derived.

**Seam: `flat` is a test, not a profile.** It is exported through a separate
symbol from the reportable profiles so it cannot be accidentally published as a
result.

## `src/titer/metrics/` - estimate, with intervals

Kaplan-Meier over elapsed days (R1), Wilson and paired bootstrap rates (R2),
reliability diagrams and ECE (R3), expected loss per profile (all).

**Seam: coverage and floor are returned as a pair.** A calibration floor at an
unstated coverage is meaningless, so the abstention cascade cannot return one
without the other.

**Seam: bins are never merged.** ECE uses 10 equal-width bins and an empty bin
is reported as empty. Merging empty bins flatters calibration.

## `src/titer/sim/` - the fitted simulator

Fits a cost, latency and error model to the W2 cache, and samples from it so RL
can run without spending credits.

**Seam: the simulator never sees the evaluation split.** It is fitted on the
training portion of the cache only. This is frozen in the pre-registration
because a simulator fitted on the eval set would make the sim-to-real gap
unmeasurable - which is the one number this module exists to expose.

## `src/titer/env/` - the environment

OpenEnv-native, with a `keel` `reset/step/state` facade over it. Actions are
priced provider calls plus `answer` and `abstain`. Turn cap and budget are
episode parameters and are recorded on every rollout.

**Seam: train and eval share the scoring stack.** The reward is computed by the
same `src/titer/oracle/` code that produces the reported outcome classes. A different
wrapper would be a different task, and the checkpoint would be selected against
something we do not report.

**Seam: the health report gates training.** `scripts/env_health.py` must emit
gold=1.0, noop=0.0, a passing flat probe, the solve-rate histogram, the
in-band percentage, and the zero-advantage group rate before `src/titer/train/` will run.

## `src/titer/train/` - SFT then GRPO

QLoRA 4-bit, LoRA on all layers including MLP. SFT on rejection-sampled passing
rollouts; then GRPO/RLVR against the oracle.

**Seam: checkpoint selection never touches the frozen test split.** Selection is
on the hill-climb split, at peak held-out, on the full metric profile rather
than one scalar.

**Seam: seeds.** A minimum of four training seeds. The across-seed spread is
computed before any margin is written down, and if the spread exceeds the margin
there is no claim.

## What is deliberately not built

- No Sets integration. Ploid's `/v1/sets` is private preview and its own docs
  say not to build a production integration against it.
- No enrichment calls. Out of scope by `docs/ETHICS.md` section 3, on
  proportionality grounds rather than budget.
- No 8-K prose extraction. That is the model-judged step this project excludes.
