# SURVEY: the field, as of 2026-09-02

## Who sells people resolution

Ploid, Exa (Websets), People Data Labs, Apollo, Clay, ZoomInfo, Cognism and a
long tail. Two shapes: proprietary indexes (Ploid, PDL, Apollo) and
orchestrators that waterfall over other tools (Clay).

## What they claim

- **Ploid**: *"the largest living index of people in the world"*, 3B+ people,
  *"profiles refresh as people change jobs... so you reason over who someone is
  today, not who they were at the last crawl."* No published accuracy figure. A
  reported CEO interview cites 1.4B against the 3B+ marketing number; the primary
  source is unverified and the discrepancy is worth probing, not asserting.
- **Apollo**: the most quantified and therefore the most testable: 240M+
  contacts, *"98% email accuracy rate"*, 150M contacts refreshed monthly,
  *"less than 1% invalid direct phone numbers"*, data *"Refreshed in real-time."*
- **People Data Labs**: publishes dataset counts (2.47B records) but **no
  accuracy percentage**; argues philosophy instead, that false-positive merges
  are *"more detrimental than false-negatives"*. Freshness is documented as
  **monthly** API updates, with per-record `job_last_verified` fields.
- **Clay**: claims to *"often double or triple data coverage rates"* versus an
  incumbent, citing 30% to 80% coverage.
- **Exa**: the weakest public claims; no accuracy percentage or coverage count
  for people data.

Note the shape of this: the vendor with the strongest freshness claim
(*"real time"*, Ploid) publishes no accuracy number, and the vendor that
publishes an honest freshness cadence (monthly, PDL) publishes no accuracy
number either. Nobody publishes both, and nobody publishes an interval.

## What has been measured independently

- **PeopleSearchBench** (arXiv 2603.27476): 119 queries, 4 platforms, three
  dimensions, bootstrap intervals, judge validated at kappa 0.84. Explicitly does
  not measure identity resolution, false merges, or cost.
- **openbenchmarks.com/company-enrichment**: 282 companies, human-verified,
  independent, public repo, no intervals, companies not people.
- **Vendor "studies"**: mutually contradictory. The same provider at 42.4% in
  one and 78% in another; a third puts the category average near 50% real
  accuracy against 95%+ marketing claims. No methodology, no intervals, and the
  publisher is usually a competitor.

## The gap this repository targets

Nobody has published, for any vendor: a false-merge rate against attested ground
truth, a staleness curve against attested change dates, a calibration of the
signals a caller gets for free, or a cost-priced decision policy over the
provider's own tiers.

Ploid's Terms §12 make the gap sharper rather than softer: *"We do not warrant
that outputs will be accurate, complete, or suitable for any particular
decision."* The marketing asserts currency; the contract warrants nothing; and
no public instrument exists to tell a buyer which is closer to the truth.
