# Design: v2 study (replication, adjudication, prompt sensitivity, paired strata, and second surfaces)

Status: **design, not a registration.** Written 2026-11-23 alongside the paper v2 revision
(D049, D051). Nothing here is frozen, nothing has been run, no paid call has been made, and
every choice marked **owner** is open. A future execution would freeze a new pre-registration
file (e.g., `docs/PRE-REGISTRATION-V2.md`) and publish its hash before the first paid call,
with the owner's own predictions recorded in advance.

## Why

The surviving result of v1 (`results/expertise_e1_v2.json` and `results/expertise_control.json`)
measures one endpoint (Exa `/answer`), called with one prompt wording and one output schema,
once per task, in September 2026. Five gaps remain that cannot be closed without new API spend,
independent human readers, or vendor/legal steps:

1. **No test--retest stability.** Every task in the 1,250-call expertise study was queried once.
   Sampling intervals capture author/topic draw variance, not stochastic run-to-run variance of
   an answer engine whose underlying model and live index change over time.
2. **Unadjudicated oracle error in NEAR and FAR.** Reading the 21 CONTROL affirmations
   (`results/control_affirmations_read.json`, single unblinded assistant pass) showed only 6 of
   21 clearly represent endpoint error, with 6 broad topic labels and 9 plausible same-person /
   split-profile / homonym cases. The 42 NEAR and 33 FAR affirmations (75 total) have never been
   adjudicated by blinded human readers, so the oracle-error fraction in NEAR and FAR is unknown.
3. **Single prompt wording and output schema.** Prompt phrasing and schema constraints can shift
   affirmation rates and verbalised confidence substantially. Neither prompt sensitivity nor
   sycophantic agreement with a yes/no claim has been tested.
4. **Unpaired cross-run distance gradient.** NEAR and FAR came from `expertise_e1_v2.json` while
   CONTROL came from a separate run (`expertise_control.json`) on independent draws whose
   attested confirmation rates differed (`0.9600` vs `0.9840`).
5. **Single endpoint and unmeasured people-index arm.** All surviving expertise numbers come
   from one endpoint. Provider P stayed unmeasured after five budgets (R001, D028, D035, D040),
   and no second answer API was evaluated.
6. **Pre-venue legal and vendor-reply gate.** Exa self-serve Terms of Service §4.2(a) restricts
   publishing information obtained through the service (D019, D048), and the vendor has not been
   offered a right of reply before public venue submission.

## What stays

- Ground-truth discipline: public filings (SEC Forms 3/4/5) and publisher-attested authorship
  (OpenAlex `/works`, exhaustive verification before asking, catch-all topics excluded); no
  model assigns a ground-truth label (`CONTRACTS.md`, D003, R002).
- Privacy posture: pointers and hashes only; no raw provider bodies or person--false-claim pairs
  published (`docs/ETHICS.md`, `make privacy-gate`).
- Statistical reporting: per-stratum Wilson intervals, paired bootstrap / McNemar intervals for
  within-subject contrasts, no pooled marginal rates across balanced strata, empty calibration
  bins reported as empty (`docs/PRE-REGISTRATION-EXPERTISE.md`).
- Hard exclusions: no Exa Order Form or MSA (D019), no Apollo or People Data Labs calls, no
  contact-reveal or enrichment endpoints.

## Planned workstreams

### A. Test--retest on the same 1,250 tasks

Re-run the exact 750 main-run tasks (`expertise_e1_v2`) and 500 control-run tasks
(`expertise_control`) at least twice in a fixed measurement window (e.g., two repeats 24--72
hours apart, plus one later-window check), recording model metadata where exposed.

- **Metrics:** per-stratum agreement rate, flip rate (`affirm -> deny` and `deny -> affirm`),
  within-task test--retest variance vs across-task binomial variance, and calibration stability
  (ECE, Brier, Murphy reliability/resolution).
- **Estimated cost:** ~$6.25 per full 1,250-call pass at the September 2026 Exa `/answer` unit
  cost ($0.005/call), so ~$12.50--$18.75 for two to three passes.
- **Owner decision:** number of repeats (2 vs 3) and spacing between passes.

### B. Blind two-reader adjudication of all 75 NEAR and FAR affirmations

Two independent human readers evaluate all 75 false affirmations from the confirmatory main run
(42 NEAR, 33 FAR), plus an independent blind re-read of the 21 CONTROL affirmations (96 items
total), with stratum labels hidden and task order randomised.

- **Coding rubric:** identical four-way taxonomy anchored to `results/control_affirmations_read.json`:
  (1) `endpoint_error` (wrong person, unattributed/fabricated source, or evidence contradicts or
  does not support the topic), (2) `broad_label` (generic OpenAlex topic label supporting a
  loose match), (3) `oracle_gap_or_split_profile` (real work by the same researcher missed by
  the single OpenAlex profile or topic classifier), (4) `homonym_ambiguous` (same-name person
  not resolvable from public record).
- **Reporting:** inter-rater agreement (Cohen's $\kappa$ and raw percent agreement), resolved
  adjudication counts per stratum, and both raw and adjudicated-error rates with 95% Wilson
  intervals.
- **Cost:** $0 API spend; human annotation time (~4--6 hours per reader for 96 items).
- **Owner decision:** recruit second independent reader and publish adjudication guidelines
  before unblinding.

### C. Multi-prompt wording sweep (2--4 prompt wordings)

Test 2 to 4 semantically equivalent prompt wordings on a matched subsample (e.g., $n = 250$ per
stratum) to measure prompt sensitivity and yes-bias/sycophancy:

1. **Baseline (v1):** *"Does `<name>`, affiliated with `<institution>`, have published research
   expertise in `<topic>`?"*
2. **Strict bibliographic:** *"Has `<name>` (affiliated with `<institution>`) published
   peer-reviewed works specifically on `<topic>`? Answer false unless you find direct
   publication evidence."*
3. **Neutral / open-choice framing:** *"Assess whether `<name>` at `<institution>` has a
   published record in `<topic>`, or whether their published work lies in other areas."*
4. **Negative-presupposition framing (sycophancy probe):** *"Is it accurate that `<name>`
   (`<institution>`) has NOT published research in `<topic>`?"* (polarity inverted before scoring).

- **Metrics:** within-task paired differences across prompt wordings (10,000 paired bootstrap
  resamples), prompt-induced range of false-affirmation rates, and calibration shift.
- **Estimated cost:** ~$3.75--$5.00 per prompt wording on a 4-stratum draw ($n = 250$ each).
- **Owner decision:** exact wording set (2, 3, or 4 prompts) and whether to vary `outputSchema`
  confidence elicitation (e.g., 5-point verbal scale vs numeric `[0, 1]`).

### D. Paired three-distance draw from the same authors

Draw one cohort of $N = 250$ (or $N = 300$) OpenAlex authors with ORCID identifiers who each
have valid verified-false topics at **all three distances** (NEAR, FAR, CONTROL) plus one
ATTESTED topic. Run all four claims per author in a single measurement window and randomise
request order.

- **Why:** removes the unpaired cross-run confound between NEAR/FAR and CONTROL. Every pairwise
  contrast (NEAR vs FAR, FAR vs CONTROL, NEAR vs CONTROL) becomes a within-author paired
  comparison (exact McNemar test and paired bootstrap CI), and a Cochran's $Q$ / Friedman test
  replaces the unpaired $\chi^2$ and Cochran--Armitage tests of D049/D050.
- **Estimated cost:** ~$5.00 for $N = 250 \times 4 = 1{,}000$ calls on one endpoint.
- **Owner decision:** sample size ($N = 250$ vs $N = 400$ to achieve $\pm 0.035$ half-width per
  the pre-registered power table).

### E. Second answer endpoint, Provider P at registered size, and E4 completion

1. **Second answer endpoint:** add at least one independent commercial search-augmented answer
   API whose self-serve Terms of Service permit aggregate benchmark publication (checked via a
   new D018/D019-style Terms gate before any API call). Run on the identical paired draw from D
   for a valid matched-$n$ cross-endpoint comparison.
2. **Provider P people-index arm:** run the pre-registered power-rule minimum ($n = 49$ per arm
   for $\pm 0.10$ half-width at $p = 0.15$; ~$9.80 per arm at the measured $0.20/search, or
   $n = 100$ per arm / ~$20/arm for $\pm 0.07$ half-width) on a current-state task design that
   matches Provider P's documented structured filters (fixing the past-dated mismatch documented
   in D028/D035), after reading verbatim pilot rows per the R001 rule.
3. **E4 scholar-arm completion (optional, $0 vendor spend):** re-score the already-cached 250
   scholar rows in `scripts/run_e4_coverage.py --window 2026-09` using a fresh OpenAlex API key
   to replace the `4/250` `NO VERDICT` artifact (`results/e4_coverage.json`) cleanly, plus add a
   second scholarly affiliation oracle to bound OpenAlex `last_known_institutions` lag (D038).

### F. Pre-venue publication gate (Terms of Service and vendor right-of-reply)

Before submitting to any peer-reviewed venue or issuing a public claim beyond this preprint:

1. **Exa Terms of Service §4.2(a):** obtain legal review or written confirmation from Exa that
   reporting aggregate statistical rates (with zero record-level outputs, zero personal records,
   and self-serve access only) is permitted under §4.2(a) of the current self-serve Terms.
   Continue enforcing D019: never sign an Exa Order Form or MSA containing §2.4(j).
2. **Vendor right-of-reply:** send Exa a complete copy of the manuscript, the aggregate tables,
   and the exact prompt/schema specification with a fixed response window (e.g., 14 or 30 days)
   prior to venue submission, and record any vendor response (or non-response) verbatim in a
   dated `DECISIONS.md` entry and in the paper's Disclosures section.

## What the owner decides before freezing v2

1. **Total API budget** across A, C, D, and E (indicative minimum ~$45--$75 for A + 2 prompts in
   C + paired D + one second endpoint + Provider P at $n = 49$/arm).
2. **Second endpoint selection** after running a fresh Terms-of-Service gate.
3. **Independent second reader** for the 96-item blind adjudication (B).
4. **Pre-registered predictions** in the owner's own words for each new hypothesis before the
   v2 registration hash is published.
5. **Legal/vendor outreach timing** for Gate F.

## Order of work once decided

1. Complete Gate F (Terms check for any new provider; Exa §4.2(a) review) and human-reader
   protocol for B.
2. Freeze `docs/PRE-REGISTRATION-V2.md` and publish its SHA-256 hash externally before any paid
   call.
3. Run a 5-row verbatim pilot per arm (R001 rule) and commit row-inspection notes.
4. Execute D (paired draw), A (test--retest), C (prompt sweep), and E (second endpoint + Provider
   P) within one documented window.
5. Complete B (blind two-reader adjudication) before writing final prose.
6. Offer vendor right-of-reply (Gate F.2), regenerate all paper tables via
   `scripts/export_paper_tables.py`, and release v3.
