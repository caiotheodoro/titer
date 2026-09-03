# BENCHMARK

Results. One run has produced numbers; everything else is unmeasured or void.

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
