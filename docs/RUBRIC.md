# RUBRIC — how this repository grades itself

Self-scoring is evidence of intent, not of quality. It is published because
refusing to score yourself is worse, and because the gap between a self score
and an independent cold read is itself informative.

The W0 version of this file scored 50 of 50 *available* points and left 60
unavailable because no results existed. They exist now.

## Post-results score (2026-09-03)

| # | Criterion | Weight | Score | Evidence |
|---|---|---|---|---|
| 1 | Ground truth is a program, not an opinion | 15 | **15** | SEC filings and OpenAlex/DOI authorship. No model assigns any label, and a test greps the modules to keep it that way. |
| 2 | Every reported number carries an interval | 10 | **10** | Every rate in `BENCHMARK.md` is a Wilson or bootstrap interval. |
| 3 | Trivial floor reported and beaten | 10 | **4** | The web floor was run and **withdrawn as a parser artefact** — it measured title-only resolution, not free web search. The R4 floors (`never_verify`, `always_deep_verify`, `abstain_always`) *are* reported on real-fitted data. Partial credit is the honest score. |
| 4 | Pre-registration frozen before `src/`, publicly hashed | 10 | **10** | Two, both hash-published, both gated, the gate verified to fire. |
| 5 | Unflattering findings lead | 10 | **10** | The README leads with five artefacts. `RETRACTIONS.md` carries two entries; `MEASUREMENT_CARD.json` names eight unmet claims. |
| 6 | Coverage stated in someone else's vocabulary | 5 | **5** | PeopleSearchBench's four scenarios; the expertise gaps in a buyer's terms. |
| 7 | Red team attacks own claims, LIVE ones kept | 5 | **5** | 17 attacks, 8 carried LIVE — including "your 18% may be prompt interpretation" and "one provider is not a benchmark". |
| 8 | Cost asymmetry modelled, ranking stability reported | 10 | **6** | Five profiles including `expert_sourcing` at 150×. **No ranking is reported at all** — only one provider survived, so stability across profiles is untestable. |
| 9 | Environment health gate before any training | 10 | **8** | Run on real data: solve rate 0.37, in band. Loses 2 for the `high` collision band having **zero** observations. |
| 10 | Across-seed spread published for every trained arm | 10 | **n/a** | Nothing trained. The gate exists (`src/titer/train/seeds.py`) and is tested against reconforge's real numbers. |
| 11 | Ethics enforced mechanically, not asserted | 5 | **5** | `make privacy-gate` inside `make validate`; it has caught three real violations, including in my own commits. |

**Self-score: 78 of 90 available** (criterion 10 excluded — nothing trained).

## Where it loses points, in one place

- **The trivial floor failed.** D020 made it the arm that must be beaten and it
  was never validly measured.
- **No cross-provider ranking.** One provider survived; the pre-registered
  `cannot_separate` branch forbids ranking language and there is nothing to rank.
- **The hardest collision band is empty** in the fitted environment.
- **No trained policy.** R4 ships an environment, not a result about a model.

## Independent read — obtained 2026-09-04

**74 / 90**, against a self-score of 78. The reviewer checked the repository
cold and verified the delivery claims independently: 238 tests passing, gates
green, both pre-registration hashes matching and their files untouched since the
freeze commits, GitHub public, both datasets public and ungated, Space serving
200.

Three criteria were marked down, and all three are correct:

| Criterion | Self | Independent | Why |
|---|---|---|---|
| 3 — trivial floor | 4 | **3** | The floor was withdrawn as a parser artefact and never validly measured. |
| 5 — unflattering findings lead | 10 | **8** | `MEASUREMENT_CARD.json` was eight commits stale and contradicted the README on the front page — claiming SEC was blocked and zero credits spent, against 4.2M built rows. |
| 8 — cost asymmetry, ranking stability | 6 | **5** | No cross-provider ranking exists at all. |

The criterion-5 deduction is the sharpest one, because it lands on the criterion
the card *is*. The fix was not to edit the card: it is now **generated** by
`scripts/refresh_card.py` and gated by `gate_card_fresh`, which compares its
counts to live values and refuses a `blocked_on` alongside recorded spend. A
second gate, `gate_no_stale_status`, refuses any document asserting a state the
repository disproves — it found five on its first run, two of which the cold
read had not caught.

### The reviewer's own summary, kept verbatim because it is fairer than mine

> Value: high as methodology exemplar and hiring signal. Low as benchmark of
> category.

That is the honest description of this work. It measured one provider at n=750
and produced one surviving number; what it demonstrates well is a process for
not publishing the other five.
