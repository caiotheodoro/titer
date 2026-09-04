# DECISIONS

Append-only. Each entry: Decision / Rationale / Evidence / Alternatives rejected.
Negative results and reversals go here on purpose. Never edit an entry; supersede
it with a later one that names what it reverses.

---

## D001 - Name: `titer` (2026-09-02)

**Decision.** The repository is `titer`.

**Rationale.** A titer is the concentration reached by titration - adding reagent
until you know. The project is about how much you have to spend before you are
sure about an identity. House style is a single-word instrument name.

**Evidence.** Sibling repos `assay`, `vernier`, `plumb`, `suture` follow the same
convention.

**Alternatives rejected.** `warrant` - reads badly next to people search.
`caliper` - a vernier *is* a caliper scale, so it would read as a sequel to a
different project. `docket` - names the oracle rather than the method.

---

## D002 - Cross-provider, not a single-vendor audit (2026-09-02)

**Decision.** Measure multiple people-search providers behind one adapter layer,
with Ploid as the lead subject rather than the only subject.

**Rationale.** A single-vendor audit is structurally identical to `vernier`'s
Build AI play and dies entirely if API access is refused. A category instrument
survives any one provider saying no, and the cross-provider contrast is the more
citable claim.

**Evidence.** `/v1/person` is 25 ACU, which is $5.00 at Ploid's published
pay-as-you-go rate of $0.20/ACU. A design that depends on one vendor's goodwill
at that price is one email from failure.

**Alternatives rejected.** Ploid-only, for the above. All-providers-equally -
rejected because Ploid is the specific product the work is aimed at, and
pretending otherwise would obscure the motivation.

---

## D003 - Oracle tiers: EDGAR is Tier A, ORCID is Tier B, Companies House is opportunistic (2026-09-02)

**Decision.** SEC Forms 3/4/5 are the sole Tier A corpus. ORCID is retained as an
explicitly-labelled Tier B (weak attestation) arm. Companies House is requested
but never on the critical path.

**Rationale.** This reverses an earlier intent to treat all three as equivalent
ground truth. Only EDGAR is attested by a filing with legal consequence and
carries a non-recycled filer identifier.

**Evidence, measured 2026-09-02.**
- EDGAR: quarterly `form345.zip` TSVs verified downloadable and parsed; 2025Q1
  contains 66,287 owner rows, 63,284 submissions, 32,388 distinct `RPTOWNERCIK`.
- ORCID: approximately 98% of affiliations are self-asserted by the researcher;
  ORCID's own figure is that about 2% have an affiliation added by an
  organisation. It is a registry, not a filing.
- Companies House: no free bulk officers file (Products 195/198/216 are gated
  behind an approval conversation with no published SLA); 600 requests per 5
  minutes implies roughly 32 days to enumerate live companies; and
  `person_number` **increments when an individual changes address or name**, so
  one human fragments into several identifiers. `officer_id` scoping is
  undocumented - OpenCorporates asked on the Companies House developer forum and
  received no answer.

**Alternatives rejected.** Dropping ORCID entirely - rejected because the Tier A
vs Tier B contrast is itself informative: a provider scoring *better* against
self-asserted data than against filings is evidence the index is built from
self-reported profiles rather than records. Keeping Companies House on the
critical path - rejected because its person identifier fragments in exactly the
direction the false-merge measurement depends on.

---

## D004 - 8-K Item 5.02 dropped as a person-level source (2026-09-02)

**Decision.** 8-K Item 5.02 is not used to derive person-level ground truth. It
is retained only as a free issuer-level "an officer change occurred on date D"
cross-check.

**Rationale.** The item codes are structured and free via `filings.recent.items`,
but the officer's name and title appear only in narrative prose. Extracting them
requires NLP - which is precisely the model-judged step this project exists to
avoid.

**Evidence.** Verified against Apple (CIK 320193): `filings.recent.items` yields
`5.02` with filing and report dates, and no person field. The one substantial
public dataset built this way (datamule, ~1M executive-officer rows) is
explicitly LLM-extracted.

**Alternatives rejected.** LLM extraction with a validated judge - rejected
because it would make the corpus's central selling point false.

---

## D005 - Publication posture: pointers and hashes only (2026-09-02)

**Decision.** The released corpus contains accession numbers, CIKs, derived
closed-class labels, dates and salted name hashes. No raw personal records. No
contact fields ever, in any artifact, including the replay cache.

**Rationale.** Anyone can rebuild the corpus from the SEC's own free files using
the pointers. Redistributing assembled personal records would commit the exact
harm - aggregating scattered public facts into one convenient file - that this
project exists to measure.

**Evidence.** `docs/ETHICS.md` sections 2 and 2.1. Enforced by `make
privacy-gate` inside `make validate`, which fails if a cache file appears in
`git ls-files` or a committed file matches the contact-field patterns.

**Alternatives rejected.** Full records - easiest reproduction, irreversible PII
publication. Fully synthetic - zero legal risk, but then it no longer measures a
real index and the project has no subject.

---

## D006 - Budget consequence: fitted simulator for training, real calls for evaluation (2026-09-02)

**Decision.** R4 trains on a cost/error simulator fitted to the small real
sample, and is evaluated on held-out **real** provider calls. The split is frozen
in `docs/PRE-REGISTRATION.md` before any credit is spent.

**Rationale.** The available budget is $5 - one paid verification, or about 500
search matches. RL needs thousands of episodes. Live rollouts are arithmetically
impossible, so the only honest options were a simulator with a real-call
evaluation, or a simulator with no real evaluation at all.

**Evidence.** Ploid pay-as-you-go is $0.20/ACU; `/v1/person` = 25 ACU = $5.00
(the "$2.50 face value" in their docs is the Business seat rate of $0.10/ACU).
Search is $0.10 per 10 matches. The free-plan credit grant is not published on
the live pricing page and is budgeted as zero. User holds $5 of credit.

**Alternatives rejected.** Simulator-only with no real evaluation - the headline
would then rest on a model of a provider rather than a provider. Abandoning the
trained policy - rejected because the value-of-information policy is the one part
of this project with no prior art anywhere in the workspace.

**Consequence accepted.** The sim-to-real gap becomes the central stated
limitation and is published as a number, not a caveat.

---

## D007 - Matched-n is the only ranking claim (2026-09-02)

**Decision.** Cross-provider rankings are drawn solely from a matched-`n` table
in which every arm is truncated to the smallest arm. Per-provider max-`n` results
are published in a separate table explicitly labelled not-a-ranking.

**Rationale.** Free tiers will be wildly unequal. Ranking a provider measured at
n=1000 against one measured at n=50 is the precise methodological sin the vendor
"studies" commit, and criticising them while committing it would be indefensible.

**Evidence.** Published vendor comparisons put Apollo at 42.4% in one study and
78% in another, with no matched design, no methodology and no intervals.

**Alternatives rejected.** Matched-n only - throws away real data from generous
providers. Max-n only - best per-provider precision, but any cross-provider
ranking drawn from it is unsound.

---

## D008 - The EDGAR corpus ships first, as its own release (2026-09-02)

**Decision.** The corpus is released as a standalone Hugging Face dataset at W1,
before any benchmark result exists.

**Rationale.** It has independent value, it is citable by people who do not care
about the benchmark, and shipping it early proves the oracle works before a
single credit is spent on a provider.

**Evidence.** No existing dataset packages person-company-role-date from Forms
3/4/5 at scale. The closest on Hugging Face is 34,882 transactions - about 0.5%
of a single year. The larger alternatives (BoardEx, Boardroom Alpha, sec-api.io)
are paid and non-redistributable, and the one large free effort is LLM-extracted.

**Alternatives rejected.** Bundling corpus and results in one repository - buries
the corpus's independent value under the benchmark framing.

---

## D009 - Environment protocol: OpenEnv primary, keel facade over it (2026-09-02)

**Decision.** The R4 environment is OpenEnv-native. A thin `reset/step/state`
facade implements the `keel` protocol on top of it.

**Rationale.** The post-training discipline is unambiguous - start from the eval
harness, do not rewrite a similar gym, and train against the same scoring stack
you evaluate against. OpenEnv gets ecosystem compatibility and Hub shareability.
The facade costs little and makes this `keel`'s first implementation.

**Evidence.** `keel/docs/superpowers/specs/00-keel-protocol.md:106` defines
`reset/step/state` with `Actor = agent|human|probe` and `turnCap: 32`, and has
zero lines of code. `assay/src/assay/adapters/openenv.py` already exists and can
be reused.

**Alternatives rejected.** keel-native only - bespoke, fights the same-harness
rule, harder to share. OpenEnv only - leaves keel a spec forever, and forgoes a
closed loop worth publishing.

**Follow-on committed.** Once the environment exists, point `assay` at it and
publish the audit of our own environment. assay's judges docked it for "the
agent is not load-bearing"; an agent choosing which paid call to make next
cannot be anything else.

---

## D010 - Reward: three program-checked atoms, zero shaping (2026-09-02)

**Decision.** `R = sum(3 atoms) - lambda * acu_spent - K * [confident and wrong]
+ a * [correct abstention]`. No shaping terms of any kind. The efficiency term
applies only among successes.

**Rationale.** Terminal binary is too sparse to train against at low capability,
but the legitimate cure is density from the oracle, not invented process credit.
The filing attests three independently checkable facts per episode, so density
comes free and honestly.

**Evidence.** Documented failure mode: shaped "explore first" rewards produced
performative first-turn exploration with zero downstream use, and removing the
shaping recovered the wanted behaviour. Applying an efficiency penalty to
failures rewards failing cheaply, which is `abstain_always` in disguise.

**Alternatives rejected.** Terminal binary only - likely leaves GRPO with no
advantages to compute. Process shaping - the above.

---

## D011 - Four cost profiles, plus a flat integrity probe (2026-09-02)

**Decision.** Report expected loss under `recruiter`, `gtm_outbound`,
`kyc_sanctions` and `journalism`. Treat ranking stability across profiles as the
result. Add a `flat` profile used only as a harness test.

**Rationale.** A single hand-picked false-merge penalty is unfalsifiable. A
ranking that survives all four profiles is a strong claim; one that flips between
them is a more interesting finding than a win.

**Evidence.** `assay` uses four cost profiles, separates on three of four, and
publishes that it does not separate on the fourth. Under `flat`, expected-loss
ranking must equal accuracy ranking; if it does not, the harness has a bug.

**Alternatives rejected.** Single justified K - unfalsifiable. Continuous sweep
over K - most complete, but does not yield a statable headline claim; it is kept
as a secondary figure.

---

## D012 - Difficulty is name-collision degree, measured from the oracle (2026-09-02)

**Decision.** Task difficulty is `d(name)` = distinct `RPTOWNERCIK` sharing an
exactly-normalized `RPTOWNERNAME`. Bands: 1, 2-3, 4-9, >=10.

**Rationale.** It is a measured property of the corpus rather than an assigned
guess, and it indexes the false-merge failure mode directly, so the curriculum
and the hypothesis point the same way.

**Alternatives rejected.** Handcrafted difficulty - a vibe. Random sampling -
likely puts most tasks outside the 10-80% solve band, which is how a run comes to
look like "GRPO does not work". Empirical post-hoc binning - most faithful but
requires a full rollout pass before the mix exists, and the bins do not
generalise to new tasks; retained as a validation check on `d`.

---

## D013 - Policy model: Qwen3-8B, with a 4B ablation (2026-09-02)

**Decision.** Qwen3-8B, 4-bit QLoRA on Modal L4, as the headline trained arm.
Qwen3-4B as an ablation. LoRA on all layers including MLP; learning rate about
10x a full fine-tune.

**Rationale.** 8B is the workspace's proven substrate for 4-bit QLoRA on an L4.
"How small can the spender be" is a publishable result in its own right, and a
budget-decision policy plausibly does not need 8B.

**Evidence.** `suture` trained 4-bit QLoRA for an 8B on Modal L4 successfully;
bf16 27B OOMs there. Attention-only LoRA underperforms MLP-inclusive LoRA at
matched parameter count.

**Alternatives rejected.** 4B only - tool-calling competence at 4B is a real risk
for a multi-turn budget agent, and a failed SFT floor leaves GRPO nothing to
amplify. 8B only - loses the size result for little saving.

---

## D014 - Budget-blind baseline: GPT-5.6-mini (2026-09-02)

**Decision.** The "capable but spends freely" arm is GPT-5.6-mini, the cheapest
frontier tier, given identical tools and no budget discipline.

**Rationale.** User instruction, overriding a recommendation to use a larger open
model. Keeps comparability with sibling repos that benchmark against the GPT-5.6
family, at eval-only cost.

**Evidence.** `suture` reports GPT-5.6 zero-shot at 0.373 and `reconforge`
benchmarks the same family; using a different family would break that line of
comparison. Cost is bounded because the frontier arm is used at evaluation only,
never in training.

**Alternatives rejected.** A larger open model on Modal - cheaper and fully
open-weights, but not comparable to the existing line. Trivial floors only - no
evidence the trained policy beats simply using a bigger model.

**Note.** `vernier` rejected DeepSeek/GLM over data residency against Ego4D
licensing. That objection does not transfer here: the corpus is US
public-domain filings and carries no residency constraint. DeepSeek remains
available as a cheap secondary check if wanted.

---

## D015 - Private repository until W7; public pre-registration hash at W0 (2026-09-02)

**Decision.** The code repository stays private until the W7 release. A public
Hugging Face repository is created at W0 containing only `PRE-REGISTRATION.md`,
the power analysis and their hashes.

**Rationale.** Building in private avoids anyone reading half-finished claims.
But commit dates are locally forgeable, so "frozen before results existed" would
otherwise be asserted rather than proven. The public hash costs nothing and makes
the ordering externally checkable. It also reserves the dataset name early.

**Alternatives rejected.** Public from commit 1 - strongest possible ordering
proof, but exposes early waves before numbers exist. Git history alone - forgeable.
OSF/Zenodo with a DOI - strongest timestamp, but a DOI on an unfinished project
is hard to revise.

---

## D016 - Static Hugging Face Space, never a publication gate (2026-09-02)

**Decision.** Ship a static Space rendering results from committed JSON. The
release does not block on it.

**Rationale and evidence.** `assay` could not deploy its Gradio Space: Hugging
Face returned 402, free `cpu-basic` requires a paid plan, and a static Space
cannot run a server-side probe battery. Assume the same wall here rather than
discovering it at release. Note `hf repos create --space-sdk`, not `--sdk`.

**Alternatives rejected.** A live Gradio Space - best demo, most likely to hit
the same 402. No Space - loses the browsable shop window for the collection.

---

## D017 - Publish first, then a link-first email (2026-09-02)

**Decision.** The artifact is standalone-valid and published before any outreach.
Outreach is then a short link-first email to Ploid proposing collaboration.

**Rationale.** Naming the goal now prevents the framing drifting into a job
application by W4, which would bend every README line and make it harder to lead
with an unflattering number.

**Evidence.** `vernier` follows the same sequence and records that its goal is a
research collaboration, not a job application.

---

## D018 - Provider Terms of Service is a W0 gate, with a pre-committed fallback (2026-09-02)

**Decision.** Before any provider call, each provider's ToS and AUP are checked
for clauses prohibiting benchmarking, publishing named comparative results, or
bulk querying for evaluation. A provider that forbids naming is either anonymised
as "Provider A/B/C" or dropped; the choice and the quoted clause are recorded
here.

**Rationale.** A benchmark that violates a Terms of Service cannot ship, and
discovering that after spending credits and building adapters would be the
expensive way to learn it.

**Status: OPEN.** Fact-finding was still in flight when this entry was written.
This entry is superseded by a later one recording the outcome. **No provider call
is made until that entry exists.**

**Pre-committed.** Anonymisation changes only the naming. No hypothesis,
estimator or threshold in `docs/PRE-REGISTRATION.md` moves as a result. Precedent
for naming exists: PeopleSearchBench and openbenchmarks both name vendors.

---

## D019 - Provider set fixed: Ploid, Exa, free-web floor. Apollo and PDL excluded. (2026-09-02)

**Supersedes the OPEN status of D018.** The Terms of Service gate is resolved.

**Decision.** v1 measures **Ploid**, **Exa**, and a **free web-search floor**.
Apollo is excluded from v1 and written benchmark consent is requested in
parallel. People Data Labs is excluded. Clay is excluded on comparability
grounds, not legal ones.

**Rationale and evidence, per provider.**

- **Ploid - permitted, and the lowest-risk of the five.** The complete Terms
  (last updated 5 April 2026) contain no benchmarking clause, no publicity
  clause, no competitive-analysis clause and no non-disparagement. §4 prohibits
  scraping *"except through documented APIs or features we expressly permit"* -
  which expressly permits exactly what a benchmark harness does. The one
  redistribution limit is qualified: *"Resell, sublicense, or redistribute the
  Services or outputs in a way that competes with Ploid"*, and a comparative
  measurement is not a competing product.

- **Exa - permitted on self-serve only.** The click-through ToS contains no
  benchmark clause. The **Master Subscription Agreement §2.4(j)** does:
  *"make available to any third party any analysis of the operation or
  benchmarking of any Services."* **Operational constraint, binding on this
  project: do not sign an Exa Order Form or MSA before publication.** Signing
  one retroactively acquires the prohibition. Self-serve ToS §4.2(a) also
  restricts publishing *"any information contained on, or obtained from or
  through, the Services"* - so we publish aggregate metrics and never
  record-level provider output, which `docs/ETHICS.md` section 2 already
  required for unrelated reasons.

- **Apollo - prohibited.** ToS §3(f)(vii), verbatim: *"Disclose the results of
  any Platform or program benchmark tests to any third parties without Apollo's
  prior written consent."* This is unambiguous and directly on point. §3(f)(iv)
  additionally bars automated access, and the API terms §5(i) bar use that
  competes *"as determined by Apollo in its sole discretion"*. Excluded from v1.
  A written-consent request is sent at W0; if granted, Apollo is added by a new
  DECISIONS entry and measured in a clearly-labelled later window, never
  back-dated into the primary table.

- **People Data Labs - excluded.** No benchmark clause, but SSA §5 defines
  Confidential Information to include *"information contained in or derived
  from the Services"*, which on a literal reading makes publishing benchmark
  results a confidentiality breach. §6.4 additionally requires deletion of all
  data and a signed Data Deletion Agreement within 30 days of termination -
  directly incompatible with a retained, reproducible corpus. The reproducibility
  conflict is the decisive factor, not the ambiguity.

- **Clay - excluded on comparability.** ToS is the second-most permissive: no
  benchmark, competitive-use or anti-scraping clause; the only limit is *"not to
  re-sell any data you obtain from Clay"*, and publishing a benchmark is not
  reselling. Excluded because Clay is a **waterfall orchestrator over 75+
  enrichment tools**, not a proprietary index. Measuring it would measure
  orchestration quality and answer a different question. Recorded so that its
  absence is not read as a legal finding.

**Alternatives rejected.** Ploid plus floor only - clean, but collapses back to
the single-vendor audit D002 rejected. Gating W2 on consent from all five -
strongest study, but makes the schedule hostage to vendor replies that may never
arrive. Anonymising Apollo as "Vendor D" - rejected because §3(f)(vii) forbids
disclosing *the results*, not the vendor's name, so anonymisation plausibly does
not cure the breach.

**Consequence for `docs/COVERAGE.md`.** Two providers plus a floor is a thin
comparison set, and that thinness is a coverage gap caused by contract terms
rather than by effort. It is published as such.

---

## D020 - The trivial floor is free web search (2026-09-02)

**Decision.** Every paid provider is compared against a free web-search baseline
resolving the same task. The floor is a reported arm, not a footnote.

**Rationale.** The workspace bar is that the arm which has to be beaten is the
trivial floor, not the incumbent. If a paid people index cannot beat free web
search at identifying a person who is named in a public filing, that is the
headline finding and it should be impossible to miss in the README.

**Evidence.** `assay` sets `flag_everything` as the arm to beat rather than the
incumbent tool, and publishes the floor comparison constructively. The same
logic applies here with more force, because the corpus population - officers and
directors of public issuers - is the population most likely to be well covered
by ordinary web search.

**Alternatives rejected.** Adding naive EDGAR full-text search as a second floor
- harsher and arguably fairer, but it tests the oracle partly against itself and
needs framing we do not yet have; deferred, and recorded here so the omission is
deliberate. No floor at all - abandons the stated bar.

---

## D021 - Pre-registration published and hash-locked; repositories created (2026-09-02)

**Decision.** The frozen pre-registration and contracts are published to a public
Hugging Face dataset repository before any measurement exists. The working code
repository is created private.

**Artifacts.**

| What | Where |
|---|---|
| Code (private until W7) | `https://github.com/caiotheodoro/titer` |
| Public pre-registration timestamp | `https://huggingface.co/datasets/caiotheodoro/titer-edgar-officers` |

**Hashes, recorded here so a later edit is detectable by anyone.**

```
PRE-REGISTRATION.md  d27dfeba1474b678bfde60f16f80ebbf1ae954024c2a78aa81df6252a2ba8fe9
CONTRACTS.md         6e4488c0fde3fad1bc31f7819e87ff1714ccc6e12d39f9b41cca2daf0cacb423
```

Verified by downloading the published files and re-hashing them against the
working tree, rather than by trusting the upload to have succeeded.

**Rationale.** Commit dates in a private repository are locally forgeable, so
they are not evidence that the analysis plan was fixed before the data. A public
hash is. The same repository reserves the eventual dataset name, and its card
states in its first line that no data exists yet - so the reservation cannot be
mistaken for a release.

**Not done, deliberately.** The Apollo written-consent request and the Companies
House Product 216 request are drafted at W0 in the plan but were not sent: both
are outward-facing contacts and the user chose to hold them. Apollo therefore
remains excluded, and `docs/COVERAGE.md` already records that its absence is a
contractual fact and not a quality finding. Companies House remains outside the
critical path, as D003 requires.

**Consequence for W0.** The wave's exit conditions in `docs/WAVES.md` are now
partially met: gates green, pre-registration published and hash-locked,
repositories created. The two outreach items remain open and are not blockers for
W1, which touches only free SEC bulk files.

---

## D022 - Task construction: the queried fact is never the scored fact (2026-09-02)

**Supplements, does not supersede, `docs/PRE-REGISTRATION.md`.** The
pre-registration fixes the hypotheses, estimators and falsification conditions.
It does not specify how a task is phrased, and that turned out to matter.

**The defect found.** The obvious task is "who was CFO of ISSUER on DATE"; the
obvious way to map a provider's returned person back to a CIK is by name plus
the employer they returned. Combining the two is **circular**: we would supply
the employer in the query, resolve the answer using the employer, and then score
whether the employer was right. Every answer scores `CORRECT` and the instrument
measures nothing. Resolving on name alone does not save it either - for a name
with collision degree 3 the provider has no signal telling it which of the three
we meant, so penalising it is unfair rather than informative.

**Decision - one task family serves both R1 and R2.**

> Person named *N*, who was *&lt;role&gt;* at **issuer A** on date *t1* (attested).
> What organisation were they at on date *t2*?

- Ground truth is **issuer B**, attested by a filing at *t2*.
- The query supplies *t1*'s employer. The scored fact is *t2*'s employer. The
  two are never the same fact, so the circularity is gone by construction.
- Identity resolution uses the returned employer, which was **not** supplied in
  the query, so it remains an independent signal.

**How the outcome classes fall out of one task:**

| Returned | Class | Which result it feeds |
|---|---|---|
| issuer B, same CIK | `CORRECT` | both |
| **issuer A**, same CIK | `STALE` | **R1** - the index has not caught up with the move |
| an employer belonging to a *different* CIK sharing the normalized name, confidence >= tau | `FALSE_MERGE` | **R2** |
| the same, confidence < tau | `UNSURE_WRONG` | R2 |
| nothing / not_found | `MISS` | both |
| declined | `ABSTAIN` | both |

`STALE` is no longer an awkward sixth class; it is the R1 measurement.

**Population consequence, and it is a real narrowing.** The task requires a
person with **at least two distinct attested issuers at two distinct times** -
someone who actually moved. People who filed at a single issuer for their whole
career cannot generate this task and are excluded from the measurement
population. That is a coverage gap caused by the design, it is published in
`docs/COVERAGE.md`, and the retained fraction is reported as a number once the
corpus is built rather than estimated now.

It is also the *right* population: "the index refreshes as people change jobs"
is a claim about people who changed jobs.

**Alternatives rejected.** Name-only queries - unfair at collision degree > 1,
because no signal distinguishes the targets. Supplying a LinkedIn URL or
provider person_id as the anchor - no public mapping from either to a CIK
exists, so it would reintroduce a judged resolution step. Scoring only people
with unique names - discards precisely the high-collision cases the project
exists to measure.

**Consequence for `CONTRACTS.md`.** No definition changes. Section 4's outcome
classes and section 4.1's resolution rule are unchanged; this entry fixes how a
task is drawn, which section 4.1 left open.

---

## D023 - H1's estimator changes from Kaplan-Meier to isotonic regression (2026-09-02)

**This supersedes the estimator named in `docs/PRE-REGISTRATION.md` H1.** The
pre-registration is not edited; this entry is the record, and it carries the
counterfactual the reversal clause requires.

**What changed.** H1 pre-registered "Kaplan-Meier over `delta`". The estimator
is now **isotonic regression via the Pool Adjacent Violators Algorithm**, with
bucketed Wilson rates published alongside.

**Why - the pre-registered estimator was wrong for the data.** Kaplan-Meier
estimates a survival function from right-censored time-to-event observations:
you watch a subject until the event happens or you stop watching. That is not
what R1 collects. Each task is inspected **exactly once**, at elapsed time
`delta`, and yields a single binary observation - was the move reflected by
then. The event time is interval-censored at one inspection point. This is
**current status data**, and its nonparametric maximum likelihood estimator is
isotonic regression on the indicators ordered by `delta`, not Kaplan-Meier.

Feeding current status data to Kaplan-Meier by pretending each observation is an
event-or-censoring at time `delta` would produce a curve, and the curve would be
biased in a direction that depends on the `delta` distribution - which is set by
our sampling, not by the index's behaviour. It would have looked fine.

**What would have been reported under the original plan.** A Kaplan-Meier curve
and a median lag read off it. On a synthetic check the two estimators disagree
whenever the elapsed-time distribution is non-uniform, which ours certainly is:
filings cluster by quarter. The direction of the disagreement is not fixed, so
the original plan would have produced a number of unknown bias rather than an
obviously wrong one - the worse failure mode.

**What is unchanged.** The hypothesis, the falsification condition ("reflection
probability is flat in `delta`"), the paired bootstrap for provider differences,
the 10,000 resamples and seed 11, and the commitment to publish the curve rather
than a single summary. Only the estimator changes.

**One property gained, and it is load-bearing.** Isotonic regression is monotone
by construction, which encodes the single structural assumption we are willing
to make: an index that has reflected a change does not un-reflect it.
`ReflectionCurve.is_monotone` is asserted in tests so the property cannot
silently lapse.

**`median_lag` returns `None` rather than extrapolating** when the curve never
reaches 0.5 within the observed range. "Not reached within N days" is a result;
an extrapolated median would be an invention.

**Alternatives rejected.** A parametric survival fit (Weibull, log-logistic) -
smaller variance, but it assumes a shape for exactly the thing being measured.
Logistic regression on `delta` - assumes monotone *and* sigmoid; isotonic
assumes only monotone.

---

## D024 - Scoring corrections found by adversarial review, before any data (2026-09-02)

Two fresh-context reviews attacked the scoring core. Every finding below was
**re-verified against live code** before being acted on, per the standing rule
that review findings are wrong in both directions often enough to check. Five
were confirmed critical. They are recorded here because several change how a
number will be computed, and `CONTRACTS.md` sections 4 and 6 must be read
alongside this entry.

Nothing had been measured yet. All of this was caught before a credit was spent.

### C1 - A provider that volunteered nothing scored `CORRECT`

`judge` returned `CORRECT` whenever the person matched and `employer_cik` was
`None`. The task asks which organisation the person was at, so a bare name is a
non-answer - but supplying a *wrong* employer scored `STALE` while supplying
*none* scored `CORRECT`. The metric was non-monotone in honesty and every
provider's optimal strategy was to return a name and nothing else.

**Now:** a missing employer is `MISS`.

### C2 - The answerer decided which atoms were scored

`window_scored` was `True` only if the provider volunteered employment dates,
and `Atoms.total` averaged over *scored* atoms - so omitting the dates shrank
the denominator and **raised** the score. Withholding paid.

**Now:** which atoms are scored is a property of the **task**. The window atom
is always scored; no dates means it fails. Only `title_class = UNKNOWN` drops an
atom, because that is our coverage gap and not the answerer's fault.

### C3 - The reward discarded the atoms it claims to sum

`R` took `atoms.total` only when the outcome was `CORRECT`, and `0.0`
otherwise. A policy that named the right human with the right title and was
merely `STALE` scored identically to one returning nothing - discarding exactly
the credit the atom system exists to carry, on the class `CONTRACTS` 4 calls
"the R1 signal". The reward was also profile-sensitive only for `FALSE_MERGE`,
so the trained objective was not the reported loss under any profile.

**Now:** `R = atoms.total - profile[outcome]/max(profile) - lambda*spend` (spend
charged only among successes). Every outcome is priced by the cost profile, so
the trained objective is the reported loss rather than a proxy for it.

### C4 - Stalling to the turn cap paid the same as abstaining

A flat `ABSTAIN_CREDIT` was added on every abstention, including the forced one
at the turn cap. With a free provider in the mix, burning 32 turns paid `+0.05`
- identical to abstaining immediately, and strictly better than answering
wrong. That is a shaping term rewarding delay, which `CONTRACTS` 6 prohibits.

**Now:** `ABSTAIN_CREDIT` is deleted. Abstention is priced by the profile like
every other outcome, and stalling earns a negative reward.

### C5 - Two parrot channels on the atoms

**The title was printed in the prompt.** Titles persist across a move for most
executives and `title_map` has nine coarse classes, so emitting the anchor title
handed over the answer to atom 2. The prompt no longer names it; the anchor
*employer* alone identifies the person, and that is the fact we do not score.

**Identity was credited when only the employer pinned it.** `resolve` breaks a
name collision using the returned employer. State the right employer and you
have, by construction, picked the right same-name person - so scoring both
double-counted one signal, and hardest at high collision degree, the exact axis
H2 stratifies on.

**Now:** the identity atom is scored **only** when the name alone was unique
(`reason == "unique_name"`). For colliding names the employer answer *is* the
identity answer, and is counted once.

### C6 - Task construction did not require the person to have left

`build_tasks` accepted "a second distinct issuer 180+ days later", which is a
concurrent board seat, not a move - and concurrent directorships are the norm in
this population. A provider answering with the still-current anchor issuer was
scored `STALE` for being factually right, contaminating H1's staleness signal
toward finding staleness that is not there.

**Now:** the target must post-date the person's **last** filing at the anchor
issuer.

### C7 - The leak probe could not detect the only leak that existed

`_bucket` is a pure function of the signature, so train and test signatures were
disjoint by construction and `leak_rate` read exactly `0.0` for any input. It
verified the implementation, not the corpus. Meanwhile the real leak was wide
open: one executive generates many *different* signatures across a career
(different issuers, titles, periods), so the same person appeared in train and
test.

**Measured on a synthetic 200-person corpus with three filings each: the
person-level leak under signature bucketing was 0.9239.** Almost every person in
the test set had been seen in training.

**Now:** splits bucket on `person_cik`, which is strictly stronger than
signature-disjointness and satisfies `CONTRACTS` 7. `leak_rate` takes a `level`
argument, the person-level rate is the reported one, and a test asserts the
probe distinguishes the two schemes - so the probe has demonstrated power rather
than asserted it.

### C8 - The flat-profile probe is an algebraic identity

Under `FLAT`, `expected_loss == 1 - accuracy` exactly, so "the flat ranking
equals the accuracy ranking" cannot fail. Over 20,000 random arm sets it
disagreed **zero** times. It was on the publish-regardless list as evidence the
harness works, and it is not evidence of anything.

Its one failure case was a bug of ours: an arm with *no* outcomes returned loss
`0.0` and ranked best.

**Now:** empty arms return `None` from both `expected_loss` and `accuracy`, and
`flat_probe_has_power` is the falsifiable companion - a non-flat profile must be
able to produce a different ranking, or the cost lookup is not wired in. The
identity itself is documented as an identity, not reported as a check.

### C9 - Smaller confirmed defects

| Defect | Effect | Fix |
|---|---|---|
| `signature()` sorted field *values* | person/issuer CIKs share a namespace, so `(100,200)` and `(200,100)` hashed identically and two facts became one task | labels included, order fixed |
| `name_norm` stripped `"v"` | ate the middle initial in "SMITH JOHN V", manufacturing a collision and inflating the false-merge rate H2 reports | `"v"` removed from suffixes |
| apostrophes were spaced | "O'BRIEN JOHN" and "OBRIEN JOHN" split one human in two | deleted, not spaced |
| `resolve_issuer` used the *person* normalizer on company names | "Microsoft Corporation" missed "MICROSOFT CORP", and an unmatched employer resolved to `None`, which C1 then read as `CORRECT` - every miss flattered the provider | separate `normalize_company` |
| isotonic blocks kept the **right** edge | `median_lag` returned the largest day in a pooled block, not the smallest; providers looked staler than the data supports, on H1's headline number | left edge |
| `wilson(0, 0).point == 0.0` | an empty bin rendered as a hard zero, i.e. a claim the rate *is* zero | `point=None` |
| out-of-range confidences | dropped from every bin while still counting in `n`, biasing ECE **low** - a miscalibration measure under-reporting miscalibration | rejected with an error |
| `int(5.0 // 0.1) == 49` | every non-dyadic price published an `n` one too small, including the `n=25` row of the frozen power table | `floor(round(...))` |
| Exa adapter read `title` as a person name | Exa returns a web-page title; every answer became token soup and scored `MISS`, fabricating a finding about a provider | page-title parsing, conservative on failure |
| `entity_not_human` counter | did not test humanity: a human founder with >10% and no board seat was counted non-human | renamed `ten_percent_owner_only`, both counters documented as one rule |
| contact-field test | passed with the protection deleted, because the dataclass has no such fields - it asserted the schema and called it a protection | structural and behavioural layers asserted separately |
| `TitleClass` compared with `is` | `TitleClass` subclasses `str`, so a value surviving a JSON round-trip compares equal but is not identical, silently failing every title atom | `==` |
| `title_map` | "Vice Chairman"/"Deputy Chairman" mapped to `CHAIR`; "Chief Exec. Officer" missed `CEO`; `CIO` claimed for technology while "Chief Investment Officer" fell elsewhere | guards and patterns corrected |

### What this says about the instrument

Every one of these was found *before* a measurement existed, by pointing fresh
context at the code with a mandate to find defects rather than to approve. Four
of the confirmed findings were defects in the **probes themselves** - the leak
probe, the flat probe, the contact-field test, and the health gate's own hack
probe. A probe that cannot fail is worse than no probe, because it is reported
as evidence that nothing failed. That is precisely the error this project was
built to catch in other people's measurements, and we shipped four of them.

`docs/RED-TEAM.md` A8 is now closed; the remaining LIVE attacks stand.

---

## D025 - Each provider receives the task in the shape its own API documents (2026-09-03)

**Decision.** A `Task` is rendered per provider by `Provider.render(task)`. The
facts disclosed are identical - person name plus the anchor employer - and the
scored fact is withheld in every rendering.

**Why.** Handing Ploid's `/v1/search` the task prompt verbatim returned **zero
results**, while a short people-search query against the same index returned
results. `/v1/search` is documented as taking a query, not a question; Exa's
`/answer` is documented as an answer engine and takes the question as written.
Scoring the prompt form against Ploid would have measured our input shape rather
than their index, and produced a fabricated finding - the same failure
`NotConfigured` exists to prevent.

**The rule this establishes.** Every arm must be given its best fair shot at the
same question with the same disclosed facts. A provider is never penalised for
our choice of wire format. Renderings are code, reviewable, and identical across
tasks.

**Also settled here: spend is read, not assumed.**

- Exa reports `costDollars.total` per call.
- Ploid reports `meta.credits_charged`, and it is **0** when a search returns
  nothing - so an empty result is correctly free rather than billed at a list
  price we invented.

`base.py` required this from the start: an estimated price makes the
value-of-information claim circular. Where a response carries no cost field the
fallback is tagged `usd_listprice_estimate`, so an assumed figure can never be
mistaken for a measured one.

**Not yet resolved.** Ploid's `person.title` is a LinkedIn *headline*, not a
role title, so its search tier cannot answer the "in what role" half of the
task. That is passed through to `title_map/v1` unaltered: a headline naming no
office becomes UNKNOWN and fails the title atom. Inferring a role from the
headline would put a judged step in the scoring path. Whether this understates
Ploid is a question for `docs/COVERAGE.md` once there are numbers.

---

## D026 - Corpus coverage starts 2006q1, not 2003q3 (2026-09-03)

**`CONTRACTS.md` section 2.1 rule 4 says "2003q3 or later". The data does not
exist before 2006q1.** The rule stands unchanged - it is still the inclusion
predicate, and it is still correct - but it is not the binding constraint.
Availability is.

**Measured.** The SEC landing page advertises **82 quarterly archives, 2006q1
through 2026q2**. Mandatory electronic Section 16 filing began mid-2003, which
is why the rule was written that way; SEC's *packaged* Insider Transactions Data
Sets simply start later. Recovering 2003q3-2005q4 would mean parsing raw
ownership XML out of the daily dissemination feed, roughly 3,000 additional
requests against a burst-sensitive service, for about 12% more calendar
coverage at the oldest and least relevant end.

**Decision.** Corpus coverage is **2006q1-2026q2**. `docs/COVERAGE.md` states
the gap in years, not as a footnote. The inclusion rule is not edited, because
it is not wrong - and editing a frozen contract to match what happened to be
available is exactly the move this repository exists to refuse.

**Consequence for R1.** None material. Staleness is measured against elapsed
days since a filing, and the freshest quarters carry that signal; the 2003-2005
gap sits at the far tail where reflection probability is saturated anyway.

**Consequence for R2.** Slightly fewer name collisions than the full record
would show, so `d(name)` is a mild **under**-estimate. That biases the reported
false-merge rate **down**, which is the safe direction for a critical finding
and is stated as such.

**A second thing this turned up, worth recording separately.** The newest
quarter is served from a **different path prefix**:
`/files/datastandardsinnovation/data/...` rather than
`/files/structureddata/data/...`. A filename generator keyed on the old prefix
would have silently dropped 2026q2 - the freshest quarter, and the one R1 most
wants. `docs/HANDOFF.md` has said "scrape the links, never generate them" since
W0 on general principle; this is the specific failure it was guarding against,
and it had already occurred by the time we looked.

---

## D027 - Difficulty uses the provider-facing name; H2 moves to stratified sampling (2026-09-03)

**This changes `CONTRACTS.md` section 8 and deviates from the sampling implied
by `docs/PRE-REGISTRATION.md` section 1. Both are recorded here with the
counterfactual, and neither frozen document is edited.**

### What the built corpus showed

The corpus is 4,206,080 rows over 230,405 people, 2006q1-2026q2. Measuring
collision degree exactly as CONTRACTS 8 defines it - distinct `RPTOWNERCIK`
sharing an *exactly-normalized* name - gives:

| Band | Movers (task population) | Share |
|---|---|---|
| `unique` | 45,051 | 97.24% |
| `low` (d=2-3) | 1,238 | 2.67% |
| `medium` (d=4-9) | 43 | 0.09% |
| `high` (d>=10) | **0** | **0.00%** |

Maximum degree anywhere in the corpus: **7**. A random sample of 50 tasks would
contain roughly **1.3** colliding-name tasks and **zero** hard ones. H2's central
claim - that false merges increase in collision degree - would have been
untestable, and we would have discovered that after spending the budget.

### Why collisions are so rare, and why that is our artefact

`name_norm/v1` keeps single-letter tokens, deliberately: dropping an initial
merges "John A Smith" into "John Smith" and manufactures a collision that never
happened. That is the right call for **resolution** - it is the conservative
direction, and it is what stops us inventing a false merge.

It is the wrong call for **difficulty**. SEC filings carry middle initials. A
recruiter, a sales tool or a journalist searching for a person usually does not.
Measured over the same corpus:

| Normalization | Colliding names | People affected | Max degree |
|---|---|---|---|
| keeping initials (`normalize`) | 2,844 (1.24%) | 6,026 | 7 |
| dropping initials (`normalize_presented`) | 11,589 (5.45%) | 31,079 | **28** |

**A 4.4x difference in the ambiguity a provider is actually handed.** Our own
normalization choice was hiding the phenomenon we exist to measure.

### Decision

Two normalizations, separated, both published:

* **`normalize`** - resolution only. Conservative. Never invents a merge. It
  continues to back the contamination bound in CONTRACTS 4.2.
* **`normalize_presented`** - difficulty only. Never used to resolve anything.
  This is now the `d` of CONTRACTS 8.

Under the provider-facing name the task population becomes measurable:

| Band | Movers | Share |
|---|---|---|
| `unique` | 39,184 | 84.57% |
| `low` | 5,028 | 10.85% |
| `medium` | 1,771 | 3.82% |
| `high` | 349 | 0.75% |

**7,148 colliding-name movers**, including 349 genuinely hard ones.

### H2 moves to a stratified design

Simple random sampling puts ~85% of a small budget into `unique` tasks, which
carry no information about false merges. H2 therefore samples **by stratum**,
with the strata reported separately and **never pooled into a marginal rate** -
a pooled figure over a deliberately unrepresentative sample would misstate the
population, which is the sin this project was built to name.

R1 (staleness) continues to use simple random sampling: it is a claim about the
population, and stratifying it would bias the reflection curve.

**What would have been reported under the original plan.** A single false-merge
rate over ~50 randomly drawn tasks, of which ~1 would have had a colliding name.
The rate would have been dominated by `unique` tasks, would almost certainly
have read 0.00 with a Wilson interval spanning most of [0, 0.07], and we would
have published "no evidence of false merges" when the design simply could not
have found any.

### Also fixed here

`near_duplicate_rate` conflated two different things and read **0.9135** on the
real corpus - because an active insider files dozens of Form 4s a year at one
employer. That is not near-duplication in any sense that matters: `signature()`
already collapses the same attested fact filed twice into one task. It is now
split into `repeat_filing_rate` (same fact re-filed; harmless) and
`near_duplicate_rate` (same relationship re-attested at a later period; the one
worth watching).

`title_map/v1` gains the real filed strings measured falling to UNKNOWN:
"Vice Chairman" and its variants, "SEVP", "CAO". Excluding Vice Chairman from
`CHAIR` was right; dropping it out of the taxonomy altogether was not. "See
Remarks" - 39k rows - correctly stays UNKNOWN: it is a pointer to prose, and
guessing what the prose says would put a judged step in the corpus.

Measured title coverage: **45.55% UNKNOWN, of which 42.40 points are titles the
filer left blank** and only 3.14 points are non-empty strings the map missed.
The gap is in the source, not the normalizer, and it is published either way.

---

## D028 - The task must ask what a current-state index can answer (2026-09-03)

**Two harness defects, found within minutes of each other, both of which made
every Ploid outcome an artefact. Neither is about Ploid.**

### C1 - Filtering on the anchor employer forced the answer

The corrected renderer sent `filters: {"company": <anchor>}`. Ploid's company
filter selects people **currently at that company**, so constraining it to the
anchor guaranteed the anchor came back - and the anchor is precisely the answer
we score as `STALE`. Every task would have been `STALE` by construction, and it
would have looked exactly like a damning finding about index freshness.

Verified live: `{"query": "George Reyes", "filters": {"company": "Google"}}`
returns George Reyes at google. The truth for that task is Gen Digital. The
filter, not the index, produced the stale answer.

**Now:** the anchor is disambiguating **context inside the query text**, never a
filter. The `company` filter is not used at all.

### C2 - The question did not match what the surface answers

Deeper, and the one that matters. A people-search index returns a person's
**current** employer. Our task asked for their employer **on a specific past
date**, median four years ago. A perfect index would answer "wrong" on most
tasks - not because it is stale, but because we asked something it does not
claim to answer. `docs/METHOD.md` says each arm must be given its best fair shot
at the same question; asking a current-state index about 2019 is not that.

**Now:** the task population is restricted to people whose **target employer is
their last attested employer**, so "where are they now" is the honest question
and a wrong answer means something.

Measured over the 46,332 tasks:

| Subset | n | Share |
|---|---|---|
| target is the person's last known employer | 30,607 | 66.1% |
| ...and that filing is under 5 years old | 16,896 | 36.5% |

Median age of the last filing is 4.0 years. The recency cut matters: a person
last attested in 2011 may have moved twice since, and the corpus cannot see it -
scoring an index wrong for knowing something SEC does not is not a measurement.

**Consequence, stated plainly.** This narrows the population again, on top of
D022's "must have moved" and D026's coverage window. `docs/COVERAGE.md` carries
the cumulative figure: from 230,405 people to 16,896 usable tasks, **7.3%**.
Every narrowing was forced by a mismatch between what we could attest and what
the surface answers, and each is published rather than quietly applied.

### What this says about the two Ploid runs

Both are void, and R001's diagnosis was **incomplete rather than wrong**. The
free-text rendering was a real defect. But the corrected rendering had two more,
and the run that produced 0/21 through the "fixed" harness (20 MISS, 1
FALSE_MERGE, resolution failing on 20 of 21) was measuring C1 and C2, not Ploid.

**No number about Ploid has survived any of the three runs.** The credits are
nearly gone. That is the honest state, and it is recorded rather than rounded
into a finding.

### The pattern worth naming

Three runs, three harness defects, zero findings about a vendor. Every one was
caught by reading returned rows rather than by reading a summary statistic, and
every one would have produced a publishable-looking number. `docs/SURVEY.md`
records the same provider at 42.4% and 78% in two published comparisons with no
methodology; this is what that gap is made of.

---

## D029 - Temporal disambiguation: an untested hypothesis, with the experiment (2026-09-03)

**Status: HYPOTHESIS. No measurement supports it. Recorded so it is falsifiable
later rather than asserted now.**

**The claim.** People-search indexes cannot be given a *biographical* constraint.
Ploid's published filter set is `title`, `seniority`, `company`, `industry`,
`location` - every field describes a person's **current state**. No query can
express *"the Jane Chen who was at X in 2019."* Where a name collides, the
caller therefore has no way to hand over the one piece of context that would
disambiguate, and the index returns *a* Jane Chen rather than *the* one.

**Why it is NOT the explanation for our results.** Four defects in our own
harness were each independently sufficient to produce the Ploid outcomes we saw
(R001, D028). Attributing those to a product gap would be exactly the error this
repository exists to name. Concretely, the one clean observation runs the other
way: `{"query": "George Reyes", "filters": {"company": "Google"}}` returned the
correct person as the top result from `ploid_people_index`. When asked properly,
it found him.

**What is genuinely observed, and it is thin.** Under malformed queries the
index returned *plausible wrong people* - "Mark Smith" at "Mark Smith Inc.",
"Richard Walker" at "Richard Walker West Inc." - eponymous small-business owners
rather than the filed officer. That is consistent with the hypothesis and also
consistent with a bad query. It distinguishes nothing.

**The experiment that would settle it.** A paired design over colliding-name
tasks, where every arm gets the identical name and the *only* difference is
whether a biographical constraint is available:

| Arm | Input | Measures |
|---|---|---|
| A | name only | baseline ambiguity |
| B | name + a **current-state** constraint the API accepts (`company`) | what today's filters buy |
| C | name + a **historical** constraint expressed in free text | whether the index uses it at all |
| D | name + historical constraint, oracle-supplied | ceiling |

The claim is supported if C ≈ A and D > B: the index cannot exploit history even
when it is handed it. It is falsified if C > A, which would mean the semantic
query field already absorbs biographical context and no new filter is needed.

Requires ~4 x n colliding-name tasks of provider credit. Not runnable at the
current budget; the tasks are frozen and the harness is ready.

**Until that runs, D029 is cited as a hypothesis and never as a finding.**

---

## D030 - The subject changes to expertise; the method does not (2026-09-03)

**Decision.** `titer` measures **expertise verification** first and **identity
disambiguation under a capability constraint** second. The SEC employment corpus
is retained as a cross-domain second population. The name, the oracle discipline,
the cost machinery and the environment are unchanged.

### Why - market evidence, including the part that argues against us

Expert sourcing for AI-data companies is large and compounding: Mercor at ~$2B
gross annualized and doubling in six months; Micro1 5x in eight; Handshake 0 to
~$1B in fifteen; frontier labs reported at ~$1B/yr each on human data; referral
bounties of **$250-$15,000 per verified expert hire**, which is the implicit
price ceiling for sourcing one.

**The against-case, recorded as prominently as the for-case, because it is
stronger than the pitch:**

1. **The winners own attested supply and say so.** Handshake's moat is 500,000
   PhDs verified through **university registrar integration** - `.edu` plus
   registrar, so credentials are institution-attested rather than self-reported.
   Mercor sources >60% of expert hires by referral. Micro1 built its own sourcing
   agent. A 3B-profile index is the commodity these companies deliberately
   de-commoditized.
2. **The acute pain is verification, not discovery.** Suspected North Korean
   operatives worked through Mercor on stolen credentials, in some cases
   producing data for US labs; a March 2026 breach exfiltrated identity and
   biometric dossiers and drew class actions; a vendor study flagged 38.5% of
   19,368 AI interviews for cheating (that last from a party selling
   anti-cheating tooling - directional, not authoritative). **Nobody in this
   market says they cannot find PhDs.**
3. **No public evidence that any of ten major buyers purchases third-party
   people data.** Either a research gap or a missing budget line. Stated as
   unknown; only customer conversations settle it.
4. **A direct competitor is already executing this GTM.** HeroHunt.ai sells a
   "1B-reach people-search API" and is content-marketing into this exact segment.
5. **The published analyst sizing is unusable.** The "$3-8B market" totals are
   *smaller than the combined revenue of the vendors inside them*. These numbers
   must not appear in any deliverable.

### The finding that redirects the instrument

**Handshake's moat is this repository's Tier A / Tier B distinction operating as
a business.** Attested-not-self-reported is worth ~$1B of annualized revenue to
someone. That is the strongest external validation the method has had - and it
says the subject should be expertise, where the attestation chain (OpenAlex
authorship, Crossref DOIs, ORCID identity) is *stronger* than SEC filings, not
weaker.

Note the reversal of D003: ORCID was demoted there as ~98% self-asserted. That
objection largely dissolves for expertise, because a researcher's **publication
record is attested by publishers**, not by the researcher. ORCID becomes the
identity spine; OpenAlex and DOIs carry the attestation.

### Consequences

- A new frozen `docs/PRE-REGISTRATION-EXPERTISE.md`, hash-published. **The
  original pre-registration is never edited.** Its H1-H4 remain live for the
  EDGAR arm - unfinished, not falsified.
- Ploid enters as an **architectural argument, explicitly unmeasured**, grounded
  in their own published filter set. Credits are exhausted and D029 is a
  hypothesis.
- The product argument is *not* "sell search to expert platforms" - they build
  that. It is: the unserved need is institution-attested verification at API
  speed, and Ploid already has the right architecture, missing the attestation
  chain behind the word "verified" and a biographical input.

**Alternatives rejected.** A strategy memo alone - produces no evidence, which is
the only thing this project is good at. A second repository - duplicates the
oracle, cost and calibration machinery. Dropping EDGAR - discards 4.2M attested
rows and the cross-domain contrast.

---

## D031 - Constructed-false claims get a difficulty axis (2026-09-03)

**Amends `CONTRACTS.md` A3, which specified one adjacency rule. It now specifies
two tiers, reported separately.**

**What the data showed.** A3's rule - same domain, different field, zero
attested works - was implemented and the first negatives inspected before any
measurement. They ranged from genuinely hard to trivially rejectable:

| Author's attested topic | Constructed-false topic | Verdict |
|---|---|---|
| Cutaneous melanoma detection | Dental education and practice | plausible |
| Immunotherapy and immune responses | Microbial metabolism | plausible |
| Diabetes and associated disorders | **Hemiptera insect studies** | absurd |
| Inorganic and organometallic chemistry | **Approximation theory and sequence spaces** | absurd |

The cause is that an OpenAlex *domain* is enormous - "Physical Sciences" spans
chemistry, mathematics, physics, computer science and engineering. "Different
field within the same domain" therefore admits chemistry-to-pure-maths.

**Why that matters more than it looks.** A benchmark whose negatives are mostly
absurd measures nothing: any provider rejects "this chemist studies approximation
theory", the false-affirmation rate comes back near zero, and the null is an
artefact of the construction rather than a property of the provider. That is
precisely the shape of the H1 and H2 sampling failures - a design that cannot
observe the thing it was built to observe.

**Decision.** Two mechanical tiers, both zero-attested-works, both reported and
**never pooled**:

- **`NEAR`** - same *field*, different *subfield*. An immunologist asked about
  neurogenetic disorders; a dermatologic oncologist asked about rheumatology.
  This tier carries the signal.
- **`FAR`** - same *domain*, different *field*. The original A3 rule, retained
  as the easy control that demonstrates the axis is doing work.

Negative difficulty now joins claim polarity and name-collision degree as a
pre-registered stratification axis. If a provider separates on `FAR` and not on
`NEAR`, that is the finding, and pooling the two would have hidden it.

**No model participates.** Both tiers are set operations over the OpenAlex topic
hierarchy, versioned `topic_adjacency/v1`, deterministic given the seed.

**What would have been reported under A3 as written.** A single
false-affirmation rate over a mixture of hard and absurd negatives, in unknown
proportion, with no way to tell whether a low rate meant a careful provider or
an easy test set.

---

## D032 - E2's colliding population is built by search, not by sampling (2026-09-03)

**Measured, before designing the task.** Name-collision degree over the 20,000
author corpus: 499 colliding names, 1,241 authors affected (6.21%), maximum
degree 9.

**That number is an artefact of the sample size, not a property of the world.**
The corpus is a 20,000-author slice of roughly 3.66M eligible ORCID authors.
Two researchers sharing a name are unlikely to *both* land in a 1-in-180 sample,
so within-sample collision under-counts real collision by a large and unknown
factor.

The EDGAR corpus did not have this problem: it is the complete population of
Section 16 filers, so a degree computed over it is the real degree. Here it is
not, and treating it as real would repeat D027 - a sampling scheme that cannot
observe the thing it is meant to measure.

**Decision.** E2's colliding population is constructed by **targeted search**:
query OpenAlex directly for authors sharing a normalized presented name, rather
than waiting for collisions to appear by chance. E1 continues to use the random
corpus, because polarity and negative difficulty are properties of the claim
rather than of the population, and random sampling is correct for them.

**Consequence, published.** The two studies therefore use differently
constructed populations, and no collision rate from E2 may be read as a
population rate - it is a deliberately enriched sample, exactly like a
case-control design. The `pooling_rule` field already carries this warning for
stratified runs and will carry it here.

**What would have been reported otherwise.** A false-merge-under-collision rate
computed over 1,241 accidentally-colliding authors, presented as if collision
were 6% of researchers. The real figure is unknown and larger.

---

## D033 - H1's monotonicity assumption is falsified; the isotonic estimator is withdrawn (2026-09-03)

**D023 replaced Kaplan-Meier with isotonic regression, arguing that monotonicity
was "the single structural assumption we are willing to make: an index that has
reflected a change does not un-reflect it." Measured, that assumption is false.**

Reflection rate by elapsed time since the filing became public, n=100 per bin,
sampling strata and reporting bins aligned:

| Elapsed | Reflected |
|---|---|
| 0-90d | 0.2800 [0.2014, 0.3749] |
| 90-365d | 0.3800 [0.2910, 0.4779] |
| **365-1095d** | **0.5700 [0.4722, 0.6627]** |
| 1095-2555d | 0.3300 [0.2456, 0.4269] |
| 2555-inf | 0.2900 [0.2101, 0.3854] |

An inverted U. Reflection roughly doubles over three years and then falls back
to its starting level. The 0-90d and 365-1095d intervals do not overlap, so the
rise is real; the 365-1095d and 2555+ intervals do not overlap either, so the
fall is real.

**Consequences.**

1. **The isotonic estimator is withdrawn for H1.** PAVA pools violators to force
   monotonicity, so on this data it produced a "median reflection lag" of 7,360
   days - an artefact of forcing a shape the data does not have. **That number
   is not reported.** Binned rates with Wilson intervals are reported instead;
   they assume nothing about shape.
2. **H1's falsification condition is not met.** The pre-registration said H1 is
   falsified if reflection is flat in elapsed time. It is not flat. But the
   "half-life" framing the hypothesis was built on does not apply to a
   non-monotone curve, so H1 is neither confirmed nor falsified as written - it
   is **mis-specified**, and that is the honest verdict.

**The most likely explanation is our oracle, not the index.** For an old filing,
the person's last SEC-attested employer is increasingly likely to be stale
*relative to reality*: executives leave public-company roles and SEC stops being
able to see them. A provider correctly reporting where they are **now** is then
scored wrong by us. Under that reading the rise to three years is genuine index
catch-up and the fall afterwards is **oracle decay** - the ground truth ageing
out, not the index regressing.

That is a hypothesis, not a finding. The experiment that distinguishes them is
E4: run the same instrument over the scholarly population, whose oracle
(OpenAlex affiliations) tracks people after they leave public companies. If the
scholarly curve is monotone where the EDGAR curve is not, the inverted U is
ours.

**What would have been reported under D023 as written.** A median reflection lag
of 7,360 days - roughly twenty years - presented as a staleness half-life. It
would have been nonsense, and it would have looked like a devastating finding
about the provider.

---

## D034 - The control tier: the axis exists, and it has a floor (2026-09-04)

**Partially reverses D031's falsification.** D031's NEAR and FAR tiers did not
separate, and the confirmatory run reported the difficulty axis as unsupported.
That was true of those two tiers and wrong as a general claim.

A third tier, `FAR_DOMAIN`, was added as an explicit **control** rather than a
difficulty step: a topic from a wholly different OpenAlex domain. An
immunologist asked about multiferroics; a dermatologic oncologist asked about
aquatic ecosystems; an organometallic chemist asked about historical studies on
Spain. n=250, verified zero-works, catch-alls excluded.

| Tier | False affirmation |
|---|---|
| NEAR — adjacent subfield | 0.1680 [0.1268, 0.2193] |
| FAR — adjacent field | 0.1320 [0.0956, 0.1796] |
| **CONTROL — different domain** | **0.0840 [0.0556, 0.1250]** |

Matched `ATTESTED` arm on the same 250 authors: 0.9840 [0.9596, 0.9938].

**Two findings, and the second is the one that matters.**

1. **The axis exists.** NEAR is exactly **2.00x** the control and the intervals
   do not overlap. Topic distance changes the rate. D031's tiers were too close
   together to resolve it, not wrong in principle. FAR still does not separate
   from the control, so the gradient is only visible at the extremes.

2. **The control is not zero.** 21 of 250 unambiguously absurd claims were
   affirmed - **one in twelve**. There is a floor of affirmation that topic
   distance does not remove.

**Why the floor matters more than the gradient.** `docs/RED-TEAM.md` A12 is the
strongest live attack on this project's headline: that the 13-17% on adjacent
topics may be a *defensible reading* of a vague question rather than an error,
since a provider might reasonably answer "does X work near T". That defence
cannot apply here. No reading of "published research expertise in historical
studies on Spain" applies to an organometallic chemist.

So A12 is now **bounded rather than open**: at least **8.4 percentage points**
of the 16.8% is genuine error. Interpretation can account for at most the
difference, roughly 8pp, not the whole rate.

**What would have been reported without this tier.** "Negative difficulty does
not detectably change the false-affirmation rate" - which is what the previous
BENCHMARK said, and which is wrong at the extremes. And A12 would have stayed
fully open, leaving the entire headline explicable as prompt interpretation.

Cost: $2.50. It resolved a LIVE red-team attack and corrected a published
falsification, which is the best value per dollar in this project.

---

## D035 - Four more harness defects, found by one pilot call before the budget (2026-09-04)

A $5 Ploid top-up arrived. R001's rule is that before spending a budget on an
arm, one task goes through it and the returned rows are read verbatim. That
single call, plus two follow-ups, found **four defects**. None is about Ploid.

### C3 - A Section 16 filer is not always a human

The first task drawn was `LGP Associates V LLC`. Ten-percent owners are
routinely funds and partnerships: **419 of the 23,015 built tasks (1.82%)** name
an organisation. A people index cannot return a current employer for
`Permira V L.P.`, so each is a guaranteed `MISS` that reads as a coverage
failure. **Three of the 40 tasks in the seed-11 draw were entities: 7.5 points
of fabricated error rate**, in an arm whose earlier runs reported 0/21.

Now excluded mechanically by `name_norm.is_entity_name`, rate published in
`results/task_stats.json`. The rule is deliberately conservative: bare
`HOLDING`, `TRUST`, `BANKS` and `CHURCH` are not markers, because
`HOLDING FRANK B JR` and `TRUST MARTIN` are real filers with those surnames.
Excluding them would trade a false finding about a vendor for a silent
narrowing of the population.

### C4 - The word "formerly" was matched as search text

D028 replaced the company filter with free-text context: `"<name>, formerly at
<company>"`. Querying `"Kelly Nima, formerly at GoDaddy"` returned a geodesist
at *"NGA formerly NIMA"*, a solicitor at *"Kelly & Co (formerly Michael F Kelly
Solicitor)"*, and a manager at *"PERSOL (formerly known as Kelly Services)"*.

Not one row was a person we asked about. Every one matched the **scaffolding of
our own query** against company-history text in the index. The anchor is still
disclosed, as bare tokens, because every arm must disclose the same facts; on
the same task, bare tokens put the right person at rank 1.

### C5 - 53.4% of names went out in the wrong order

`_presented_name` called `normalize_presented`, which **sorts its tokens**.
Sorting is correct for a collision key, where `REYES GEORGE` and `George Reyes`
must land in one bucket. It is wrong for a query, and it reproduces
given-name-first order only when the given name sorts before the surname.
`REYES GEORGE -> George Reyes` is correct **by luck** (G < R), and it was the
only example the docstring carried. `Kelly Nima` went out as `Kelly Nima`;
`EDWARDS JEFFREY L` as `edwards jeffrey`.

Measured over the task set: **12,066 of 22,596 names (53.4%)** were presented in
an order no person writes. Fixed by `name_norm.presented_query_name`, which is
kept separate from the collision key rather than changing it.

### C6 - The surname is not always token 0

EDGAR files `Van Dask Kristin Lea`. Taking one token as the surname yields
`Dask Kristin Lea Van`. A leading particle now absorbs what follows it
(`van`, `de la`, `mc`, `st`): 144 names, 0.64%. Middle tokens are dropped for
the reason `normalize_presented` already documents - filings carry them, people
searching do not. Verified live: `"Kristin Lea Van Dask Prospect Capital"`
returns no Van Dask at all; without the middle name she is rank 1.

### What this says about the arm

Three earlier runs, three defects, zero findings. A fourth budget, four more
defects, all in the same class: **the harness was measured, not the vendor.**
Every one was caught by reading returned rows, and every one would have produced
a publishable-looking number about a commercial product.

`docs/SURVEY.md` records the same provider at 42.4% and 78% in two published
comparisons with no methodology. Seven defects across four budgets is what that
gap is made of, and it is the reason this repository's headline is a ratio
rather than a leaderboard.

**Counterfactual.** Without the pilot rule, the $5 would have bought 25 calls
through a harness that sent half the names backwards, poisoned its own
retrieval, and asked a people index about limited partnerships. The result
would have been another 0/n, and this time there would have been no credits
left to find out why.

### C7 - The anchor tokens displace the person they were meant to disambiguate

The corrected render sent `"<given> <surname> <anchor company>"`. On 6 of the 18
scored tasks the returned rows were people **at the anchor company with the
wrong name**: asking for `Michael Anzilotti Access National` returned Libby Fike
and Byron Schulze at *virginia commerce bancorp inc*.

Settled by ablation on the last $0.40. `{"query": "Michael Anzilotti"}` returns
**Michael Anzilotti at rank 1**. The company tokens do not disambiguate the
name; they compete with it, and sometimes win.

This is C4 wearing different clothes. Removing the word "formerly" removed the
phrasing that matched company-history text, and left a bag of company tokens
that matches company text directly. A free-text people search has no way to
express "this person, who used to be here" - the surface takes one string and
ranks against all of it.

### Outcome of the fourth budget

**The run is void, and no number about Ploid is claimed. Again.**

`results/ploid_v4.json` records 0 correct of 18 (band `unique`, seed 23,
$3.60). It is not reportable: C7 was live during it, proven on a task inside
the run. The record is kept because a void run with a known cause is evidence,
and because deleting it would leave the fourth 0/n looking like the first three.

What the rows do show, and what they do not:

- The queried name appeared in the top 3 on **12 of 18** tasks, attached to a
  different individual. "Randall Stephenson" returns a Las Vegas police officer
  and a Methodist church volunteer; the Walmart director is not among them.
- That is **suggestive and unclaimable**. Six of the eighteen were contaminated
  by C7, and the two clean name-only ablations are an anecdote, not a rate.

**What it would cost to know**, per the pre-registered power rule, at `p = 0.15`:

| half-width | n | search-tier cost |
|---|---|---|
| ±0.10 | 49 | $9.80 |
| ±0.05 | 196 | $39.20 |

The measured cost is **$0.20 per search**, twice Ploid's published $0.10-per-10-
matches, because a live call reports `meta.credits_charged = 1` at $0.20/ACU.
Publishing that number is the pre-registered `cannot_separate` branch doing its
job: this budget could not separate anything, and the `n` that would is now on
the record.

**Four budgets, seven defects, zero findings about a vendor.** Every defect was
found by reading returned rows; not one was visible in a summary statistic. The
instrument is now materially better and the vendor remains unmeasured, which is
an honest description of where four budgets went.

---

## D037 - Five defects found before training, three of them reward hacks (2026-09-04)

W5's rule is "no health report, no training run". The health report existed and
was green. Reading the environment before writing a training loop found **five
defects**, three of which would have let a trained policy beat the published
floors without learning anything about the task, and one of which would have
fabricated the A12 result at zero cost.

Each was verified to fail before its fix, then to pass after.

### C1 - The window atom was free reward

`atoms()` scores the employment window from `answer.employment_start`, which
arrived in the **policy's own action dict**. Answering `date(1,1,1)` with no end
date satisfies `start <= period` and `end is None` for every task, on every
outcome, because atoms are scored regardless of outcome. That is roughly
**+0.33 reward per episode for nothing**, which alone beats the published
`never_verify` floor of 0.0455 by an order of magnitude.

The comment directly above the offending line forbids exactly this for
`title_class`: *"A policy that hands us a pre-classified enum would be doing our
normalization for us, which is a leak."* Same leak, inconsistently applied.

**Now:** dates come from the provider's returned candidate. No match means no
dates and the atom fails, which `atoms()` already documented as correct.

### C2 - Confidence was a free knob

`judge()` reads confidence only in the wrong-person branch: `FALSE_MERGE` at
`conf >= 0.5`, `UNSURE_WRONG` below. Under `gtm_outbound` that is 5.0 against
2.0, so stating **0.49 saved 3.0 of penalty every time the policy was wrong and
cost nothing when it was right.** Strictly dominant. Every calibration claim in
this repository would have died with it.

**Now:** a Brier term, `BRIER_W * (confidence - correct)^2`. It is outcome-only
- it reads the terminal outcome and the stated confidence and rewards no
intermediate behaviour - so the "no shaping" rule is intact. This amends
`CONTRACTS.md` §6 on evidence, which §6 permits.

The gate is not "hedging must be bad": on a known-wrong answer hedging *should*
win, and that is the rule working. The gate is that **truthful confidence must be
optimal**. Swept over constant-confidence policies, the reward argmax now sits at
**0.4** against an empirical accuracy of **0.3773**. With the term disabled the
argmax is **0.0** and the probe fails, which is how it was verified.

### C3 - The turn cap did not bind in the refusal branches

`insufficient_budget` and `budget_exceeded` returned `done=False` without
checking the cap, which was only checked after a successful charge. A policy
that keeps requesting what it cannot afford ran **37 turns against a cap of 32**
and would never terminate. The three floors never hit it; an exploring policy
hits it immediately.

### C4 - The expertise runner's cache key omitted the prompt

`CacheKey("exa", "expertise", task_id, window)`. `full_run.py` has always keyed
on `f"{task_id}|{rendered}"`; the runner that produced E1 did not. A new prompt
variant over the same tasks in the same month would have returned a **cached hit
for every task**: `adapter.query` never reached, `--spend` apparently working,
$0 spent, and the OLD answers written under the NEW variant's filename. No
error, no warning.

This is the class of defect the README leads with, sitting in the runner that
produced the headline. It would have made the A12 experiment report a fabricated
result for free.

**Now:** the prompt is in the key, and a variant uses a distinct action. The
2,388 already-measured entries keep replaying free through an explicit legacy
fallback that is applied **only** to the original action, so a variant can never
inherit the original's answers. Verified: E1 v2 replays byte-identically.

### C5 - `env_health --real` gated nothing

`run_real` always returned 0. It was a reporter wearing a gate's name, and it
probed for neither C1 nor C2. It now gates on the 10-80% band, on having enough
real observations, and on both reward-hack probes.

### The floors were wrong, and the ordering changed

Re-measured under the fixed reward:

| Floor | Published | Corrected |
|---|---|---|
| `never_verify` | 0.0455 | **-0.2292** |
| `always_deep_verify` | 0.0277 | **-0.2574** |
| `abstain_always` | -0.1000 | **-0.1000** |

`never_verify` still beats `always_deep_verify`, so **"spending 3x more bought
marginally fewer correct answers" survives**. But both active floors are now
beaten by **doing nothing**. Under `gtm_outbound` at a 37% solve rate, answering
is negative expected value, and the floor a trained policy must beat is
`abstain_always` at -0.1.

That is a better-posed training problem than the one before it: the task is no
longer "verify more cheaply", it is "answer only when you are likely right".

**Counterfactual.** Without reading the environment first, a policy trained
against the old reward would have reported a large margin over `never_verify`,
every point of it earned by asserting `date(1,1,1)` and `confidence=0.49`. It
would have been this project's sixth artefact, and the first one published.

---

## D036 - The trained arm is a policy on the simulator, not an 8B fine-tune (2026-09-04)

W6 says "SFT → GRPO, 8B and 4B". That is not what shipped, and the substitution
is recorded rather than made quietly.

**Why.** The fitted R4 environment exposes **three** discrete actions - query,
answer(confidence), abstain. The declared `train` extra
(torch/transformers/peft/trl/bitsandbytes, sized for a Qwen3-8B QLoRA) is
enormously oversized for that action space, and every eval rollout of an LLM
policy costs real provider calls. The simulator is fitted to real cached
observations, so rollouts against it are **free**, which is the only reason
≥4 seeds is affordable - and without ≥4 seeds there is no claim at all under the
seed rule.

**What shipped.** `src/titer/train/policy.py`: a linear-softmax policy over ten
bounded observation features and thirteen actions, **130 parameters, stdlib
only**. Confidence is discretised into buckets so the policy must *choose* it,
which matters after D037 made confidence a scored quantity rather than a free
knob.

`collision_band` is deliberately not a feature. The simulator conditions on it;
the observation does not expose it; a policy trained on it would be learning
from something no live provider hands over.

**The result.** Frozen test, 6 seeds, `gtm_outbound`:

| | value |
|---|---|
| trained policy, mean | **0.0461** |
| baseline (`abstain_always`) | −0.1000 |
| margin | 0.1461 |
| across-seed SD | **0.0122 (0.08× the margin)** |
| verdict | **CLAIM** |

It beats `abstain_always` under all five cost profiles. Absolute rewards are
**not** comparable across profiles - the reward normalises by
`max(profile.values())`, so a profile with a 150× false-merge cost compresses
every term - but the sign and the ordering within each profile are.

**What it learned, and what it did not.** It queries once, then **abstains on
41.7%** of tasks, which lifts precision on the answered subset from the 37% base
rate to **64%**. That is the valuable half and it is genuine selectivity.

It states **confidence 1.0 on every answer it gives**, at 64% accuracy. That is
the same failure E3 measured in the provider: confidence pinned at ceiling,
carrying no information. A calibrated policy would state ≈0.64 and score better;
this one leaves roughly 0.04 of reward on the table by not doing so.

**So the honest headline is narrow.** The policy learned *when to answer*. It did
not learn *how sure to say it is*, in an environment that now prices exactly
that. Reporting only the margin would hide the more interesting half.

**What this does not license.** No claim about any language model, about the 8B
or 4B arms, or about a policy operating against a live provider. Every number
here is measured against a simulator fitted to 485 cached observations, and the
simulator's `high` collision band still has zero of them.

---

## D038 - E4 is not measurable at this budget, and the reason is measured (2026-09-04)

E4 asks whether the same provider resolves the academic and SEC populations at
materially different rates, identical instruments, never pooled.

The instrument was built (`scripts/run_e4_coverage.py`): the **name-only**
question, the one rendering both populations can receive unchanged, since the
scholar corpus carries no affiliation history to anchor on. Then the R001 rule
was applied - two rows on the wire, read before the budget.

**The first scholar row killed the design as scored.** Truth
`Manipal Academy of Higher Education`; returned `Kasturba Medical College,
Manipal University`. Kasturba Medical College is *inside* Manipal Academy of
Higher Education, which was formerly Manipal University. The provider named the
right institution at a finer granularity and a **normalised string match scored
it wrong**.

A 12-task probe ($0.07) put a number on it. Of 8 scholar rows:

| | n |
|---|---|
| strict match | 2 |
| shares a distinctive token but not a match | 1 |
| no overlap | 5 |

The no-overlap cases are mostly genuine misses - `Adam Smith Institute` returned
`The Mohegan Tribe` - which is what a name-only query on an ambiguous name
does. But at least one more is a hierarchy artefact
(`Centre National de la Recherche Scientifique` returned as one of its
*laboratoires*), and one is plausibly a joint appointment (`UCLA` returned as
`VA Greater Los Angeles Healthcare System`).

**So the measurement cannot separate "wrong person" from "right institution,
named as a sub-unit" without an institution resolver.** At n=250 that ambiguity
would sit inside the headline, and the headline would read as a coverage finding
about the academic population. That is the R002 shape exactly: a scoring artefact
the same size as the effect.

**Two things block it, and both are named rather than worked around.**

1. **The scorer needs institution IDs, not strings.** Resolving both sides
   against OpenAlex `/institutions` and comparing IDs is the same
   "resolve against an oracle" discipline `resolve.py` already uses for CIKs.
   OpenAlex's account budget was exhausted for the day at the time of writing
   (both authenticated and unauthenticated paths returned
   `$0 remaining ... resets at midnight UTC`), so it could not be built or run.
2. **The two oracles are not equally strong, and no scorer fixes that.** SEC
   truth is a filing an officer signed. Scholar truth is OpenAlex
   `last_known_institutions`, derived from publication affiliations, which lags
   a move and can name a lab rather than the parent body. A measured gap is
   therefore (index coverage x oracle freshness) and cannot be split without a
   second scholarly oracle.

**Not run. E4 stays unmet in `MEASUREMENT_CARD.json`.** Tuning the matcher
against the rows just read would be fitting the scorer to the sample, which is
the failure this repository is about. Total spent finding this out: **$0.08**.

**What it would take:** an institution resolver over OpenAlex IDs, a measured
sub-unit-to-parent containment rate published alongside, and a second scholarly
affiliation source to bound oracle staleness. That is a wave of work, not a
budget line.

---

## D039 - E2 falsifies D029 on an answer engine (2026-09-04)

D029 was recorded as *"a hypothesis, and never a finding"*, with the experiment
that would settle it written down. The experiment ran. **The hypothesis is
falsified**, on the surface tested, and it was our own.

**Claim (D029).** A people-search surface cannot be handed a *biographical*
constraint: every documented filter describes a person's current state, so where
a name collides the caller has no way to pass the one fact that disambiguates.

**Pre-registered falsification.** C > A - the free-text capability arm beats the
name-alone arm.

**Result.** Exa `/answer`, n=80 per colliding band, four renderings of the
identical task set, within-task, seed 23, $3.60:

| Contrast | `low` | `medium` | `high` |
|---|---|---|---|
| C - A | **+0.1500** [0.0750, 0.2375] | **+0.1875** [0.1000, 0.2750] | **+0.2875** [0.1875, 0.3875] |

Three bands, three intervals excluding zero. Naming the past employer in free
text moves the correct rate from 0.05 to 0.20 at `low`, and from **0 of 80** to
0.19 and 0.29 at `medium` and `high`.

**What survives of D029.** Its scope. The claim was about indexes with
**structured filters** - `title`, `seniority`, `company`, `industry`,
`location`, all current-state. Exa `/answer` is an answer engine and reads free
text, so it was never the surface the argument was about. Falsifying it here
does not falsify it for a filter-based index; the within-provider Ploid arm is
that test.

**The unexpected half.** `D - C` separates only at `low`. Handing over the
attested date and role class on top of the company name buys **nothing
measurable** once names actually collide. The disambiguating signal is the past
employer, and the rest of the anchor is decoration. Nothing predicted that, and
it is the more useful finding for anyone building a query.

**Also worth stating plainly:** arm A is **0 of 80** at both `medium` and
`high`. A colliding name with no context is not merely harder, it is
unresolvable against this population, and that is the ceiling the other arms are
read against.

**Counterfactual.** Had this not run, D029 would have stayed in the log as a
plausible architectural story about a product gap, cited as motivation and never
tested. It is exactly the kind of claim this repository exists to make
falsifiable, and it did not survive contact.

---

## D040 - Two defects I introduced, and the Ploid arm they cost (2026-09-04)

Recorded because the record is the product, and these were committed by the
tooling rather than caught by it.

### C1 - A patch that silently did not apply

`build_arms` was patched with `str.replace()` against an anchor that was not in
the file, without an assert, and the script printed `ploid arms wired`
unconditionally. Nothing errored. The arm was simply absent from the dict, and
**$1.60 bought one arm of a two-arm within-provider contrast**.

This is the exact shape of every defect in `RETRACTIONS.md`: a claim that
quietly stopped being true, believed because the tool said so. `build_arms` now
constructs both arms, and four tests pin the arm sets - including that the
default non-E2 set is unchanged - so an absent arm is a red test rather than a
wasted budget.

### C2 - An arm is not a provider, and the card started inventing vendors

Since E2, four renderings of one provider are four arms. A cache key's first
field is the arm, which is **correct** - two renderings must never collide - but
`refresh_card.live_spend()` summed spend by that field. So
`MEASUREMENT_CARD.json` grew entries for `exa_A_name_only`,
`exa_C_anchor_freetext`, `exa_D_full_context`, `ploid_A_name_only` and
`ploid_B_company_filter`, **five fictional providers**, with E2's real spend
split across them.

The aggregate total stayed right, which is why nothing looked wrong. Attribution
now folds the arm back onto the provider that billed it. Corrected:
**ploid $15.60, exa $19.77, webfloor $2.28, total $37.65.**

### The arm itself

Ploid, within-provider, `medium` band, n=12 per arm, $4.00. Both arms **0
correct**. The difference is in resolution, not accuracy: name-only left 11 of
12 as `colliding_name_no_employer` and resolved nothing; the filter resolved 3,
and 2 of those came back `STALE` - the **anchor**, exactly as D028 C1 predicted
a current-state filter would.

That is consistent with D029 on the surface D029 was aimed at, and **consistency
at n=12 with zero correct in both arms is not evidence**. The paired interval
`0.0000 [0.0000, 0.0000]` is degenerate, not a null result. Required n is 49 per
arm for a ±0.10 half-width, $9.80 per arm; this budget bought 12.

**Five budgets, no Ploid accuracy number.** Unchanged, and stated rather than
softened.

---

## D041 - H2 is falsified, and it cost nothing (2026-09-04)

`MEASUREMENT_CARD.json` carried "H2 false merge under name collision: strata
empty by construction" for the whole life of the project. That was true of the
W3 draw and it was never a budget problem.

**The cause was the sampling, not the money.** D027 recorded that simple random
sampling put 251 of 299 observations into a single collision band, so three of
four bands held almost nothing and no gradient in `d` could exist. E2 drew
**n=80 in every band by construction**, because a within-task design needs equal
allocation. Those observations resolve H2 for **$0**, from data collected to
answer a different question.

**Claim (H2).** `FALSE_MERGE` under name collision is (a) non-zero, (b)
increasing in collision degree `d`, and (c) large enough to dominate expected
loss under `kyc_sanctions` and `journalism`.

**Falsified if** the rate net of the contamination bound is indistinguishable
from zero at the achieved `n`, **or** is flat in `d`.

**Result**, `exa_D_full_context` held constant across bands, n=80 each:

| Band | `FALSE_MERGE` | raw Wilson | net of contamination |
|---|---|---|---|
| `low` (d 2-3) | 0/80 | 0.0000 [0.0000, 0.0458] | **[0, 0]** |
| `medium` (4-9) | 1/80 | 0.0125 [0.0022, 0.0675] | **[0, 0]** |
| `high` (>=10) | 0/80 | 0.0000 [0.0000, 0.0458] | **[0, 0]** |

**Both falsification conditions fire at once.** The rates are 0.0000, 0.0125,
0.0000 - not increasing in `d`, and flat is enough on its own. And net of the
measured same-human-two-CIK bound of **12.76%** (CONTRACTS 4.2), every interval
collapses to zero: a single false merge in eighty colliding names is entirely
absorbed by the possibility that one person holds two filer registrations.

**So (a), (b) and (c) all fail.** The provider does not confidently return a
wrong identity at a measurable rate on this population, and expected loss under
`kyc_sanctions` is driven by `MISS`, not by `FALSE_MERGE`.

**Why this is worth publishing rather than filing away.** H2 was the hypothesis
most likely to produce an alarming, quotable number about a commercial product -
"confidently wrong about who someone is, more often as names get more common".
It is the kind of claim that travels. It is not true here, and the
pre-registration commits to publishing that as prominently as the positive
result would have been.

**One caveat that limits the reach.** The identity atom is scored only when the
name alone pinned the person (D024), and on colliding names `resolve` structurally
cannot return `unique_name`. Most outcomes are therefore `MISS` rather than a
wrong identity: the provider mostly fails to name anyone resolvable rather than
naming the wrong one. A surface that answered more confidently could behave
differently, and that is not measured here.
