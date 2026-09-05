# titer

[![gates](https://github.com/caiotheodoro/titer/actions/workflows/ci.yml/badge.svg)](https://github.com/caiotheodoro/titer/actions/workflows/ci.yml)

*The concentration you reach by titration: add reagent until you know.*

**Six headline numbers about commercial people-search products. Five were
artefacts of this instrument, not findings about any vendor. Every one was
caught by reading the rows the provider returned, never by reading a summary
statistic.**

---

## Why five-of-six is the finding

[`docs/SURVEY.md`](docs/SURVEY.md) records the same B2B data vendor at **42.4%**
in one published comparison and **78%** in another. Neither publishes a
methodology. The category's own numbers put average accuracy near 50% against
95%+ marketing claims.

Harness design moves a vendor number further than vendor quality does. This
repository is a worked example of how far: five times, under conditions where we
were *specifically watching for it*, a defect in the measurer produced a number
that looked publishable.

| # | The number | What it actually was |
|---|---|---|
| 1 | A 0/21 against a people index | We packed the company into the free-text query instead of the documented `filters`, so it scored our wire format. [R001](docs/RETRACTIONS.md) |
| 2 | 0/21 again, through the "fix" | Our filter selected people *currently* at the company, so the anchor always came back. [D028](docs/DECISIONS.md) |
| 3 | Web floor 0/300 | Our parser read person names out of page titles like `FORM 8-K 10.04.2013`. |
| 4 | E1 at 17–21% | 13.3% of "false" claims were true. OpenAlex `topics` is a top-N summary, not a record. [R002](docs/RETRACTIONS.md) |
| 5 | H1 median lag 7,360 days | Isotonic regression forcing monotonicity onto a non-monotone curve. [D033](docs/DECISIONS.md) |
| 6 | **E1 at 8–17%** | **Survived. Three times.** |

Each was found the same way, by reading what the provider actually returned. In
case 4 the affirmations kept looking *correct*: a dermatologic oncologist
affirmed for "Educational Methods" had in fact co-authored medical education
research. Correct answers, scored as errors.

---

## What survives

**Expertise verification.** Exa `/answer`, negatives verified false against
OpenAlex `/works` *before* the provider was asked.

| Claim | n | Correct | False affirmation |
|---|---|---|---|
| Attested | 250 | **0.9600 [0.9279, 0.9781]** | 0 [0, 0.0151] |
| False, adjacent subfield (NEAR) | 250 | 0.8320 | **0.1680 [0.1268, 0.2193]** |
| False, adjacent field (FAR) | 250 | 0.8680 | **0.1320 [0.0956, 0.1796]** |
| False, different domain (CONTROL) | 250 | 0.9160 | **0.0840 [0.0556, 0.1250]** |

The control ran separately, with its own matched attested arm at 0.9840 [0.9596,
0.9938] on the same authors. It confirms real expertise 96% of the time and
affirms topics the person has **never published in** one time in six. It is bad
at saying *no*.

**NEAR is 2.00× the control and the intervals do not overlap**, so topic distance
moves the rate. The control also refuses to go to zero: 21 of 250 absurd claims
were affirmed, one in twelve, which puts a floor of at least 8.4 points under the
16.8 that no generous reading of the prompt explains.

**Calibration.** 686 of 750 answers (91.5%) sit in the 0.9–1.0 confidence bin at
mean confidence **0.987** against accuracy **0.889**. Confidence is pinned at
ceiling and does not discriminate there. ECE 0.1153.

**A capability constraint does disambiguate, falsifying our own hypothesis.**
D029 argued a people-search surface cannot be handed a biographical constraint.
On Exa's answer engine it plainly can. Naming the person's past employer in free
text, n=80 per colliding band, paired within task:

| Band | name alone | + past employer | paired difference |
|---|---|---|---|
| `unique` | 0.2375 | 0.3500 | +0.1125 |
| `low` | 0.0500 | 0.2000 | **+0.1500 [0.0750, 0.2375]** |
| `medium` | **0.0000** | 0.1875 | **+0.1875 [0.1000, 0.2750]** |
| `high` | **0.0000** | 0.2875 | **+0.2875 [0.1875, 0.3875]** |

Three bands, three intervals excluding zero. The pre-registered falsification
condition was exactly this, and it fired. Adding the attested date and role on
top of the employer buys nothing measurable once names collide, and a colliding
name with **no** context is 0 of 80. ([D039](docs/DECISIONS.md))

**A false affirmation is usually ungrounded.** For each of 399 affirmations, we
resolved up to three of the provider's own citations against OpenAlex and asked
whether any is a work that author actually wrote. Cost: $0, the citations were
already cached.

| Claim affirmed | cites a real work by that author |
|---|---|
| Attested | **0.5733 [0.4933, 0.6497]** |
| False, adjacent field | 0.2843 [0.2058, 0.3784] |
| False, adjacent subfield | 0.2302 [0.1653, 0.3110] |
| **False, different domain** | **0.0000 [0.0000, 0.1546]** |

The control arm now fails two independent tests: it is the arm no generous
reading of the prompt explains, **and** the arm that cites nothing verifiable at
all, zero of twenty-one. But roughly **one in four** adjacent false affirmations
*is* grounded in the person's real work, so the interpretation defence survives
in the middle of the table and dies only at the extreme.
([D044](docs/DECISIONS.md))

**False merges run backwards.** H2 predicted confidently-wrong identities would
rise with name-collision degree. They fall:

| collision degree | 1 | 2–3 | 4–9 | ≥10 |
|---|---|---|---|---|
| false merge, n=80 each | **0.0375** | 0.0000 | 0.0125 | 0.0000 |

False merges are likeliest where names **don't** collide. On a colliding name the
provider mostly cannot name anyone resolvable, so the outcome is a miss rather
than a wrong identity: it never gets the chance to be confidently wrong. The risk
sits where nobody stratifies for it. H2 is falsified, and it cost **$0**. The
strata it needed were already in the E2 draw. ([D041](docs/DECISIONS.md),
[D042](docs/DECISIONS.md))

**Index freshness.** Reflection of an attested job change rises 0.28 → **0.57**
over three years, then falls to 0.29. Non-monotone, so no half-life exists and
the pre-registered estimator was withdrawn. The fall is most likely *our oracle*
ageing out rather than the index regressing.

**The environment, and a trained policy.** Fitted to 485 real observations, solve
rate 0.37, inside the 10–80% band. `never_verify` (−0.2292) still beats
`always_deep_verify` (−0.2574), so spending 3× more still bought marginally fewer
correct answers. But both are beaten by **doing nothing**: at a 37% solve rate,
answering is negative expected value and `abstain_always` (−0.1000) is the floor
to beat. Those numbers are corrected; the ones published before were inflated by
two reward defects ([D037](docs/DECISIONS.md)).

A policy trained on the simulator clears it, over 6 seeds on a frozen split:

| | value |
|---|---|
| trained policy | **0.0461** |
| `abstain_always` | −0.1000 |
| margin | 0.1461 |
| across-seed SD | **0.0122**, 0.08× the margin |

It **learned when to answer and not how sure to be**: it abstains on 41.7% of
tasks, lifting precision from the 37% base rate to **64%**, then states
confidence **1.0 on every answer it gives**. That is the same failure E3 measured
in the provider, reproduced by our own policy in an environment that prices it.
([D036](docs/DECISIONS.md))

## What does not survive

**The people-index arm is unmeasured, and that is a statement about us.** Five
budgets produced seven defects in our own harness and no valid observation, so
**no accuracy number is claimed for any people-search index here**, not a poor
one and not any. Publishing a void score with a footnote is precisely what
[R001](docs/RETRACTIONS.md) forbids, because the number travels and the footnote
does not.

What the runs did establish is about query construction, and it is useful:

- **Asked properly, the index finds the person.** `{"query": "George Reyes",
  "filters": {"company": "Google"}}` returns the right George Reyes as the top
  result. Our early failures were malformed queries, not missing people.
- **The documented `company` filter earns its place.** On colliding names it
  resolved 3 of 12 where a bare name resolved 0, though it returns the person's
  *current* employer, so it answers "who is there now", not "where did they go".
- **Extra context can cost precision.** Appending company tokens to a name
  displaced the target: `Michael Anzilotti Access National` returned two other
  people at that company, while `Michael Anzilotti` alone returned him at rank 1.

What a real measurement would cost is published instead of guessed: **n=49 per
arm for a ±0.10 half-width, $9.80** at the measured $0.20 per search.

The index in question is [Ploid](https://ploid.com), named here because hiding
which surface we failed to measure would be its own kind of dishonesty. Their
Terms are the most permissive of the five vendors surveyed and expressly allow
automated access through documented APIs, which is why they were the arm we
could attempt at all. The full record, defects included, is in
[R001](docs/RETRACTIONS.md), [D028](docs/DECISIONS.md),
[D035](docs/DECISIONS.md) and [D040](docs/DECISIONS.md).

Also void: our web floor, the raw E1 rates, and H1's median lag.
See [`docs/RETRACTIONS.md`](docs/RETRACTIONS.md).

---

## How it works

**The oracle is a filing.** Section 16 of the Securities Exchange Act compels
officers and directors to state, by name, that they held a role at an issuer on a
date: 4.2M attested rows. For expertise, publishers attest authorship through
DOIs, so the researcher is never the source.

**False claims are constructed.** A person's attested topics come from their
works, so a false expertise claim is a topic with **zero** works, drawn
mechanically from an adjacent field and verified exhaustively. No model
participates in any label, anywhere, including title normalisation.

**Errors are priced.** Five cost profiles. Under `expert_sourcing` a fake expert
admitted costs 150× a miss, grounded in observed sourcing bounties of
$250–$15,000 against a documented infiltration incident.

**Everything replays.** The cache stores raw provider bodies, so a parser fix
costs nothing and every table regenerates with no keys and no spend.

## The limitations, up front

- **One provider.** Every surviving number describes Exa. Nothing here supports a
  claim about the category.
- **Part of the 16.8% may be prompt interpretation.** The confirmatory run
  removed contaminated negatives; it cannot remove *adjacent* ones. The control
  bounds this: at least 8.4 points are error under any reading.
  ([RED-TEAM A12](docs/RED-TEAM.md))
- **Publication record is not expertise.** Engineers, practising clinicians and
  lawyers leave no bibliographic trace and are invisible here, which is most of
  who an expert platform actually hires.
- **7.3% of the EDGAR population is usable** after four forced narrowings.
  ([COVERAGE](docs/COVERAGE.md))
- **The trained policy is a 130-parameter linear model on a simulator**, not
  a language model and not a live-provider agent. The simulator's `high`
  collision band still holds zero observations.
- **The trivial floor failed.** It was never validly measured.

## Reproduce

```bash
make validate                 # ten gates; a nonzero exit is the product
uv run --extra dev pytest tests
uv run python scripts/env_health.py --real
```

Every measurement regenerates from the replay cache without an API key.
Commands and footguns: [`docs/REPRODUCTION.md`](docs/REPRODUCTION.md).

**268 tests green.** Total spend to produce all of the above: **$41.35**.

## Layout

**Everything in one place:**
[the collection](https://huggingface.co/collections/caiotheodoro/titer-six-vendor-numbers-five-were-my-harness-6a9a4689d8a468b26e466075).

| Path | What |
|---|---|
| [`CONTRACTS.md`](CONTRACTS.md) | Frozen definitions. No change without a decision entry **and** evidence. |
| [`docs/PRE-REGISTRATION.md`](docs/PRE-REGISTRATION.md) · [`-EXPERTISE`](docs/PRE-REGISTRATION-EXPERTISE.md) | Frozen before `src/`, hashes published. Never edited. |
| [`docs/RETRACTIONS.md`](docs/RETRACTIONS.md) | The two formal retractions. Committed at W0, before any measurement. |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Append-only, 45 entries, each with the counterfactual. Two (D042, D044) correct earlier ones. |
| [`docs/RED-TEAM.md`](docs/RED-TEAM.md) | 17 attacks on our own claims; 7 carried LIVE, 2 open, 1 bounded by a control tier. |
| [`docs/BENCHMARK.md`](docs/BENCHMARK.md) · [`RUBRIC`](docs/RUBRIC.md) · [`COVERAGE`](docs/COVERAGE.md) | Results, the independent read (74/90 against a 78/90 self-score), and what this cannot see. |
| [`docs/MARKET.md`](docs/MARKET.md) | Where an attestation layer would sell, with the case against it. |

## Rectification

If you appear in a corpus and want out, write to the address in
[`docs/ETHICS.md`](docs/ETHICS.md) §6. Honoured within 7 days, no justification
required, recorded as a count and never as an identity.

## Licence

MIT. Corpora derive from US Government public-domain records and CC0 sources,
published as pointers, never as assembled records.
