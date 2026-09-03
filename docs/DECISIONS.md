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
