# RED-TEAM: attacks on this repository's own claims

Written at W0, before there are results to defend. Each attack gets a status:
**LIVE** (a real weakness we carry), **MITIGATED** (with the mechanism named),
or **OPEN** (we do not yet know).

---

## A1. "Your ground truth is not a person key." · LIVE

`RPTOWNERCIK` is unique per filer *registration*. A human who registered twice
holds two CIKs and the SEC publishes no merge table. So a provider we score
`FALSE_MERGE` may have correctly found the same human under a second
registration.

**Status: LIVE, bounded.** The direction we depend on is sound - different CIK
proves different registration - and that is what false-merge detection rests on.
The reverse is presumptive. We measure an upper bound (distinct CIKs sharing an
exactly-normalized name *and* an overlapping issuer) and report false merges raw
and net of it. If the bound turns out to be large, the R2 claim weakens
proportionally and we say so in the README.

## A2. "Executives are the easy case, so your numbers flatter the providers." · LIVE

Section 16 filers have unusual web presence. Providers should do better on them
than on a representative target.

**Status: LIVE and deliberately unrebutted.** Any error rate we measure is
plausibly a **lower bound** on what a buyer experiences. That direction is the
safe one for a critical finding: if providers fail here, they fail worse
elsewhere. It does mean no measured *success* rate generalises, and
`docs/COVERAGE.md` says so.

## A3. "Cross-sectional staleness is not staleness." · LIVE

R1 infers a survival curve from one snapshot across many elapsed-day values,
rather than watching a record update.

**Status: LIVE.** A provider that back-fills historical records would appear
fresher than it is, and we cannot distinguish that from genuine freshness. The
mitigation is a forward panel, which is named in COVERAGE with its trigger. Until
then R1 measures "is the fact present now, as a function of how old it is",
which is a weaker claim than "how fast does the index update", and the README
must use the weaker wording.

## A4. "Your title normalization is a judgement call dressed as a program." · MITIGATED

Mapping `"President and CEO"` to a class is a decision, and decisions can be
tuned toward a result.

**Status: MITIGATED.** The map is regex-only, frozen as `title_map/v1`, and
versioned; the raw string is retained on every row; no model can reach the
module; unmatched titles become `UNKNOWN` and are excluded from the title atom
rather than scored in either direction. Residual risk: the regex set was written
by us, before seeing results, but by us. A reviewer should read
`src/titer/corpus/title_map.py` as an adversary.

## A5. "n = 50 cannot separate anything, so this is theatre." · MITIGATED

At the achievable budget the Wilson half-width may exceed 0.10.

**Status: MITIGATED by pre-commitment.** `docs/PRE-REGISTRATION.md` section 3
fixes, before data, what we may say at each `n`, including the branch where the
published result is "this budget cannot separate these providers, and here is
the `n` that would." The attack is correct that a small `n` limits the claim; it
is wrong that this is discovered after the fact.

## A6. "You excluded the providers that would have beaten Ploid." · MITIGATED

Apollo and PDL are absent, and Ploid is the lead subject.

**Status: MITIGATED, and worth checking.** Both exclusions are contractual, with
the prohibiting clause quoted verbatim in `docs/DECISIONS.md` D019, and
`docs/COVERAGE.md` states that the provider set is "who could be measured
lawfully", not "who matters". No provider is ever dropped for performing badly;
that rule is in the pre-registration. A reviewer should verify the quoted clauses
against the live Terms rather than trusting our quotation.

## A7. "The simulator is fitted to the same data you evaluate on." · MITIGATED

If it were, the sim-to-real gap would be unmeasurable.

**Status: MITIGATED by construction.** `src/titer/sim/` is fitted on the training portion
of the W2 cache only, the split is frozen in the pre-registration, and the
enforcement is a test rather than a convention. This is the single easiest thing
in the repository to get quietly wrong, so it gets an explicit failing test.

## A8. "The reward has a shaping term you did not notice." · OPEN

We claim zero shaping. Claims like that are usually wrong somewhere.

**Status: CLOSED, and it had landed.** See `docs/DECISIONS.md` D024 C4. There
was a flat abstention credit, and combined with a free provider it made stalling
to the turn cap pay exactly what abstaining immediately paid, and strictly more
than answering wrong - a shaping term rewarding delay. The credit is deleted;
abstention is priced by the cost profile like every other outcome.

The wider lesson is recorded in D024: four of the confirmed review findings were
defects in the *probes*, not in the thing being probed.

## A9. "You are measuring a vendor while asking them for a job." · MITIGATED

The stated outcome is publish-first then a link-first email proposing
collaboration.

**Status: MITIGATED by sequencing and by pre-commitment.** The pre-registration
fixes the hypotheses and the falsification conditions before contact, and
commits to publishing falsified hypotheses. `docs/DECISIONS.md` D017 records the
goal explicitly so that framing cannot drift toward flattery at wave 4. A
reviewer should check whether the README leads with the unflattering number; if
it does not, this attack has landed.

## A10. "A benchmark of real named people is itself the harm you are measuring." · LIVE, and answered

Aggregating scattered public facts about real people into one convenient file is
a privacy harm.

**Status: LIVE, and it is the reason for the pointer-only release.** We publish
accession numbers, CIKs, classes, dates and salted name hashes - never assembled
records, never contact fields, never provider response bodies. Anyone rebuilding
the corpus does so from the SEC's own files. `docs/ETHICS.md` section 5 states
the dual-use judgement plainly rather than hiding it, and section 3 declines to
buy contact data even where it would sharpen a result.

The residual: we still query commercial providers with real people's names. That
is unavoidable for the measurement to exist, it is within each provider's Terms,
and the responses are stripped of contact fields before they touch disk.

## A11. "Ploid's Terms disclaim accuracy, so there is no claim to test." · OPEN

Ploid §12: *"We do not warrant that outputs will be accurate, complete, or
suitable for any particular decision."*

**Status: OPEN, and it cuts both ways.** It is a fair objection to framing this
as catching a broken promise. It is also itself the finding: the marketing says
*"who someone is today, not who they were at the last crawl"* while the contract
warrants nothing. We must be careful to test the marketing claim as a factual
question, not as a breach - and a reviewer should flag any sentence in the README
that implies otherwise.

---

# Attacks on the expertise findings (added 2026-09-03)

## A12. "Your 16.8% is prompt interpretation, not error." · BOUNDED

The prompt asks *"Does X have published research expertise in T?"* A provider
may reasonably read that as "does X work in an area close to T", in which case
affirming an adjacent topic is a defensible answer to a vague question rather
than a false claim.

Bounded by a control tier, not closed. See `docs/DECISIONS.md` D034.

The worry was real and the confirmatory run could not address it: removing
*contaminated* negatives does not remove *adjacent* ones, and a provider might
defensibly answer "does X work near T".

A control tier settles the lower bound. Asked about a topic from a **wholly
different domain** - an organometallic chemist and historical studies on Spain -
the false-affirmation rate is **0.0840 [0.0556, 0.1250]**, n=250. No generous
reading rescues that. **At least 8.4 percentage points of the 16.8% is genuine
error**, and interpretation can account for at most the difference.

Still live: whether the remaining ~8pp is interpretation or error.

**The experiment is now built and it is cheaper than "budget" suggested.** Every
one of the 2,388 cached `/answer` responses already carries `answer.evidence` and
citations - mean 7.99 each, 1,984 with an author field. So the first half costs
**nothing**: for each affirmation, resolve the cited titles against OpenAlex and
ask whether any is a work that author actually wrote. An affirmation supported
only by a Google Scholar profile or a staff page cites no attested work, and
that is a fact about what was returned rather than a judgement about how the
question was read. No model reads the evidence string - a model assigning that
label is the circularity D022 bans.

`scripts/a12_citation_audit.py` does this and spends $0.

**It has not produced a number yet.** OpenAlex's account budget was exhausted
mid-run (both authenticated and unauthenticated requests returned
`$0 remaining ... resets at midnight UTC`), which cost the first attempt 175
audited affirmations because it only wrote results at the end. It now
checkpoints every 25 and stops cleanly on a rate wall. **A12 therefore stays
LIVE, with the residual still open and the tooling waiting on a quota reset
rather than on money.**

## A13. "The negatives are still constructed by you." · MITIGATED, not eliminated

Every negative is a topic with zero attested works, chosen by a versioned set
operation over the OpenAlex hierarchy, verified against `/works`, and stripped
of catch-all labels. Spot-checked at 0/150 contaminated [0, 0.0250].

**Residual:** adjacency is defined by OpenAlex's own taxonomy, so a defect in
that taxonomy propagates into ours. D031's difficulty tiers were *supposed* to
detect this and did not separate.

## A14. "E3's calibration is measured against your labels." · LIVE

The overconfidence gap (0.987 stated vs 0.889 actual) uses our correctness
labels. If those labels are wrong in the provider's favour, the gap shrinks -
which is exactly what happened when contamination was removed (12.5 points →
10 points).

**Status: LIVE and bounded.** The direction is known and the correction has been
applied once. A residual adjacent-topic bias would shrink it further. The claim
that survives is the weaker one: **confidence is pinned at ceiling on 91.5% of
answers and does not discriminate there**, which holds regardless of where
accuracy truly sits.

## A15. "H1's inverted U is your oracle, not the index." · LIVE, and we say so

Reflection rises 0.28 → 0.57 → 0.29. We argue the fall after three years is SEC
ageing out of reality rather than an index regressing.

**Status: LIVE, and it is our own explanation of our own result.** D033 states
it as a hypothesis and names the experiment (E4, over a population whose oracle
tracks people after they leave public companies). Not run. Until it is, H1 is
**mis-specified** - not confirmed, not falsified.

## A16. "One provider is not a benchmark." · LIVE

Every surviving number describes **Exa**. Ploid is retracted, the web floor is
a parser artefact, and no other provider was measured.

**Status: LIVE and unfixable at this budget.** Nothing here supports a claim
about the category. `docs/BENCHMARK.md` names one provider throughout, and the
pre-registered `cannot_separate` branch forbids ranking language regardless.

## A17. "You published the methodology because the results were thin." · answered

Six headline numbers, five artefacts. A reader may reasonably suspect the
framing is a rescue.

**Status: answered by the record, which is checkable.** `docs/RETRACTIONS.md`
and `docs/DECISIONS.md` are append-only and timestamped; the retraction
machinery (`RETRACTIONS.md`, the `flat` integrity probe, the leak probe, the
claim gates) was committed at **W0, before any measurement existed** - see the
first commit. The pre-registrations were hash-published before their studies.
The framing is what the record produced, not a story fitted to it afterwards.
