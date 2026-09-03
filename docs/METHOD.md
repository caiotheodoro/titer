# METHOD

How a claim in this repository gets made, and what stops a bad one.

## The one-sentence method

Find a question about people-search quality whose ground truth is a **program**
rather than an opinion, measure it under a **cost** the caller actually bears,
and publish the **interval** rather than the point.

## Why a filing and not a judge

The obvious way to evaluate a people-search index is to ask a strong model,
armed with web search, whether the returned person matches the query. That is
what the best existing benchmark does, carefully, with a judge validated at
kappa = 0.84 against human annotators.

It has a structural problem that no amount of judge validation fixes. The judge
verifies against the same public web the provider searched. A person the web
indexes poorly is scored as "not found" for the provider *and* unverifiable for
the judge, so the two errors are correlated and the benchmark cannot see its own
blind spot. Its authors say so.

A filing breaks the correlation. Section 16 of the Securities Exchange Act
compels an officer or director to state, by name, that they held a role at an
issuer on a date. The SEC assigns the filer an identifier and publishes the
record. Whether a provider found that person has nothing to do with whether the
fact is true, because the fact was established by a legal obligation rather than
by web presence.

This buys three things a judged oracle cannot:

1. **Correctness is a comparison, not an inference.** Did the returned identity
   resolve to this CIK: yes or no.
2. **Hard negatives that provably exist.** Two filings with the same name and
   different CIKs are different registrations, by construction. False merges
   become measurable instead of arguable.
3. **A timestamp.** The filing date is when the fact became public. Index lag is
   the difference between that and when the index reflects it.

## Why cost, and not accuracy

Accuracy treats every error as one error. The callers of these APIs do not.

Naming the wrong human costs a recruiter an awkward email, and costs a
sanctions-screening pipeline or a journalist something that cannot be undone by
apologising. A missed person costs everyone roughly the same small amount. So
the error that dominates real loss is the one that accuracy weighs least
distinctively.

We therefore report expected loss under four named cost profiles and treat
**stability of the ranking across profiles** as the finding. A ranking that
survives all four is a strong claim. A ranking that flips is more interesting
than a win, because it tells a buyer that the right provider depends on what
their errors cost - which is the actual decision they face.

A `flat` profile, where every error costs the same, exists only as an integrity
probe: under it the expected-loss ranking must equal the accuracy ranking, and
if it does not the harness has a bug.

## Why an interval, and why the power rule is pre-committed

The published comparisons in this category put the same provider at 42.4% in one
study and 78% in another. Neither reports an interval. Both were published by
competitors.

The budget here is $5. That is a real constraint and it cannot be argued away,
so `docs/PRE-REGISTRATION.md` section 3 fixes **in advance** what we are
permitted to say at each achievable sample size, including the branch where the
answer is "this budget cannot separate these providers, and here is the `n` that
could." Committing to that rule before seeing the data is the only thing that
stops a disappointing `n` being rationalised into a ranking afterwards.

All comparisons are **paired**: every provider receives the identical task set
in the identical order, and differences are computed within-task by bootstrap.
Pairing is what makes a small `n` worth anything.

## Where a model is allowed to act, and where it is not

The boundary is fixed and it is the same boundary a sibling project measured the
hard way: **the script owns mechanism, the model owns meaning.**

| Step | Who decides |
|---|---|
| Which quarters, which rows enter the corpus | program (`CONTRACTS.md` 2.1) |
| `role_class` | the filing, parsed |
| `title_class` | frozen regex, versioned, no model |
| Mapping a provider's identity to a CIK | frozen deterministic rule, no model |
| Outcome class | program |
| Reward atoms | program |
| Which paid call to make next | **the policy under test** |

A model never assigns a ground-truth label anywhere in this repository. The one
place a model makes a decision is the place we are measuring: whether to spend.

## The environment

R4 is an OpenEnv environment with a `keel`-protocol facade. The agent is handed
a task derived from an attested tuple, a set of priced actions, and a budget.
It ends the episode by naming an identity with a confidence, or by abstaining.

Reward is three program-checked atoms, minus what was spent, minus a heavy
penalty for being confidently wrong, plus a small credit for abstaining
correctly. There are **no shaping terms**: no credit for searching, for
narrowing candidates, or for "checking the evidence". Shaped exploration
produces performative exploration.

Before any training run, the environment must pass a health gate: gold
trajectories score 1.0, a no-op agent scores 0.0, inverted labels collapse the
score, the flat-profile probe passes, and the solve-rate histogram shows enough
tasks in the 10-80% band to give GRPO something to normalise against. No health
report, no training run.

## Training on a simulator, evaluating on reality

Live rollouts at $5 a verification are arithmetically impossible, so the policy
trains against a cost/error simulator fitted to the small real sample and is
**evaluated on held-out real calls**. The gap between simulator-evaluated and
real-evaluated performance is measured and published as a number.

This is the central limitation of R4 and it is stated in the README rather than
discovered by a reader.

## What stops a bad claim

- `CONTRACTS.md` is frozen; changing a definition requires a DECISIONS entry
  **and** measured evidence.
- `docs/PRE-REGISTRATION.md` is frozen before `src/` exists, its hash published
  publicly at W0, and it is never edited - only superseded by a dated entry that
  states the counterfactual.
- Claim gates in `tests/` assert that every cited path resolves, that the
  advertised suite size equals the collected test count, and that every cited
  path is tracked by git.
- `docs/RED-TEAM.md` attacks this repository's own findings.
- No training margin is quoted without its across-seed spread.
- `MEASUREMENT_CARD.json` reads `NOT_VERIFIED` until every gate passes. A card
  that always exits zero is decoration.
