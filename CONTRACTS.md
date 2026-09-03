# CONTRACTS — frozen definitions

Everything in this file is load-bearing. Nothing here changes without an
append-only entry in `docs/DECISIONS.md` **and** measured evidence for the
change. A number in `docs/BENCHMARK.md` that cannot be traced to a definition
here is not a result.

Frozen: 2026-09-02. Version: `contracts/v1`.

---

## 1. Attestation tiers

A ground-truth tuple carries the tier of the document that attests it. The tier
is a property of the source, never of our confidence in it.

| Tier | Meaning | Source in v1 |
|---|---|---|
| **A** | Attested by a filing with legal consequence for misstatement, carrying a filer-assigned identifier | SEC EDGAR Forms 3/4/5 |
| **B** | Self-asserted to a registry, no legal consequence, identifier is self-claimed | ORCID public employment affiliations |

Tier A is the corpus. Tier B exists so the **attestation ladder** is measurable:
if a provider scores better against self-asserted data than against filings,
that is evidence the index is built from self-reported profiles rather than
records. That contrast is a finding about how an index works, not a ranking.

A tuple is never promoted between tiers. Tier B results are never pooled with
Tier A results in any headline number.

---

## 2. The attested tuple

One row of ground truth, derived by joining `REPORTINGOWNER` to `SUBMISSION` on
`ACCESSION_NUMBER` in the SEC Insider Transactions Data Sets.

```
AttestedTuple = {
  person_cik:      str   # RPTOWNERCIK   - filer-assigned, never recycled
  person_name_raw: str   # RPTOWNERNAME  - free text, exactly as filed
  issuer_cik:      str   # ISSUERCIK
  issuer_name_raw: str   # ISSUERNAME
  issuer_ticker:   str   # ISSUERTRADINGSYMBOL, may be empty
  role_class:      set   # from RPTOWNER_RELATIONSHIP - closed, see section 3
  title_raw:       str   # RPTOWNER_TITLE - free text, may be empty
  title_class:     enum  # deterministic regex normalization, see section 3
  period:          date  # PERIOD_OF_REPORT - the attested event date
  filed:           date  # FILING_DATE     - when it became public
  accession:       str   # ACCESSION_NUMBER - the pointer we publish
}
```

**Published form.** Only `accession`, `person_cik`, `issuer_cik`, the derived
classes, the dates, and hashes of the raw name strings are released. See
`docs/ETHICS.md`. Raw name strings are reconstructable by anyone from the SEC's
own free files; we do not redistribute them.

### 2.1 Inclusion rules

A row enters the corpus only if all hold:

1. `RPTOWNER_RELATIONSHIP` contains `Officer` or `Director`. This excludes the
   roughly 5-8% of reporting owners that are legal entities rather than humans
   (measured: the first row of 2025Q1 is `Apollo Management Holdings GP, LLC`,
   relationship `TenPercentOwner`).
2. `PERIOD_OF_REPORT` and `FILING_DATE` both parse as dates, and
   `PERIOD_OF_REPORT <= FILING_DATE`.
3. `RPTOWNERCIK` is non-empty and numeric.
4. Filing quarter is `2003q3` or later. Mandatory electronic Section 16 filing
   began mid-2003; earlier coverage is not representative and is excluded
   rather than silently thinned.

Every exclusion is counted and the counts are published in `docs/COVERAGE.md`.
An exclusion rate that is not published is a defect.

---

## 3. Closed taxonomies

### 3.1 role_class - attested, no normalization

`RPTOWNER_RELATIONSHIP` is already a closed comma-joined set in the source
files. We parse it into a set and never rewrite it.

```
RoleClass in { DIRECTOR, OFFICER, TEN_PERCENT_OWNER, OTHER }
```

Measured 2025Q1 distribution over 66,287 owner rows: `Officer` 34,785,
`Director` 16,506, `Director,Officer` 7,385, `TenPercentOwner` 3,492,
`Director,Officer,TenPercentOwner` 1,297, `Director,TenPercentOwner` 1,107,
`Other` 1,101, `Director,Other` 204.

### 3.2 title_class - normalized, deterministic, versioned

`RPTOWNER_TITLE` is free text (`"CEO"`, `"Chief Executive Officer"`,
`"President and CEO"`) and is non-empty on **65.9%** of 2025Q1 rows.
Normalizing it is a judgment call, and a judgment call that a model makes would
leak a model-decided label into a corpus that claims to be attested.

Therefore:

- Normalization is **regex-only and deterministic**. The pattern set is frozen
  in `src/titer/corpus/title_map.py` and versioned as `title_map/v1`.
- **No model, at any point, assigns a title_class.**
- `title_raw` is retained beside `title_class` on every row, always.
- Any title the frozen patterns do not match becomes `UNKNOWN`.

```
TitleClass in { CEO, CFO, COO, CTO_CIO, PRESIDENT, CHAIR,
                GC_LEGAL, OFFICER_OTHER, UNKNOWN }
```

**`UNKNOWN` is never scored.** A task whose target has `title_class = UNKNOWN`
is excluded from the title atom - it counts as neither a match nor a mismatch -
and the exclusion rate is published. Scoring `UNKNOWN` in either direction would
convert our own coverage gap into a provider's score.

---

## 4. Outcome classes

What a provider or policy returned, for one task, judged against one attested
tuple. Exactly one class applies.

| Class | Condition |
|---|---|
| `CORRECT` | Returned identity resolves to `person_cik` |
| `FALSE_MERGE` | Returned a *different* `person_cik`, at stated confidence >= tau |
| `UNSURE_WRONG` | Returned a different `person_cik`, at confidence < tau |
| `MISS` | Returned nothing, `not_found`, or an empty result set |
| `ABSTAIN` | Explicitly declined to answer |
| `STALE` | Returned `person_cik` correctly but attached to a superseded employer - the R1 signal |

`FALSE_MERGE` is the expensive error and the reason this project exists. It is
separated from `UNSURE_WRONG` because being wrong while hedging is a materially
different failure from being wrong while confident.

### 4.1 Resolving "resolves to person_cik"

Providers do not return CIKs. The mapping from a provider's returned identity to
a CIK is itself a decision, and it is made **once, deterministically, before any
scoring**, by exact match on the SEC's own `cik-lookup-data.txt` plus a frozen
name normalization versioned as `name_norm/v1`. Ambiguous mappings are recorded
as `UNRESOLVABLE` and excluded from scoring with the rate published. We never
let a model adjudicate this mapping.

### 4.2 The CIK caveat, stated plainly

`RPTOWNERCIK` is unique per *filer registration*, not guaranteed one-per-human.
A person who registered twice can hold two CIKs and the SEC publishes no merge
table.

The consequence is asymmetric:

- **Different CIK implies provably different registration.** Sound. This is what
  `FALSE_MERGE` detection rests on, and it is the direction we depend on.
- **Same human implies same CIK.** *Presumptive only.* A provider penalised with
  `FALSE_MERGE` may have found the same human under a second registration.

We therefore publish a measured upper bound on this contamination - the rate of
distinct CIKs sharing an exact normalized name *and* an overlapping issuer - and
report `FALSE_MERGE` both raw and net of that bound. This limitation belongs in
the README, not a footnote.

---

## 5. Cost profiles

Severity is a property of the error. Cost is a property of the caller. A single
hand-picked penalty ratio is unfalsifiable, so we report expected loss under
four named profiles and treat **ranking stability across profiles as the
result** - a ranking that flips between profiles is a more interesting finding
than a win.

Units are relative; only ratios matter.

| Profile | `MISS` | `FALSE_MERGE` | `UNSURE_WRONG` | `ABSTAIN` | `STALE` |
|---|---|---|---|---|---|
| `recruiter` | 1 | 2 | 1 | 0.5 | 1 |
| `gtm_outbound` | 1 | 5 | 2 | 0.5 | 2 |
| `kyc_sanctions` | 3 | 50 | 10 | 1 | 5 |
| `journalism` | 1 | 100 | 20 | 0.5 | 3 |

`CORRECT` costs 0 in every profile.

### 5.1 The flat profile is an integrity probe, not a result

| Profile | every non-`CORRECT` class |
|---|---|
| `flat` | 1 |

Under `flat`, the expected-loss ranking **must** equal the plain accuracy
ranking. If it does not, the harness has a bug. `flat` is never reported as a
result; it is a test that fails the build.

---

## 6. Reward (R4 environment)

```
R = sum(atoms) - lambda * acu_spent - K_profile * [confident and wrong]
                                    + a * [correct abstention]
```

**Atoms - three, each checked by a program against the filing:**

1. returned identity resolves to `person_cik`
2. `title_class` matches (skipped when the target is `UNKNOWN`, per 3.2)
3. the attested `period` falls inside the returned employment window

**Prohibited:** any shaping term. No credit for searching, for narrowing the
candidate set, for "checking evidence", or for any intermediate behaviour.
Shaped exploration produces performative exploration; the wanted behaviour has
to emerge from the outcome or it is not real.

**Efficiency:** the `- lambda * acu_spent` term is applied **only among
successes**. Applied to failures it rewards failing cheaply, which is the
degenerate policy `abstain_always` wearing a disguise.

**Floors that must be beaten**, all reported, none omitted if unflattering:
`never_verify` (accept rank-1 of the cheapest search), `always_deep_verify`
(spend the maximum every time), `abstain_always` (the degenerate floor), the
untrained base model, and a frontier model given the same tools and no budget
discipline.

---

## 7. Splits and contamination

- **Task signature** = SHA-256 over the sorted ground-truth fields
  (`person_cik`, `issuer_cik`, `role_class`, `title_class`, `period`).
- Splits are **signature-disjoint**. Train, hill-climb, and the frozen test set
  share no signature.
- A **leak probe** must read `1.0` on a deliberately leaked split and `0.0` on a
  clean one. A leak probe that cannot detect an intentional leak is not evidence
  of a clean split.
- The frozen test split is drawn once, by seed, and is **never** used for
  checkpoint selection. Checkpoints are selected on the hill-climb split.
- Near-duplicate rate (same person, different quarter) is measured and published
  rather than assumed to be zero.

---

## 8. Difficulty

**Name-collision degree** `d(name)` = the number of distinct `RPTOWNERCIK`
sharing an exactly-normalized `RPTOWNERNAME` across the corpus. It is measured
from the oracle, not assigned, and it indexes the `FALSE_MERGE` failure mode
directly.

Bands: `d=1` (unique), `d=2..3` (low), `d=4..9` (medium), `d>=10` (high).

Secondary axes, both measured: issuer obscurity (filing count per `ISSUERCIK`)
and filing recency (days from `FILING_DATE` to the measurement date).

RL tasks are filtered to the 10-80% solve band at the SFT checkpoint. Tasks
outside the band are removed from the RL mix and **kept in eval**.

---

## 9. What this repo does not claim

- Not a claim that any provider's index is bad. A measured rate under a stated
  cost profile at a stated `n`, with an interval, is the whole claim.
- Not a claim about people who do not appear in SEC filings. The corpus is US
  officers and directors of registered issuers. `docs/COVERAGE.md` states this
  in the vocabulary of what a buyer actually wants, not ours.
- Not a claim that `RPTOWNERCIK` is a person key. See 4.2.
- Not a claim that the trained policy transfers to live traffic. It is trained
  on a fitted simulator and evaluated on held-out real calls; the gap is
  measured, published, and named as the central limitation.
