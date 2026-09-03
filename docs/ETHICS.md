# ETHICS

Written before `src/` exists, because a decision about other people's data taken
after the code works is a decision taken under sunk cost.

This project measures how well commercial people-search indexes resolve real
human identities. It cannot do that on synthetic people. So it handles data
about real, named individuals, and the constraints below are engineering
requirements enforced by `make privacy-gate`, not aspirations.

---

## 1. Who is in the corpus, and why that is lawful

Officers and directors of SEC-registered issuers, drawn from Forms 3, 4 and 5.

These people are not private individuals with respect to this fact. Section 16
of the Securities Exchange Act of 1934 **requires** them to file, by name, in
their capacity as an officer or director, and the SEC publishes those filings as
a public record precisely so that anyone may inspect them. The corpus asserts
nothing about any person that they were not legally obliged to state publicly
themselves.

The corpus is limited to that fact. It records that a named person held a role
at an issuer on a date. It records nothing about their private life.

**ORCID (Tier B)** is opt-in by construction: a researcher creates the record
and chooses its visibility. Only records already marked public are used. The
Public Data File is CC0.

**Companies House**, if it is ever used, is Open Government Licence v3.0 and
publishes only month and year of birth. We never request, store, or infer a full
date of birth.

---

## 2. What is published, and what never is

**Published:** SEC accession numbers, CIKs, issuer CIKs, the derived closed-class
labels, dates, and salted hashes of raw name strings. Anyone can rebuild the
full corpus from the SEC's own free files using these pointers. We distribute
the pointers; the SEC distributes the records.

**Never published, under any circumstance:**

- Email addresses, personal or work
- Telephone numbers
- Physical or postal addresses, including the street fields present in
  `REPORTINGOWNER.tsv`
- Social handles or profile URLs returned by any provider
- Any field a provider returns under a "reveal" or "enrichment" billing action
- Dates of birth, in any precision
- Any provider's raw response body

This holds even where the field is technically public. Aggregating scattered
public facts into a single convenient file is itself a privacy harm, and it is
the specific harm this repo exists to measure. Committing it would be
incoherent.

### 2.1 The replay cache

W2 records provider responses so that later waves can replay them without
re-spending credits. That cache is the highest-risk artifact in the repository.

- Contact fields are **stripped at ingest**, before the response is written to
  disk. Not at publication time. At ingest.
- The cache stores only: outcome-relevant identifiers, rank position,
  `resolution_source`, `identity_verified`, `last_seen`, latency, and ACU cost.
- The cache lives under `docs/private/` equivalent protection: gitignored, and
  `make privacy-gate` fails the build if a cache file appears in `git ls-files`
  or if any committed file matches the contact-field patterns.
- The gate runs inside `make validate`. A green validate that skipped the
  privacy gate is not green.

---

## 3. Enrichment calls: the line we do not cross

The providers under test will happily sell an email address or a phone number
for a named person. Buying one would sharpen H3.

We do not buy them. `POST /v1/enrich` and its equivalents on other providers are
outside the measurement design, and `docs/PRE-REGISTRATION.md` section 2 states
explicitly that the paid `confidence` field is not tested. The budget is a
convenient excuse; the reason is that acquiring contact details for hundreds of
real people, to grade a vendor, is not proportionate to the question being asked.

If the budget later grows, this does not change. A DECISIONS entry would be
required to change it, and the entry would have to argue proportionality, not
statistical power.

---

## 4. Load on the sources

- SEC: the corpus is built from roughly 80 quarterly zip files. SEC's stated
  limit is 10 requests per second with a declared `User-Agent`; we declare one
  identifying the project and a contact address, and stay far below the limit.
  We do not crawl EDGAR page by page when a bulk file exists.
- ORCID: anonymous public API, 12 req/s and 25k reads/day per IP. We use the
  annual bulk file rather than the API wherever possible.
- Providers: queried within their published rate limits, with `Idempotency-Key`
  set where supported so a retry is never double-billed.

---

## 5. Dual use

This work produces (a) a corpus that makes identity-resolution errors
measurable, and (b) a policy that spends money efficiently on people lookups.
Both could help someone build a better people-search product. That is a real
consequence and pretending otherwise would be dishonest.

The judgement, stated plainly: the asymmetry currently runs the other way.
Vendors already have the resolution capability and sell it at scale; what does
not exist is any public instrument for telling a buyer, a regulator, or a
journalist how often these systems confidently name the wrong human. Building
the instrument moves power toward the person being resolved, not away from them.

The policy in R4 is trained to spend *less*, and to abstain when unsure. Its
optimum is fewer lookups, not more.

We do not publish anything that makes it easier to find a specific individual.
The corpus is a list of people who already filed with the SEC, keyed by the
identifier the SEC itself assigned.

---

## 6. Rectification and takedown

A person who appears in the corpus may ask for removal. `README.md` carries the
contact address and this commitment:

- A request is honoured on the pointer set within 7 days, without requiring the
  requester to explain themselves or prove harm.
- Removal is recorded as a count in `docs/COVERAGE.md` - "n rows removed on
  request" - never as an identity.
- Because the corpus is pointers into public SEC filings, removal from this
  repository does not remove the underlying filing, and we say so rather than
  implying a power we do not have.
- Published results are not retroactively recomputed for a removal, because that
  would silently change a published number; the removal is noted alongside.

---

## 7. Findings about providers

If a measurement reveals a specific, serious defect in a live product - for
example, an identity confidently resolved to a demonstrably wrong human in a
high-stakes category - the finding goes to the provider before it goes public,
with a stated disclosure window. Drafts live in `docs/disclosures/` and are
shown to the user before filing. The rule inherited from `assay`: draft both,
show before filing.

Aggregate rates are not defects and are published normally.

---

## 8. What would make this project unpublishable

Named now, so it cannot be argued away later:

- If the only way to reach a usable `n` were to buy contact data at scale.
- If the corpus could not be reduced to pointers without losing reproducibility.
- If a provider's Terms of Service prohibited the measurement itself, rather
  than merely naming them in the results.

None of these is currently the case. If one becomes the case, the affected part
is dropped and the drop is published.
