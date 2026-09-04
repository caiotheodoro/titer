# BENCHMARK

Results. Two findings survive attack; the rest is unmeasured, void, or retracted.

---

# E1 — expertise verification (the headline)

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
0.1500 [0.1214, 0.1840] — though that pooled figure mixes two tiers in a
proportion we chose, so the per-tier rates are the reportable ones.

It is not that the provider is bad at the task. It is specifically bad at
saying *no*.

Under the `expert_sourcing` profile (CONTRACTS A5, a 150x false-merge ratio
grounded in observed sourcing bounties of $250-$15,000 against an infiltration
incident and a breach), expected loss is **19.8** and **25.2** on the false
strata against **0.04** on attested. The asymmetry is the entire result.

## This number survived two independent attacks

| | FAR | NEAR |
|---|---|---|
| Raw, contaminated corpus (**retracted**, R002) | 0.1875 | 0.2212 |
| Post-hoc, net of measured contamination | 0.1832 [0.1348, 0.2442] | 0.1751 [0.1262, 0.2379] |
| **Confirmatory, verified negatives** | **0.1320 [0.0956, 0.1796]** | **0.1680 [0.1268, 0.2193]** |

The post-hoc correction slightly **over**stated FAR — its point estimate sits
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
| NEAR — adjacent subfield | 0.1680 [0.1268, 0.2193] |
| FAR — adjacent field | 0.1320 [0.0956, 0.1796] |
| **CONTROL — different domain** | **0.0840 [0.0556, 0.1250]** |

**NEAR is exactly 2.00x the control and the intervals do not overlap.** Topic
distance changes the rate; D031's two tiers were too close together to resolve
it, not wrong in principle. FAR still does not separate from the control, so the
gradient is only visible at the extremes.

**And the control is not zero: 21 of 250 absurd claims were affirmed, one in
twelve.** That floor is the more important number, because it is the one no
generous reading explains — see RED-TEAM A12, now bounded rather than open. At
least 8.4 of the 16.8 points is genuine error.

An earlier version of this file said "negative difficulty does not detectably
change the false-affirmation rate". That was true of NEAR versus FAR and wrong
as a general claim. See `docs/DECISIONS.md` D034.

## E3 — calibration, on clean labels

Brier **0.1191**, ECE **0.1153**, ten bins, empty bins reported as empty.

**686 of 750 answers (91.5%) landed in the 0.9-1.0 confidence bin, at mean
confidence 0.987 against accuracy 0.889** — a ten-point overconfidence gap in
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
| `never_verify`, `always_deep_verify`, `abstain_always` | not run - require the R4 environment |
| untrained Qwen3-8B, GPT-5.6-mini | not run |
