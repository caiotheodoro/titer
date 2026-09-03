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
