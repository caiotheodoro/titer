# DATASET CARD — titer-edgar-officers

**Status: not released.** Scheduled for W1. This card is written first so the
release cannot outrun its own documentation.

## What it is

Person-company-role-date tuples attested by SEC Forms 3, 4 and 5, published as
**pointers, not records**.

Each row: SEC accession number, reporting-owner CIK, issuer CIK, `role_class`,
`title_class`, `period_of_report`, `filing_date`, name-collision degree, and a
salted hash of the raw name string.

## What it is not

It does not contain assembled personal records, email addresses, phone numbers,
postal addresses, social profiles, or dates of birth. Raw name strings are not
redistributed; they are reconstructable by anyone from the SEC's own free files
using the accession numbers.

## Source and licence

US Government public domain (SEC Insider Transactions Data Sets). Coverage
2003q3 onward — mandatory electronic Section 16 filing began mid-2003.

## Construction

Join `REPORTINGOWNER` to `SUBMISSION` on `ACCESSION_NUMBER`. Inclusion rules,
closed taxonomies and the exclusion accounting are specified in `CONTRACTS.md`
§2-3. No model participates in any labelling step, including title
normalization, which is regex-only and versioned as `title_map/v1`.

## Known limitations

- `RPTOWNERCIK` is unique per filer *registration*, not guaranteed one per human.
  Sound as a negative discriminator; presumptive as a positive one. A measured
  contamination bound ships with the dataset.
- ~5-8% of reporting owners are legal entities and are excluded by rule; the
  rate is published.
- `RPTOWNER_TITLE` is non-empty on about 66% of rows; unmatched titles become
  `UNKNOWN` and are excluded from title scoring rather than scored.
- Population is US officers and directors of registered issuers. See
  `docs/COVERAGE.md` for what that excludes, stated in an external vocabulary.

## Intended use

Evaluating identity resolution and index freshness. **Not** intended for, and
not to be used for, locating or contacting individuals.

## Rectification

A person appearing in the pointer set may request removal; honoured within 7
days without requiring justification, recorded as a count and never as an
identity. See `docs/ETHICS.md` §6.
