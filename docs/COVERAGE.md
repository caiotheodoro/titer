# COVERAGE — what this instrument cannot see

Written in someone else's vocabulary on purpose. Stating a coverage gap in
categories we invented would let us define the gap out of existence.

The categories below are **PeopleSearchBench's** four scenarios (arXiv
2603.27476), because that is the existing benchmark a reader is most likely to
compare this against, and because its authors chose those categories without
reference to our corpus.

## Against PeopleSearchBench's scenarios

| Their scenario | Their n | titer coverage | Why |
|---|---|---|---|
| **Expert / deterministic search** | 28 | **Strong** | This is the only scenario with verifiable answers, and it is exactly what an attested filing provides. Our whole corpus is this category. |
| **Recruiting** | 30 | **Weak** | Recruiters search engineers, designers, clinicians. Section 16 filers are officers and directors. The overlap is executive search only. |
| **B2B prospecting** | 32 | **Partial** | Prospectors target VP and director level at private companies. Our population is public-issuer officers, skewed senior and skewed listed. |
| **Influencer discovery** | 29 | **None** | Influence is not attested by any filing. Out of scope and not approximated. |

**The honest summary: titer covers one of their four scenarios well and one
partially.** It is deeper on the scenario where truth is checkable and absent
where it is not. That is a deliberate trade, not an oversight, but it means
titer is not a replacement for PeopleSearchBench and should not be cited as one.

## Population gaps

- **Non-US.** SEC filers only. No UK, EU or APAC coverage. Companies House
  would have supplied the UK arm; it was excluded because its person identifier
  increments when someone changes address or name (`docs/DECISIONS.md` D003).
- **Private companies.** Registered issuers only. The majority of a GTM buyer's
  targets are not here.
- **Non-executives.** Officers, directors and ten-percent owners. No individual
  contributors, no middle management.
- **Seniority skew, unmeasured in its effect.** Executives have more web
  presence than the average target, so providers should do *better* here than on
  a representative population. Any measured error rate is therefore plausibly a
  **lower bound** on the rate a buyer would experience. We state this rather than
  claiming external validity we have not earned.
- **Entity filers.** Roughly 5-8% of reporting owners are legal entities, not
  humans, and are excluded by rule. The exclusion rate is published.
- **Titles.** `RPTOWNER_TITLE` is non-empty on 65.9% of rows; unmatched titles
  become `UNKNOWN` and are excluded from the title atom rather than scored. The
  exclusion rate is published.

## Provider gaps, caused by contract terms rather than effort

Two providers plus a floor is a thin comparison set. It is thin for legal
reasons, and those reasons are published:

- **Apollo** — excluded. Its Terms prohibit disclosing benchmark results without
  prior written consent. Consent has been requested; until it arrives, Apollo is
  absent and its absence says nothing about its quality.
- **People Data Labs** — excluded. Its subscription agreement sweeps
  "information derived from the Services" into confidentiality, and requires
  deletion of all data within 30 days of termination, which is incompatible with
  a retained reproducible corpus.
- **Clay** — excluded on comparability, not law. It orchestrates 75+ enrichment
  tools rather than serving a proprietary index, so measuring it would answer a
  different question.
- **Exa** — included, self-serve only. If an Order Form is ever signed, MSA
  §2.4(j) retroactively prohibits publishing this analysis.

A reader should treat the provider set as "who could be measured lawfully at
this budget", not "who matters".

## Measurement gaps

- **The paid `confidence` field is not tested.** H3 calibrates the free signals
  only. At $5 the paid field is out of reach, and `docs/ETHICS.md` section 3
  declines to buy contact data to reach it regardless of budget.
- **One measurement window.** A living index is a moving target; every number
  here describes one window, recorded to the day.
- **Cross-sectional, not longitudinal, staleness.** R1 infers a survival curve
  from a single snapshot across many elapsed-day values. It does not watch one
  person's record update. A provider that back-fills history would look fresher
  than it is, and we cannot distinguish that case.
- **No transfer claim for the trained policy.** It is trained on a fitted
  simulator and evaluated on held-out real calls. Behaviour under live traffic,
  at a different budget, or against a provider not in the fit is unmeasured.

## What would close each gap

Each is named with the trigger that resolves it, so none of these is an
open-ended placeholder.

| Gap | Closed by |
|---|---|
| UK / non-US population | Companies House Product 216 access being granted |
| Apollo absent | Written benchmark consent arriving |
| Paid `confidence` untested | A budget increase **and** a proportionality argument in DECISIONS, not a budget increase alone |
| Cross-sectional staleness only | A forward panel: re-query the same tasks at intervals after a fresh filing |
| Recruiting / prospecting scenarios | A second Tier A oracle covering non-executive roles; none currently identified |
