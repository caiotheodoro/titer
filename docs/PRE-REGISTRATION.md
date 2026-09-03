# PRE-REGISTRATION

Frozen 2026-09-02, before `src/` exists and before a single provider credit is
spent. Git history is the evidence of that ordering; a hash of this file is
published to a public Hugging Face repository at W0 so the ordering is provable
without exposing the working tree.

**This text is never edited.** A change after the freeze is a new dated entry in
`docs/DECISIONS.md` carrying a reversal clause, never a silent edit here.

A project that audits other people's unvalidated measurements does not get to
improvise its own.

---

## 0. What is fixed before data

- Every definition in `CONTRACTS.md` (`contracts/v1`).
- The four cost profiles and their ratios.
- The outcome classes and the meaning of `FALSE_MERGE`.
- The split seed and the rule that the frozen test split is never used for
  checkpoint selection.
- The estimators and interval methods named in section 2.
- The falsification condition attached to every hypothesis.
- The rule that the fitted simulator is trained on, and only on, the W2 cache.

Not fixed, and deliberately so: the achievable sample size `n`. It depends on
the measured ACU cost per call, which is not knowable until W2. Section 3 fixes
the *rule* for what we do at each `n` instead of the number.

---

## 1. Design

**Paired.** Every provider receives the identical task set in the identical
order. All comparisons are within-task. This is the design that makes a small
`n` worth anything at all, and it is why we do not run providers on different
samples and compare marginals.

**Blind to outcome.** The task set is drawn from the corpus by seed before any
provider is called, and is not revised afterwards. If a task turns out to be
unanswerable by every provider it stays in and is reported.

**One measurement window.** All providers are queried inside a single window,
recorded to the day in `docs/BENCHMARK.md`. A "living index" measured at
different times for different vendors is not a comparison.

---

## 2. Hypotheses

Each carries: the claim, how it is measured, the estimator, the interval, and
what result would falsify it. A hypothesis without a falsification condition is
marketing.

### H1 - Staleness has a measurable half-life

**Claim.** For an employer relationship attested by a filing on date `T`, the
probability that a provider's index reflects it is a function of elapsed days
`delta = measurement_date - T`, and that function has a half-life that is
finite, measurable, and different across providers.

**Measurement.** Cross-sectional. For each task we know `T` from the filing and
`delta` at query time. Outcome is binary: does the returned record attach
`person_cik` to `issuer_cik`. No waiting period is required and none is used.

**Estimator.** Kaplan-Meier over `delta`, reported as the curve plus the
median-reflection lag. Provider differences by paired bootstrap over tasks,
10,000 resamples, seed 11.

**Falsified if.** The reflection probability is flat in `delta` (the confidence
band for the slope contains zero across the observed range). That would mean
either the index does not update on this population at all, or our `delta` range
is too narrow to see it - both of which we report as the result.

**Pre-committed nuisance.** Filings are public on `FILING_DATE`, not
`PERIOD_OF_REPORT`. `delta` is computed from `FILING_DATE`, because that is the
earliest moment the information was available to anyone. Both dates are stored.

### H2 - False merges are measurable, and cost more than they are priced

**Claim.** Under name collision, providers return a confidently wrong identity
at a rate that is (a) non-zero, (b) increasing in name-collision degree `d`,
and (c) large enough to dominate expected loss under the `kyc_sanctions` and
`journalism` profiles even when accuracy looks acceptable.

**Measurement.** Outcome class per `CONTRACTS.md` section 4, stratified by the
`d` bands in section 8. `FALSE_MERGE` reported raw **and** net of the measured
same-human-two-CIK upper bound from section 4.2.

**Estimator.** Rate per band with Wilson intervals; paired bootstrap for
provider differences; expected loss per profile.

**Falsified if.** `FALSE_MERGE` net of the contamination bound is
indistinguishable from zero at the achieved `n`, or is flat in `d`. Either
outcome is published as prominently as a positive one.

### H3 - The free signals carry calibratable information

**Claim.** The signals a caller gets without paying - search rank position,
`resolution_source`, `identity_verified`, `last_seen` - are informative about
correctness, and are **not** calibrated as shipped.

**Measurement.** Reliability diagram with 10 equal-width bins. **Empty bins are
never merged**; an empty bin is reported as empty. ECE and Brier, before and
after isotonic recalibration fitted on a disjoint split.

**Falsified if.** Raw ECE is already low (no miscalibration to fix), or the
signals carry no mutual information with correctness (recalibration cannot
improve Brier beyond its interval).

**Note on scope.** The paid `confidence` field is out of budget and is therefore
**not** part of H3. We do not test it and we will not imply that we did.

### H4 - A small policy that knows when to stop paying beats a large one that does not

**Claim.** A Qwen3-8B policy trained with RLVR on the value-of-information
environment achieves lower expected loss per ACU spent than (i) the trivial
floors, (ii) the untrained base, and (iii) a frontier model given identical
tools and no budget discipline.

**Measurement.** Expected loss per profile, and expected loss per ACU, on the
frozen test split, evaluated on **held-out real provider calls** - not on the
simulator the policy was trained against.

**Estimator.** Paired bootstrap over tasks. Reported across all four cost
profiles, with the flat-profile integrity probe passing as a precondition.

**Falsified if.** The trained policy does not beat `never_verify` and
`always_deep_verify` on at least the profile it was tuned for. Beating neither
floor is a null result and is published as one.

**The seed rule, which is not negotiable.** No margin from any training run is
quoted without the across-seed spread. `reconforge` published a headline whose
across-seed standard deviation was 2.86x the claimed margin, and retracted it in
its own README. A minimum of four training seeds; if the across-seed SD exceeds
the claimed margin, there is no claim.

---

## 3. Power, and what we do at each achievable n

The budget is $5 of Ploid credit. At the published pay-as-you-go rate of
$0.20/ACU that is 25 ACU - one `/v1/person` verification, or roughly 500 search
matches at $0.10 per 10. Ploid's free-plan credit grant is not published
anywhere we could verify, so it is budgeted as **zero** until W2 measures it;
any grant that turns out to exist is upside, recorded in `docs/DECISIONS.md`.

The achievable matched `n` is `floor(budget / measured_cost_per_task)` and is
not known until W2 measures the true cost per task on each provider.

For a binomial rate near `p = 0.15`, the 95% Wilson half-width is approximately:

| n | half-width |
|---|---|
| 25 | +/- 0.14 |
| 50 | +/- 0.10 |
| 100 | +/- 0.07 |
| 200 | +/- 0.05 |
| 400 | +/- 0.035 |

Paired comparison is more efficient than these marginals and is what we use;
the table is the honest floor, not the plan.

**Pre-committed decision rule.** After W2 measures the true cost per task:

- If the matched-`n` half-width is **<= 0.05**, provider comparisons are
  reported as rankings.
- If it is **0.05 to 0.10**, comparisons are reported as intervals only, and no
  ranking language is used anywhere, including the README and the abstract.
- If it is **> 0.10**, we state plainly that this budget cannot separate the
  providers, publish the intervals anyway, and publish the `n` that would be
  required for each hypothesis. "What it would cost to know" is the finding.

We commit to this rule now precisely so that a disappointing `n` cannot later be
rationalised into a ranking.

**Max-n arms.** Where a provider's free tier funds more than the matched `n`, we
additionally publish that provider at its own `n`, in a separate table, labelled
not-a-ranking. Cross-provider claims are drawn only from the matched-`n` table.

---

## 4. Stopping and multiplicity

- **No optional stopping.** The task set is drawn once. We do not add tasks
  after seeing results, and we do not drop tasks except by the mechanical
  exclusion rules in `CONTRACTS.md` section 2.1 and 3.2, whose rates are
  published.
- **No provider is dropped for performing badly.** A provider is dropped only
  for an access or Terms-of-Service reason, recorded with the quoted clause in
  `docs/DECISIONS.md`.
- **Multiplicity.** Four hypotheses times four cost profiles is 16 reported
  comparisons. Primary claims are H1 and H2 under `gtm_outbound`, fixed here as
  primary. Everything else is secondary and labelled as such. We do not
  advertise a secondary result as if it were primary.
- **Retraction.** If a published number is later found wrong, the correction
  goes in the README next to the original, not in a footnote and not silently.
  `docs/RETRACTIONS.md` exists for this from W0.

---

## 5. Published regardless of outcome

Committed now, so that a null result cannot quietly fail to appear:

1. Every exclusion rate (entity rows, `UNKNOWN` titles, `UNRESOLVABLE`
   mappings, near-duplicates).
2. The same-human-two-CIK contamination bound, whatever it is.
3. The achieved `n` and its interval half-width, and which branch of the
   section 3 decision rule fired.
4. The flat-profile integrity probe result.
5. The environment health report: solve-rate histogram, percentage of tasks in
   the 10-80% band, percentage of GRPO groups with zero advantage, and the
   sampler-trainer KL.
6. The sim-to-real gap between simulator-evaluated and real-call-evaluated
   policy performance.
7. Across-seed spread for every trained arm.
8. Any hypothesis that was falsified.

---

## 6. Reversal clause

This pre-registration may be superseded only by a dated entry in
`docs/DECISIONS.md` that states: what changed, why, what evidence forced it,
what was rejected, and what result would have been reported under the original
plan. A supersession that cannot state the counterfactual is not permitted.

If provider Terms of Service prohibit named comparative publication, the naming
changes and nothing else does: providers become `Provider A/B/C` and the quoted
prohibiting clause is published in `docs/DECISIONS.md`. No hypothesis, estimator
or threshold in this document moves as a result.
