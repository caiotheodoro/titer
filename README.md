# titer

*The concentration you reach by titration: add reagent until you know.*

**An instrument for the question no people-search vendor answers: how often does
the index confidently name the wrong human, and what is it worth paying to find
out?**

---

## Status

> **No results exist yet.** This repository is at W0: the definitions, the
> pre-registration and the ethics constraints are frozen, and `src/` is empty by
> design. `MEASUREMENT_CARD.json` reads `verdict = NOT_VERIFIED` and will keep
> reading that until every claim gate passes. A card that always exits zero is
> decoration.
>
> Nothing below is a finding. Everything below is a commitment about what will
> be measured and what would falsify it.

---

## The problem

People-search APIs sell resolution: *this row is that human*. Ploid's
`/v1/person` returns `identity_verified: false` until you pay 25 ACU - **$5.00
at pay-as-you-go list price**, or $2.50 at the Business seat rate. Every
competitor has an equivalent tier.

Three things are true at once:

1. **Nobody has publicly measured whether the resolution is right.** Not for any
   vendor. The best existing work, PeopleSearchBench (arXiv 2603.27476), is
   careful and states plainly that it does not measure identity resolution or
   false merges. Its oracle is a language model doing live web search.
2. **"Living index" is a falsifiable claim that nobody has tested.** Job changes
   have legally attested, timestamped public records. The lag between the record
   and the index is measurable and unmeasured.
3. **The tiers price compute, not risk.** When paying for a verification is
   worth it is left entirely to the caller's guess. There is no decision layer,
   anywhere. Ploid's own Terms disclaim the question outright: *"We do not
   warrant that outputs will be accurate, complete, or suitable for any
   particular decision."*

The vendor-published comparisons are worse than absent. The same provider scores
42.4% in one study and 78% in another; both were published by competitors, with
no methodology and no intervals. The category quotes ~50% real accuracy against
95%+ marketing claims.

## The approach

**Their oracle is the web. Ours is a filing.**

Section 16 of the Securities Exchange Act requires officers and directors of
registered issuers to file, by name, on Forms 3/4/5. The SEC publishes those
filings pre-flattened as quarterly TSVs. A two-table join yields:

> *(person CIK, issuer CIK, role, title, attested date, filing date)*

with a filer identifier, `RPTOWNERCIK`, that the SEC never recycles. 32,388
distinct people appear in 2025Q1 alone; roughly 180,000 Form 4s are filed a year,
back to 2003.

That gives two things nothing else does. Ground truth checked by a program
rather than judged by a model. And, because different CIKs are *provably*
different registrations, same-name collisions become measurable ground truth
instead of a judgement call.

## What gets measured

| | Question | Falsified if |
|---|---|---|
| **R1** | Does a "living index" have a measurable staleness half-life? | Reflection probability is flat in elapsed days |
| **R2** | How often does a provider confidently return the wrong human, and does it get worse with name-collision degree? | The rate is indistinguishable from zero net of contamination, or flat in collision degree |
| **R3** | Are the *free* signals (rank, `resolution_source`, `identity_verified`, `last_seen`) calibrated? | Raw ECE is already low, or the signals carry no information |
| **R4** | Can a small model that knows when to *stop paying* beat a large one that always escalates, per dollar? | It fails to beat `never_verify` and `always_deep_verify` |

R4 is an OpenEnv environment in which every action has a price, and the reward
is three program-checked atoms minus what was spent minus a heavy penalty for
being confidently wrong. There are no shaping terms.

## What this repository will not do

- Not claim a provider is bad. A measured rate, at a stated `n`, under a stated
  cost profile, with an interval, is the entire claim.
- Not use a language model to decide any ground-truth label, including title
  normalization. That is regex-only, frozen and versioned.
- Not publish anyone's email address, phone number, postal address or social
  profile. Not even where the field is technically public. See
  [`docs/ETHICS.md`](docs/ETHICS.md).
- Not quote a training margin without the across-seed spread. A sibling project
  published a headline whose across-seed standard deviation was 2.86x the
  claimed margin, and retracted it in its own README. That will not happen twice.

## The limitations, up front

These belong here, not in a footnote.

- **`RPTOWNERCIK` is not a person key.** It is unique per filer *registration*.
  Different CIK proves different registration - the direction false-merge
  detection depends on - but the same human can hold two CIKs, and the SEC
  publishes no merge table. We measure an upper bound on this and report false
  merges both raw and net of it.
- **The budget is $5 of Ploid credit.** At $0.20/ACU that is 25 ACU: exactly
  **one** paid verification, or roughly 500 search matches. Ploid's free-plan
  credit grant is not published, so it is treated as zero until measured.
  `docs/PRE-REGISTRATION.md` section 3 fixes, in advance, what we are allowed to
  say at each achievable sample size - including the branch where the honest
  answer is "this budget cannot separate these providers, and here is the `n`
  that could."
- **The trained policy is trained on a fitted simulator**, because live RL
  rollouts at $5 a verification are not possible. It is *evaluated* on
  held-out real calls, and the sim-to-real gap is published as the central
  limitation rather than discovered by a reader.
- **Coverage is US officers and directors of registered issuers.** That is not
  the population a GTM buyer cares about. `docs/COVERAGE.md` says so in their
  vocabulary, not ours.

## Reproduce

Nothing to reproduce yet. When there is, every command lives in
[`docs/REPRODUCTION.md`](docs/REPRODUCTION.md) and the exit code of
`make validate` is the product.

## Layout

| Path | What |
|---|---|
| [`CONTRACTS.md`](CONTRACTS.md) | Frozen definitions. Nothing changes without a DECISIONS entry and evidence. |
| [`docs/PRE-REGISTRATION.md`](docs/PRE-REGISTRATION.md) | Frozen before `src/`. Hypotheses, estimators, falsification conditions, power rule. |
| [`docs/ETHICS.md`](docs/ETHICS.md) | What is published, what never is, and why. |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Append-only. Decision / rationale / evidence / rejected alternatives. |
| [`docs/RED-TEAM.md`](docs/RED-TEAM.md) | Attacks on this repository's own claims. |
| [`docs/COVERAGE.md`](docs/COVERAGE.md) | What this instrument cannot see. |

## Contact and rectification

If you appear in this corpus and want out, write to the address in
`docs/ETHICS.md` section 6. The request is honoured within 7 days, you do not
have to explain why, and the removal is recorded as a count and never as an
identity.

## Licence

Code under the LICENSE in this repository. The corpus is derived from US
Government public-domain records and is published as pointers, not as records.
