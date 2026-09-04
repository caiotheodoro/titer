# BENCHMARK

Results. Two findings survive attack; the rest is unmeasured, void, or retracted.

---

# E1: expertise verification (the headline)

**Exa `/answer`, n=750, zero errors, $3.75, 2026-09-03.** Negatives verified
false against OpenAlex `/works` **before** the provider was asked, catch-all
topics excluded, stratified per `docs/PRE-REGISTRATION-EXPERTISE.md`.

| Stratum | n | `CORRECT` | **`FALSE_MERGE`** |
|---|---|---|---|
| `ATTESTED` | 250 | **0.9600 [0.9279, 0.9781]** | 0.0000 [0.0000, 0.0151] |
| `FALSE_far` | 250 | 0.8680 | **0.1320 [0.0956, 0.1796]** |
| `FALSE_near` | 250 | 0.8320 | **0.1680 [0.1268, 0.2193]** |

**The finding: Exa confirms real expertise 96% of the time and affirms claims
that are provably false roughly one time in seven.** Across both false tiers,
0.1500 [0.1214, 0.1840], though that pooled figure mixes two tiers in a
proportion we chose, so the per-tier rates are the reportable ones.

The provider is specifically bad at saying *no*.

Under the `expert_sourcing` profile (CONTRACTS A5, a 150x false-merge ratio
grounded in observed sourcing bounties of $250-$15,000 against an infiltration
incident and a breach), expected loss is **19.8** and **25.2** on the false
strata against **0.04** on attested.

## This number survived two independent attacks

| | FAR | NEAR |
|---|---|---|
| Raw, contaminated corpus (**retracted**, R002) | 0.1875 | 0.2212 |
| Post-hoc, net of measured contamination | 0.1832 [0.1348, 0.2442] | 0.1751 [0.1262, 0.2379] |
| **Confirmatory, verified negatives** | **0.1320 [0.0956, 0.1796]** | **0.1680 [0.1268, 0.2193]** |

The post-hoc correction slightly **over**stated FAR. Its point estimate sits
above the confirmatory interval's centre, though the intervals overlap. That is
worth stating: a post-hoc correction is weaker evidence than a clean
measurement, and here it was measurably so.

## The difficulty axis exists, and it has a floor

A third tier settled it. `FAR_DOMAIN` is a **control**, not a difficulty step: a
topic from a wholly different OpenAlex domain, so an organometallic chemist is
asked about historical studies on Spain. n=250, matched `ATTESTED` arm on the
same authors at 0.9840 [0.9596, 0.9938].

| Tier | False affirmation |
|---|---|
| NEAR, adjacent subfield | 0.1680 [0.1268, 0.2193] |
| FAR, adjacent field | 0.1320 [0.0956, 0.1796] |
| **CONTROL, different domain** | **0.0840 [0.0556, 0.1250]** |

**NEAR is exactly 2.00x the control and the intervals do not overlap.** Topic
distance changes the rate; D031's two tiers were too close together to resolve
it, not wrong in principle. FAR still does not separate from the control, so the
gradient is only visible at the extremes.

**And the control is not zero: 21 of 250 absurd claims were affirmed, one in
twelve.** No generous reading of the prompt explains those 21 affirmations, so at
least 8.4 of the 16.8 NEAR points are genuine error. That bounds RED-TEAM A12
rather than leaving it open.

An earlier version of this file said "negative difficulty does not detectably
change the false-affirmation rate". That was true of NEAR versus FAR and wrong
as a general claim. See `docs/DECISIONS.md` D034.

## E3: calibration, on clean labels

Brier **0.1191**, ECE **0.1153**, ten bins, empty bins reported as empty.

**686 of 750 answers (91.5%) landed in the 0.9-1.0 confidence bin, at mean
confidence 0.987 against accuracy 0.889**, a ten-point overconfidence gap in
the bin holding nearly all the mass. Confidence is effectively pinned at
ceiling and does not track correctness there.

Measured against the earlier contaminated labels this gap read 12.5 points; it
shrinks on clean labels, because the provider was right more often than the
contaminated labels credited. The smaller number is the correct one.

---

# Employment study

One run has produced numbers; everything else is unmeasured or void.

**Measurement window:** 2026-09 (as of 2026-09-03). Seed 11,
simple random sampling from the 46,332-task corpus. Zero provider errors.

**The pre-registered power branch is `cannot_separate`** for any cross-provider
claim, and no ranking language appears anywhere in this file.

---

## The one result that survives scrutiny: Exa `/answer`, n=299

| Outcome | n | Rate, 95% Wilson |
|---|---|---|
| `CORRECT` | 176 | **0.5886 [0.5321, 0.6429]** |
| `STALE` | 44 | 0.1472 [0.1115, 0.1918] |
| `MISS` | 79 | — |
| **`FALSE_MERGE`** | **0** | **0.0000 [0.0000, 0.0127]** |

Cost: $1.495, or $0.0050 per task. Resolution was unambiguous on 245 of 299
(`unique_name`); only 6 answers named someone absent from the corpus.

**The false-merge bound is the first genuinely tight number this project has
produced.** At n=299, a confident wrong identity occurs at under **1.3%** on
this population. Exa's failures were `MISS` and `STALE` - it declined or
returned the wrong employer for the right human - and never once confidently
named a different person.

That is a null result on H2's headline, and it is reported as prominently as a
positive one would have been.

## E2: a capability constraint DOES disambiguate, and D029 is falsified

Pre-registered falsification condition: *"falsified if the free-text capability
arm beats the name-alone arm - the semantic query field already absorbs
biographical context, and the architectural gap D029 asserts does not exist in
practice."*

**It beats it, in all three colliding bands, with paired intervals excluding
zero.** Exa `/answer`, n=80 per band, four renderings of the identical task set,
within-task comparison, seed 23, $3.60.

| Band | A: name alone | C: + past employer, free text | D: + full anchor context |
|---|---|---|---|
| `unique` (degree 1) | 0.2375 [0.1576, 0.3414] | 0.3500 [0.2545, 0.4592] | 0.4625 [0.3575, 0.5710] |
| `low` (degree 2-3) | 0.0500 [0.0196, 0.1216] | **0.2000** [0.1270, 0.3005] | 0.3375 [0.2435, 0.4464] |
| `medium` (4-9) | **0.0000** [0.0000, 0.0458] | **0.1875** [0.1171, 0.2866] | 0.2750 [0.1892, 0.3814] |
| `high` (>=10) | **0.0000** [0.0000, 0.0458] | **0.2875** [0.1999, 0.3946] | 0.3000 [0.2106, 0.4077] |

Paired differences, 10,000 resamples, seed 11:

| Contrast | `unique` | `low` | `medium` | `high` |
|---|---|---|---|---|
| C - A | **+0.1125** [0.0250, 0.2000] | **+0.1500** [0.0750, 0.2375] | **+0.1875** [0.1000, 0.2750] | **+0.2875** [0.1875, 0.3875] |
| D - A | +0.2250 [0.1250, 0.3375] | +0.2875 [0.1875, 0.3875] | +0.2750 [0.1750, 0.3750] | +0.3000 [0.2000, 0.4000] |
| D - C | +0.1125 [0.0250, 0.2000] | +0.1375 [0.0500, 0.2250] | +0.0875 [0.0000, 0.1750] *ns* | +0.0125 [-0.0625, 0.0875] *ns* |

**C - A separates in all four bands**, colliding and not, and the effect grows
with collision degree: +0.11 where names are unique, +0.29 where they collide
most. Context helps everywhere and helps most where it is most needed.

**Three things this says.**

1. **The hypothesis was ours and it is wrong.** D029 argued a people-search
   surface cannot be handed a biographical constraint. On an answer engine it
   plainly can: naming the past employer in free text moves the correct rate
   from 0.05 to 0.20, and from **zero** to 0.19 and 0.29 at the two harder
   collision bands.
2. **Nearly all of the benefit is the employer name alone.** `D - C` separates
   at `unique` and `low` but not at `medium` or `high`. Adding the attested date
   and the role class on top of the company buys nothing measurable once names
   actually collide - exactly where a caller would most want it to.
3. **A colliding name with no context is unresolvable.** At `medium` and `high`,
   arm A is **0 of 80**. That is the ceiling a name-only query has against this
   population, and it is the number that makes the other arms interpretable.

**Scope, stated rather than assumed.** D029 is a claim about people-search
indexes with **structured filters** - Ploid's documented `title`, `seniority`,
`company`, `industry`, `location`, every one a current-state field. Exa
`/answer` is an answer engine, a different surface, and falsifying the claim
there does not falsify it for a filter-based index. Arm B is the within-provider
test on the surface the hypothesis was actually about.

**Per-stratum only.** D027's pooling ban applies and no pooled rate is given.
D032 applies too: a colliding sample is deliberately enriched, case-control, so
**no collision rate here is a population rate**.

### E2 arm B: the filter-based surface, where D029 was actually aimed

Ploid, within-provider, `medium` band, n=12 per arm, paired, $4.00. **Both arms
scored 0 correct**, so no accuracy claim is made and none can be.

| | A: name only | B: name + documented `company` filter |
|---|---|---|
| correct | 0.0000 [0.0000, 0.2425] | 0.0000 [0.0000, 0.2425] |
| `STALE` (anchor returned) | 0 | **2** |
| resolved (`unique_name` + `narrowed_by_anchor`) | **0** | **3** |
| `colliding_name_no_employer` | **11** | 0 |

**Read the resolution column, not the outcome column.** With the name alone,
11 of 12 queries returned people whose employer Ploid did not give, so the
collision could not be broken and nothing could be scored. With the filter, 3
resolved - and 2 of those came back as `STALE`, meaning the row returned was
the **anchor**, which is what D028 C1 predicted a current-state company filter
would do.

So on this surface the filter buys resolution and spends it on the wrong
answer. That is consistent with D029's argument, and **consistency at n=12 with
zero correct answers in both arms is not evidence.** The paired interval reads
`0.0000 [0.0000, 0.0000]` only because both arms are uniformly zero; it is
degenerate and must not be read as "no difference".

**What it would cost to know:** 49 tasks per arm for a ±0.10 half-width at
p=0.15, which is **$9.80 per arm** at the measured $0.20 per search. This
budget bought 12.

**Five budgets, no Ploid accuracy number.** That remains the honest state.

## H2: false merges are NOT measurable here, and the strata were never the budget

`MEASUREMENT_CARD.json` carried *"H2 false merge under name collision: strata
empty by construction"* for the life of the project. The cause was the sampling,
not the money: a random draw put 251 of 299 observations into one collision band
(D027). E2 drew **n=80 in every band** because a within-task design needs equal
allocation, so H2 resolved for **$0** from observations collected for another
hypothesis.

`exa_D_full_context`, held constant across bands, n=80 each:

| Band | `FALSE_MERGE` | raw Wilson | net of the 12.76% contamination bound |
|---|---|---|---|
| **`unique` (d=1)** | **3/80** | 0.0375 [0.0128, 0.1045] | **[0.0128, 0.1045]** |
| `low` (2-3) | 0/80 | 0.0000 [0.0000, 0.0458] | **[0, 0]** |
| `medium` (4-9) | 1/80 | 0.0125 [0.0022, 0.0675] | **[0, 0]** |
| `high` (>=10) | 0/80 | 0.0000 [0.0000, 0.0458] | **[0, 0]** |

The contamination bound applies only to colliding names, where one human may
hold two registrations; a unique name has no such ambiguity, so nothing is
subtracted from its interval.

**H2 is falsified on "flat in `d`", which the pre-registration makes sufficient
on its own.** But the rate is not flat - it is **inverted**: 0.0375, 0.0000,
0.0125, 0.0000. False merges are most likely where names **do not collide**, and
effectively absent where they do.

The mechanism is in the resolution column. On a colliding name the provider
mostly cannot name anyone the resolver can pin, so the outcome is `MISS` rather
than a wrong identity: **it never gets the chance to be confidently wrong.**
Collision does not make this surface merge the wrong person more often, it makes
it stop answering. The danger sits where nobody stratifies for it - the easy,
unique-name cases where an answer comes back and looks clean.

H2 was the hypothesis most likely to yield an alarming, quotable number about a
commercial product. It is not true here, and the pre-registration commits to
saying so as prominently as the opposite.

**The caveat that limits its reach.** The identity atom is scored only when the
name alone pinned the person (D024), and on colliding names `resolve`
structurally cannot return `unique_name`. Most outcomes are `MISS`: the provider
mostly fails to name anyone resolvable rather than naming the wrong one. A
surface that answered more confidently could behave differently, and that is not
measured here.

## What does NOT hold

### The web floor is not measured. It is a parser artefact.

`webfloor` scored 0/300. It is not evidence that free web search cannot find
these people. Exa `/search` returns page titles, and our floor tries to read a
person out of the title alone. The parsed "names" are what you would expect:

```
'IDACORP Announces Election of Michael J. Kennedy to ...'
'FORM 8-K 10.04.2013'
'exv10w82'
'Ownership Information: PAR PACIFIC HOLDINGS, INC.'
```

256 of 300 resolved as `name_not_in_corpus`. What was measured is "can a person
be resolved from a search-result title, without reading the page" - answer:
essentially never. That is a weak floor, not the floor D020 requires, and the
0.0000 must not be quoted as one.

### H1's staleness curve is not measurable from a random sample.

730-infd holds **272 of 299** observations. A random
draw from a twenty-year corpus puts nearly everything in the far tail:

| Elapsed since filing | Reflected | n |
|---|---|---|
| 30-90d | 0.3333 [0.0615, 0.7923] | 3 |
| 90-180d | 0.5455 [0.2801, 0.7873] | 11 |
| 180-365d | 0.6667 [0.2077, 0.9385] | 3 |
| 365-730d | 0.7000 [0.3968, 0.8922] | 10 |
| >730d | 0.5882 [0.5289, 0.6451] | **272** |

The reported median lag of **99 days** comes from an isotonic fit dominated by a
single bin, with three of the five populated bins holding ten observations or
fewer. **It is not a staleness half-life and must not be cited as one.** H1
needs stratification by elapsed time, exactly as H2 needed stratification by
collision degree (D027). The same mistake, on a different axis, found the same
way - by looking at where the observations actually landed.

### Collision-degree stratification is absent here.

Random sampling put 251 of 299 tasks in the `unique` band and 2 in `high`. The
per-band false-merge cells are empty by construction. H2's "increasing in d"
claim is untouched by this run.

### Ploid is unmeasured.

Three runs, three harness defects, no surviving number. See
`docs/RETRACTIONS.md` R001 and `docs/DECISIONS.md` D028.

### The prompt used here is the pre-D028 form.

This run asked for the employer **on a specific past date**. D028 established
that a current-state index cannot fairly answer that, and restricted the task
population accordingly. Exa `/answer` is a research engine and can answer dated
questions, so the run stands for Exa - but it is **not comparable like-for-like**
to any arm measured under the D028 prompt.

---

## Baselines

| Arm | Status |
|---|---|
| `exa` `/answer` | measured, n=299 |
| `webfloor` | run, but the number is a parser artefact - not a valid floor |
| `ploid` | RETRACTED, unmeasured |
| `never_verify`, `always_deep_verify`, `abstain_always` | **measured** on the simulator fitted to 485 real observations |
| trained policy | **measured**, 6 seeds, frozen split |
| untrained Qwen3-8B, GPT-5.6-mini | not run |

### R4: the floors, corrected

Three reward defects were found before training (D037). Two of them inflated the
active floors, so the numbers published before this were wrong:

| Floor | Published | Corrected | mean spend |
|---|---|---|---|
| `never_verify` | 0.0455 | **-0.2292** | $0.005 |
| `always_deep_verify` | 0.0277 | **-0.2574** | $0.015 |
| `abstain_always` | -0.1000 | **-0.1000** | $0.000 |

`never_verify` still beats `always_deep_verify`, so **"spending 3x more bought
marginally fewer correct answers" survives the correction**. What does not
survive is the ordering against doing nothing: at a 37% solve rate under
`gtm_outbound`, answering is negative expected value and **`abstain_always` is
the floor to beat**.

### R4: the trained policy

A 130-parameter linear-softmax policy, SFT warm start on rejection-sampled
passing trajectories, tasks filtered to the 10-80% solve band, then GRPO with
group-relative advantage. Checkpoint selected on hill-climb, never on the frozen
split. Rollouts are free against the fitted simulator, which is what makes six
seeds affordable.

| | value |
|---|---|
| trained policy, mean over 6 seeds | **0.0461** |
| baseline `abstain_always` | -0.1000 |
| margin | 0.1461 |
| across-seed SD | **0.0122**, 0.08x the margin |
| verdict | **CLAIM** |

Per-seed frozen-test scores: 0.0411, 0.0411, 0.0411, 0.0711, 0.0411, 0.0411.

It beats `abstain_always` under all five cost profiles. **Absolute rewards are
not comparable across profiles** - the reward normalises by
`max(profile.values())`, so a profile carrying a 150x false-merge cost compresses
every term - but the sign and the within-profile ordering are.

**What it learned, and what it did not.** It queries once, then **abstains on
41.7%** of tasks, lifting precision on the answered subset from the 37% base rate
to **64%**. That is genuine selectivity.

It then states **confidence 1.0 on every answer it gives**, at 64% accuracy.
That is the same failure E3 measured in the provider - confidence pinned at
ceiling, carrying no information - now reproduced by our own policy in an
environment that prices exactly that. A calibrated policy would state about 0.64
and score better; this one leaves roughly 0.04 of reward on the table.

Reporting only the margin would have hidden the more interesting half.
