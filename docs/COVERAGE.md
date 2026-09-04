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

## The cumulative narrowing, in one place

Each restriction was forced by a mismatch between what a filing can attest and
what a provider surface answers. None was chosen for convenience, and none is
applied quietly.

| Stage | Remaining | Why |
|---|---|---|
| People in the corpus | 230,405 | 4,206,080 rows, 2006q1-2026q2 |
| ...who actually moved employer | 46,332 (20.1%) | D022: the query fact and the scored fact must differ |
| ...whose target is their LAST employer | 30,607 (13.3%) | D028 C2: a people index returns a CURRENT employer |
| ...last attested within 5 years | **16,896 (7.3%)** | the corpus cannot see moves it never recorded |

**7.3% of the corpus is usable.** A reader should hold that against every rate
this instrument reports: the population measured is US public-company officers
and directors who changed employer, whose move is the most recent thing SEC
knows about them, and who filed recently. That is a narrow and unusually
well-documented slice of humanity, and providers should be expected to do
BETTER on it than on a representative target. Any error rate here is plausibly
a lower bound.

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

---

## The scholarly population (expertise study)

Same discipline, different gaps. Stated in the vocabulary an expert-sourcing
buyer would use, not ours.

| Gap | Size | Consequence |
|---|---|---|
| **Publication record is not expertise** | unquantifiable | A brilliant engineer who never publishes is invisible. The oracle attests *authorship*, and CONTRACTS A6 says so. |
| **OpenAlex `topics` is a top-N summary** | median 5 topics per author, for authors with ~120 works | This voided the first E1 run (R002). Negatives are now verified against `/works`, which is exhaustive - but only for the topics we ask about. |
| **The corpus is 20,000 of ~3.66M eligible authors** | 0.55% | Name-collision degree measured inside it is a sampling artefact and under-counts reality (D032). No collision rate from this corpus is a population rate. |
| **`works_count` band 20-500** | excludes both ends | Excludes merged author records (one real row carries 2.4M works across 42 affiliations) and excludes early-career researchers. |
| **ORCID required** | ~3.66M of a much larger population | Researchers without an ORCID iD are absent entirely. |
| **Institution required** | 849 of 20,878 dropped | Authors with no last-known institution are excluded, which skews away from the recently unaffiliated. |
| **English-language, Anglophone-indexed venues dominate OpenAlex** | not measured | A known bias of the source; we inherit it and do not correct it. |
| **Domain skew** | Physical Sciences 46,590 topic-instances vs Social Sciences 6,637 | Findings are weighted toward the physical sciences. |

**What the expertise study cannot say anything about:** engineers, clinicians in
practice, lawyers, and every other expert whose competence leaves no
bibliographic trace. That is most of the population an expert-sourcing platform
actually hires, and it is the single largest gap in this work.

## Environment coverage (R4)

The simulator is fitted from 500 real observations. Cells: `unique` 440, `low`
44, `medium` 16, **`high` 0**. The hardest collision band has no data at all, so
any policy trained on this simulator has never seen the cases the project was
built to study. Reported rather than smoothed.
