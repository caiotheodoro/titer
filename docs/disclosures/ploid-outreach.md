# DRAFT: outreach to Ploid

**Status: DRAFT. NOT SENT.** House rule inherited from `assay`: draft it, show
it, decide separately. Nothing goes out without an explicit decision.

The blocker recorded in the previous version ("this must link to a public
repository") is **resolved** — the repo, both corpora, the Space and the
collection are public.

---

## The short version, for a cold send

**Subject:** Five budgets trying to benchmark you, no number published, one
result you might want

Hi —

I spent five rounds of credit trying to benchmark Ploid against SEC filings.
**Every one died on a defect in my harness, so I have published no number about
you** — not a poor one, not any. The write-ups of my own failures are public:
[R001](https://github.com/caiotheodoro/titer/blob/main/docs/RETRACTIONS.md).

Along the way I ran an experiment that I think is worth your time, because it
prices something your filter set cannot currently express.

**The question.** When a name collides, can the caller hand the index the one
fact that disambiguates — *who the person used to work for*? Your documented
filters are `title`, `seniority`, `company`, `industry`, `location`. Every one
describes a person's **current** state.

**The measurement.** Four renderings of the identical task, compared within
task, n=80 per collision band. Naming the person's **past** employer in free
text moved the correct rate:

| Name collision degree | name alone | + past employer |
|---|---|---|
| 1 (unique) | 0.2375 | 0.3500 |
| 2–3 | 0.0500 | 0.2000 |
| 4–9 | **0.0000** | 0.1875 |
| 10+ | **0.0000** | 0.2875 |

All four differences exclude zero on a paired bootstrap. A colliding name with
no biographical context is **0 of 80** — not merely harder, unresolvable.

I had logged the opposite as a hypothesis (that such a surface *cannot* exploit
history). The experiment **falsified my own hypothesis**, which is why I think
the finding is worth something: history is usable, and there is currently no
field to put it in.

**Three things I learned about querying your API, free:**

1. **Asked properly, the index finds people.** `{"query": "George Reyes",
   "filters": {"company": "Google"}}` returns the right George Reyes at the top.
   My early failures were malformed queries, not missing people.
2. **Free-text "formerly at X" is matched literally.** Querying
   `"Kelly Nima, formerly at GoDaddy"` returned a geodesist at *"NGA formerly
   NIMA"* and a manager at *"PERSOL (formerly known as Kelly Services)"*. The
   scaffolding of the query matched company-history text.
3. **Company tokens can outrank the name.** `Michael Anzilotti Access National`
   returned two other people at that company; `Michael Anzilotti` alone returned
   him at rank 1.

**On the `company` filter specifically:** on colliding names it resolved 3 of 12
where a bare name resolved 0, so it earns its place. But it selects people
*currently* there, so it answers "who is there now" rather than "where did they
go" — which is why I could not use it to score a move.

If it is useful, I would rather run the Ploid arm properly than leave it
retracted. The harness and task set are frozen and pre-registered; a ±0.10
half-width needs n=49 per arm, about **$10** at the measured $0.20 per search.
Whatever it says gets published, including if it flatters you.

Either way the work is public and I am happy to be told where I have it wrong.

— Caio

- Repo: https://github.com/caiotheodoro/titer
- Findings: https://huggingface.co/spaces/caiotheodoro/titer
- The experiment above: `docs/DECISIONS.md` D039, `docs/BENCHMARK.md` E2

---

## Notes for the sender, not part of the email

- **Do not claim any Ploid measurement. There is none**, after five budgets.
- The E2 result was measured on an **answer engine**, not on Ploid. It shows the
  *value of the missing input*, not that Ploid would behave the same way. If a
  reply treats it as a measurement of Ploid, correct it immediately.
- The within-Ploid arm was n=12 per rendering with **0 correct in both**. It is
  far too small to claim anything and is described as such (D040).
- `docs/RETRACTIONS.md` is the strongest credibility artefact here. Link it
  rather than hiding it.
- If they grant credit, say up front that the run is pre-registered and the
  result publishes whichever way it goes.
- Their Terms are the most permissive of the five vendors surveyed and expressly
  permit automated access through documented APIs. Worth acknowledging; it is
  why theirs was the arm that could be attempted at all.
