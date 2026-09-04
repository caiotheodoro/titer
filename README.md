# titer

*The concentration you reach by titration: add reagent until you know.*

**Six headline numbers about commercial people-search products. Five of them
were artefacts of this instrument, not findings about any vendor. Every one was
caught by reading the returned rows — never by reading a summary statistic.**

That is the result. The surviving measurements are below, and they matter less
than the ratio.

---

## Why that ratio is the finding

[`docs/SURVEY.md`](docs/SURVEY.md) records the same B2B data vendor at **42.4%**
in one published comparison and **78%** in another. Neither publishes a
methodology. The category's own numbers put average accuracy near 50% against
95%+ marketing claims.

A gap that size does not come from vendors differing. It comes from harnesses
differing. This repository is a worked example of how: five times, under
conditions where we were *specifically watching for it*, a defect in the
measurer produced a number that looked publishable.

| # | The number | What it actually was |
|---|---|---|
| 1 | Ploid 0/21 | The company was packed into the free-text query instead of the documented `filters`. [R001](docs/RETRACTIONS.md) |
| 2 | Ploid 0/21 again | The company filter selected people *currently* there, so the anchor always came back. [D028](docs/DECISIONS.md) |
| 3 | Web floor 0/300 | Our parser read person names out of page titles like `FORM 8-K 10.04.2013`. |
| 4 | E1 at 17–21% | 13.3% of "false" claims were true — OpenAlex `topics` is a top-N summary, not a record. [R002](docs/RETRACTIONS.md) |
| 5 | H1 median lag 7,360 days | Isotonic regression forcing monotonicity onto a non-monotone curve. [D033](docs/DECISIONS.md) |
| 6 | **E1 at 13–17%** | **Survived. Twice.** |

Each was found the same way: by reading what the provider actually returned. In
case 4 the affirmations kept looking *correct* — a dermatologic oncologist
affirmed for "Educational Methods", who had in fact co-authored medical
education research. Correct answers, scored as errors.

---

## What survives

**Expertise verification** — Exa `/answer`, n=750, negatives verified false
against OpenAlex `/works` *before* the provider was asked:

| | n | Correct | False affirmation |
|---|---|---|---|
| Attested claims | 250 | **0.9600 [0.9279, 0.9781]** | 0 [0, 0.0151] |
| False, adjacent field | 250 | 0.8680 | **0.1320 [0.0956, 0.1796]** |
| False, adjacent subfield | 250 | 0.8320 | **0.1680 [0.1268, 0.2193]** |

It confirms real expertise 96% of the time and affirms claims about topics the
person has **never published in** roughly one time in six. It is not bad at the
task; it is bad at saying *no*.

**Calibration** — 686 of 750 answers (91.5%) sit in the 0.9–1.0 confidence bin
at mean confidence **0.987** against accuracy **0.889**. Confidence is pinned at
ceiling and does not discriminate there. ECE 0.1153.

**Index freshness** — reflection of an attested job change rises 0.28 → **0.57**
over three years, then falls to 0.29. Non-monotone, so no half-life exists and
the pre-registered estimator was withdrawn. The fall is most likely *our oracle*
ageing out, not the index regressing.

**The environment** — fitted to 500 real observations, solve rate 0.37, inside
the 10–80% band. `never_verify` (reward 0.0455) beats `always_deep_verify`
(0.0277): spending 3× more bought marginally *fewer* correct answers.

## What does not survive

Ploid, after three runs — every one killed by a defect of ours, so **no number
about Ploid is claimed**. The web floor. The raw E1 rates. H1's median lag.
See [`docs/RETRACTIONS.md`](docs/RETRACTIONS.md).

---

## How it works

**The oracle is a filing, not a judgement.** Section 16 of the Securities
Exchange Act compels officers and directors to state, by name, that they held a
role at an issuer on a date — 4.2M attested rows. For expertise, authorship is
attested by publishers through DOIs, not by the researcher.

**A false claim is constructed, not judged.** A person's attested topics come
from their works, so a false expertise claim is a topic with **zero** works,
drawn mechanically from an adjacent field and verified exhaustively. No model
participates in any label, anywhere, including title normalisation.

**Errors are priced, not counted.** Five cost profiles. Under `expert_sourcing`
a fake expert admitted costs 150× a miss — grounded in observed sourcing
bounties of $250–$15,000 against a documented infiltration incident.

**Everything replays.** The cache stores raw provider bodies, so a parser fix
costs nothing and every table regenerates with no keys and no spend.

## The limitations, up front

- **One provider.** Every surviving number describes Exa. Nothing here supports
  a claim about the category.
- **The surviving 18% may be prompt interpretation.** The confirmatory run
  removed contaminated negatives; it cannot remove *adjacent* ones.
  ([RED-TEAM A12](docs/RED-TEAM.md))
- **Publication record is not expertise.** Engineers, practising clinicians and
  lawyers leave no bibliographic trace and are invisible here — most of who an
  expert platform actually hires.
- **7.3% of the EDGAR population is usable** after four forced narrowings.
  ([COVERAGE](docs/COVERAGE.md))
- **Nothing is trained.** R4 ships an environment, not a policy.
- **The trivial floor failed.** It was never validly measured.

## Reproduce

```bash
make validate                 # seven gates; a nonzero exit is the product
uv run --extra dev pytest tests
uv run python scripts/env_health.py --real
```

Every measurement regenerates from `data/replay.jsonl` without an API key.
Commands and footguns: [`docs/REPRODUCTION.md`](docs/REPRODUCTION.md).

**238 tests green.** Total spend to produce all of the above: **$22.75**.

## Layout

| Path | What |
|---|---|
| [`CONTRACTS.md`](CONTRACTS.md) | Frozen definitions. No change without a decision entry **and** evidence. |
| [`docs/PRE-REGISTRATION.md`](docs/PRE-REGISTRATION.md) · [`-EXPERTISE`](docs/PRE-REGISTRATION-EXPERTISE.md) | Frozen before `src/`, hashes published. Never edited. |
| [`docs/RETRACTIONS.md`](docs/RETRACTIONS.md) | The two formal retractions. Committed at W0, before any measurement. |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Append-only, 33 entries, each with the counterfactual. |
| [`docs/RED-TEAM.md`](docs/RED-TEAM.md) | 17 attacks on our own claims; 8 carried LIVE. |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) · [`RUBRIC`](docs/RUBRIC.md) · [`COVERAGE`](docs/COVERAGE.md) | Results, self-score (78/90), and what this cannot see. |
| [`docs/MARKET.md`](docs/MARKET.md) | Where an attestation layer would sell — with the case against it. |

## Rectification

If you appear in a corpus and want out, write to the address in
[`docs/ETHICS.md`](docs/ETHICS.md) §6. Honoured within 7 days, no justification
required, recorded as a count and never as an identity.

## Licence

MIT. Corpora derive from US Government public-domain records and CC0 sources,
published as pointers, never as assembled records.
