# PRE-REGISTRATION — EXPERTISE

Frozen 2026-09-03, before `src/titer/corpus/scholar.py` exists and before a
single credit is spent on this population. A hash is published to the public
Hugging Face repository so the ordering is provable by someone other than its
author.

**This text is never edited.** It supersedes nothing: `docs/PRE-REGISTRATION.md`
stays exactly as frozen, and its H1-H4 remain live for the EDGAR population -
unfinished, not falsified. See `docs/DECISIONS.md` D030.

**Written knowing how the first one went.** The employment pre-registration was
honest and still produced two designs that could not answer their own questions:
H2 sampled randomly when colliding names are 15% of the population (D027), and
H1 sampled randomly when 272 of 299 observations then landed in one elapsed-time
bin. Both were caught by looking at where observations fell, not by reading a
summary. The sampling rules below are stricter because of it.

---

## 0. Fixed before data

- The hypotheses, estimators, falsification conditions and sampling design here.
- The attestation tiers and the topic taxonomy added to `CONTRACTS.md`.
- The `expert_sourcing` cost profile and its ratios.
- The rule that **every stratified result is reported per stratum and never
  pooled into a marginal rate**.
- The power rule in section 3, unchanged from the original: it fixes what may be
  claimed at each achievable `n` before any `n` is known.

Not fixed: the achievable `n`. It depends on measured cost per task.

---

## 1. Design

**The negative control is constructible, and that is why this population is
better than the last one.** A person's attested topics come from their authored
works. A *false* expertise claim is therefore not a judgement call - it is a
topic in which they have provably never published. Every task is a balanced
discrimination between an attested claim and a constructed one, drawn from the
same oracle. The employment corpus could never do this: there was no way to
manufacture a verifiable non-employment.

**Paired.** Every arm receives the identical task set in the identical order,
each rendered in the shape its own API documents (D025). Differences are
within-task.

**Stratified by construction, not by hope.** Two axes, both fixed here:

1. **Claim polarity** - attested vs constructed-false, balanced 50/50.
2. **Name-collision degree**, using the provider-facing normalization (D027),
   with equal allocation across `unique / low / medium / high`.

Simple random sampling is **prohibited** for E1 and E2. It is what broke H1 and
H2, and the failure mode - a bin holding 90% of the observations - is invisible
in a summary statistic.

**One measurement window**, recorded to the day.

---

## 2. Hypotheses

### E1 - Providers affirm expertise that is not attested

**Claim.** Asked whether a named person has expertise in a topic, providers
affirm constructed-false claims at a non-zero rate, and that rate rises with
name-collision degree.

**Measurement.** Balanced attested / constructed-false tasks. Outcome classes
reuse `CONTRACTS.md` section 4; a confident affirmation of a constructed-false
claim is a `FALSE_MERGE` - **a fake expert admitted**.

**Estimator.** Rate per (polarity x collision band) cell with Wilson intervals;
paired bootstrap for provider differences, 10,000 resamples, seed 11. Expected
loss under all reportable profiles including `expert_sourcing`.

**Falsified if.** The false-affirmation rate is indistinguishable from zero at
the achieved `n`, or flat in collision degree. Either is published as
prominently as a positive.

**Pre-committed nuisance.** A constructed-false topic must be *plausible* -
drawn from an adjacent field, not an absurd one - or the task measures nothing.
Adjacency is defined by the OpenAlex topic hierarchy, mechanically, never by
hand-picking.

### E2 - A capability constraint does not disambiguate

**Claim.** Given a colliding name plus a capability constraint ("the Jane Chen
who published on X"), providers do not resolve to the right person more often
than with the name alone.

**Measurement.** Colliding-name tasks only, four arms: name alone; name + a
current-state filter the API accepts; name + capability in free text; name +
capability oracle-supplied (ceiling). This is the D029 experiment.

**Falsified if.** The free-text capability arm beats the name-alone arm - the
semantic query field already absorbs biographical context, and the architectural
gap D029 asserts does not exist in practice.

### E3 - The free signals are informative but uncalibrated

**Claim.** Provider-returned confidence on an expertise claim carries
information about correctness and is not calibrated as shipped.

**Measurement.** Reliability diagram, 10 equal-width bins, **empty bins reported
as empty, never merged**. ECE and Brier before and after isotonic recalibration
fitted on a disjoint split. Out-of-range confidences are an error, not silently
dropped.

**Falsified if.** Raw ECE is already low, or recalibration cannot improve Brier
beyond its interval.

### E4 - Coverage differs across populations

**Claim.** The same provider resolves the academic population and the SEC
executive population at materially different rates.

**Measurement.** Identical instruments over both corpora, reported side by side,
never pooled.

**Falsified if.** The paired difference interval contains zero.

**Why it is worth reporting either way.** A difference is a coverage finding
about who an index knows. No difference is evidence that resolution quality is a
property of the method rather than the population.

---

## 3. Power, and what may be claimed at each n

Unchanged from the employment pre-registration, because the rule is what matters
and it must not be renegotiated per study.

| Achieved 95% half-width | What may be said |
|---|---|
| <= 0.05 | comparisons may be reported as rankings |
| 0.05 - 0.10 | intervals only; **no ranking language anywhere**, including the README and any abstract |
| > 0.10 | state plainly that this budget cannot separate the arms, publish the intervals, and publish the `n` each hypothesis would have required |

`scripts/power.py` selects the branch from a **measured** cost per task, before
the measurement runs. That branch fired as `cannot_separate` on the employment
study and was honoured; it is honoured here too.

---

## 4. Stopping and multiplicity

- **No optional stopping.** The task set is drawn once, per stratum, by seed.
- **No arm is dropped for performing badly** - only for access or Terms reasons,
  recorded with the quoted clause.
- **Primary claims: E1 under `expert_sourcing`, and E2.** Everything else is
  secondary and labelled so.
- **Ploid is not measured** and no claim about it is made from this study.
  D029 remains a hypothesis (`docs/DECISIONS.md`).

---

## 5. Published regardless of outcome

1. Every exclusion rate, including the OpenAlex author-disambiguation error rate
   used as the contamination bound.
2. The achieved `n` per stratum and which section 3 branch fired.
3. The full per-stratum table. **No pooled marginal rate is ever published for a
   stratified result.**
4. Any falsified hypothesis.
5. The negative-control construction, in full, so a reader can attack it.
6. Whether the web floor is a valid floor this time - the last one was a parser
   artefact and was withdrawn (`docs/BENCHMARK.md`).

---

## 6. Reversal clause

Superseded only by a dated `docs/DECISIONS.md` entry stating what changed, why,
what evidence forced it, what was rejected, and **what would have been reported
under this plan**. A supersession that cannot state the counterfactual is not
permitted.

If provider Terms prohibit named comparative publication, the naming changes and
nothing else does.
