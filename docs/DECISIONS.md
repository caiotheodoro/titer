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
