# RETRACTIONS

Exists from W0, empty, on purpose.

If a published number in this repository is later found to be wrong, the
correction is recorded here **and** placed next to the original claim in the
README — not in a footnote, not silently edited away.

The house rule, learned expensively elsewhere: keep the unflattering number in
the README. A sibling repository still leads with a headline and retracts it in
a box directly underneath, because deleting the headline would have hidden the
more useful finding, which was that the retraction happened at all.

Format for an entry:

```
## R00n — <the claim being retracted> (<date>)

**Originally published:** <the exact claim, quoted>
**Where:** <file and section>
**What was wrong:** <the defect>
**How it was found:** <the probe, test, or reviewer>
**Corrected claim:** <the replacement, or "no claim">
**What changed to prevent recurrence:** <gate, test, or contract change>
```

## R001 - The Ploid arm of the W3 stratified run is void (2026-09-03)

**Originally measured:** Ploid 0 correct out of 21 tasks; accuracy 0.000; every
outcome a `MISS`. Exa 10/24 correct on the identical task set.

**Where:** `results/full_run.json`, stratified run, 2026-09-03. Never published
outside the repository.

**What was wrong:** the harness, not the provider. `Ploid.render` packed the
person's name and their employer into a single free-text `query` string, e.g.
`"REYES GEORGE GOOGLE INC."`. Ploid's search endpoint documents **structured
filters** - `title`, `seniority`, `company`, `industry`, `location` - and the
free-text field is not where a company belongs. The measurement therefore
scored our wire format, not their index.

**How it was found:** by attacking our own most dramatic result before reporting
it. A 0/21 against a commercial product is the highest-stakes claim this project
could make, so the returned rows were read verbatim first. Ploid was returning
the *right names* attached to eponymous small businesses - "Mark Smith" at "Mark
Smith Inc.", "Richard Walker" at "Richard Walker West Inc." - which is what a
badly-shaped query does, not what a missing person looks like.

One structured query settled it. `{"query": "George Reyes", "filters":
{"company": "Google"}}` returns **"George Reyes" at "google"** as the top
result, from `ploid_people_index`. The same person, through the free-text
rendering, returned `"Google Inc." @ "5th Wall Design"`.

**Corrected claim: none.** The Ploid arm is `NOT_VERIFIED`. The $5 grant was
exhausted at $4.60 before the defect was found, so it cannot be re-run at this
budget. Reporting 0/21 with a footnote would have been worse than reporting
nothing: the headline number would have travelled and the footnote would not.

**Unaffected:** the Exa and web-floor arms. Both were rendered in the shape
their own APIs document - `/answer` takes a question, `/search` takes a query
string - and neither depends on the Ploid path.

**What changed to prevent recurrence:**

1. `Ploid.render` returns a structured request, not a string, and uses the
   documented `filters` field.
2. A test asserts every adapter's rendering exercises the structured fields its
   API documents, so "we used the wrong shape" fails the build rather than
   waiting for someone to read the rows.
3. `docs/HANDOFF.md` gains the rule this cost us: **before spending a budget on
   an arm, run one task through it and read the returned rows verbatim.** A
   pilot that only counts outcomes cannot tell a bad query from a bad index.

**The uncomfortable part, recorded deliberately.** This is the exact failure the
project exists to name in other people's work. The vendor comparisons surveyed
in `docs/SURVEY.md` put the same provider at 42.4% and 78% with no methodology
published; a harness defect of precisely this kind is the most likely
explanation for a spread that size. We produced one, and the only reason it is
not in a results table is that the retraction step was built before the
measurement was.


## R002 - The raw E1 false-affirmation rates are retracted; the NET rates stand (2026-09-03)

**Originally measured:** Exa affirmed constructed-false expertise claims at
17.25% (FAR) and 21.00% (NEAR), n=400 per stratum, against 96.75% correct on
attested claims. Never published outside the repository.

**Where:** `results/expertise_e1.json`, 2026-09-03.

**What was wrong:** the negatives. A constructed-false claim was defined as a
topic absent from the author's OpenAlex `topics` field - which is a **top-N
summary**, median 5 topics for authors with roughly 120 works, not an exhaustive
record. "Absent from the top five" is not "never published in".

**How it was found:** by reading the evidence strings behind the affirmations
before reporting the number. They kept looking correct. Catarina Kiefe was
affirmed for "Educational Methods and Outcomes" and has co-authored medical
education research; Agostino Virdis for "Obesity and Health Practices" and
publishes on endothelial dysfunction in obesity; J. C-L. Tseng for "Radioactive
Decay" and works on SNO+ neutrinoless double beta decay. Those are not
hallucinations. They are correct answers scored as errors.

**Measured contamination**, against `/works`, which is exhaustive:

| Tier | Contaminated | Raw affirm | **NET, verified-false only** |
|---|---|---|---|
| FAR | 8.17% [5.17, 12.70] | 18.75% [14.03, 24.60] | **18.32% [13.48, 24.42]** n=191 |
| NEAR | 18.43% [13.84, 24.13] | 22.12% [17.11, 28.10] | **17.51% [12.62, 23.79]** n=177 |

**Corrected claim: the NET rates stand.** Restricting to claims verified false
against `/works`, Exa affirms them at roughly **18%**, and both intervals
exclude zero by a wide margin. This is the first headline number in this project
to survive an attack on it.

**Two things the correction destroyed, and they matter:**

1. **The difficulty axis.** Raw, NEAR (22.12%) looked worse than FAR (18.75%),
   which is what D031 predicted. Net of contamination they are
   indistinguishable - 17.51% against 18.32%. **The entire apparent effect of
   negative difficulty was contamination**, because a same-field topic is
   exactly where a stray paper hides: NEAR contamination is 2.3x FAR's. D031's
   FAR tier was built as the control that would show whether the axis was doing
   work. It showed the axis was not.
2. **Any reading of the raw NEAR number.** At 18.43% contamination against a
   22.12% raw rate, the raw NEAR figure is almost entirely explained by our own
   construction.

**What changed to prevent recurrence:** `adjacent_false_topic` now takes a
`verify` callable, hits `/works` per candidate, and returns None rather than
falling back to a contaminated negative. Catch-all OpenAlex labels are excluded
- "Diverse Scientific Research Studies" was among the first false claims
affirmed, and a negative nobody can be wrong about measures nothing. Four tests
cover it.

**Still open, and stated rather than resolved:** the NET figures are a post-hoc
correction on a sample whose catch-all topics were not filtered, and only 425 of
800 measured tasks completed the paired check. A confirmatory run on a
verified, catch-all-free corpus is the right evidence and is budgeted; it is
blocked until the OpenAlex daily budget resets.
