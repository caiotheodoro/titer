# HANDOFF — operator log

What to run, and what not to do. Read before touching anything.

## Do not do

- **Do not sign an Exa Order Form or MSA.** MSA §2.4(j) prohibits making
  available "any analysis of the operation or benchmarking of any Services".
  Signing one retroactively bans publishing this work. Self-serve only.
  (`docs/DECISIONS.md` D019.)
- **Do not call Apollo or People Data Labs.** Excluded by Terms. Apollo consent
  was requested; if it arrives, add a new DECISIONS entry first and measure in a
  clearly-labelled separate window. Never back-date into the primary table.
- **Do not call any enrichment or "reveal" endpoint.** Out of scope on
  proportionality grounds, not budget. `docs/ETHICS.md` §3.
- **Do not generate SEC quarterly filenames.** Scrape them off the landing page.
  A generated `2026q2_form345.zip` returns 404 while the page advertises that
  quarter, so a generator truncates the corpus silently.
- **Do not run two full runs at once**, and do not launch a slow background run
  without a trailing `| tail` — output buffers and the log stays empty.
- **Do not edit `docs/PRE-REGISTRATION.md`.** Supersede it with a dated
  DECISIONS entry carrying a reversal clause.
- **Do not trust a local green.** Verify from a fresh tree; a stale venv passes
  things it should not.

## Budget ledger

| Item | Value | Source |
|---|---|---|
| Ploid pay-as-you-go | $0.20 / ACU | live pricing page, 2026-09-02 |
| Ploid `/v1/person` | 25 ACU = **$5.00** PAYG | docs say "$2.50 face value" — that is the Business seat rate of $0.10/ACU |
| Ploid search | $0.10 per 10 matches | live pricing page |
| Ploid free-plan credits | **not published** — budgeted as zero | absent from the live page; the "200 credits" figure circulating in search snippets is from a superseded pricing model |
| Ploid rate limit | Free 10 rpm, PAYG 30 rpm | errors-and-limits doc |
| Exa free tier | $20 on signup + $10/month recurring | pricing page |
| Exa rate limit | `/search` 10 QPS | rate-limits doc |
| Available | **$5 Ploid credit** | user, 2026-09-02 |

Do not build cost models from cached search snippets. The live Ploid page and
the snippets disagree on the entire pricing model.

## Source access notes

- **SEC**: declare a `User-Agent` identifying the project plus a contact address.
  Stated limit 10 req/s. The corpus needs ~80 requests total; do not crawl EDGAR
  page by page when a bulk file exists.
- **ORCID** (Tier B): anonymous public API works with no token, 12 req/s, 25k
  reads/day per IP. Prefer the annual bulk file. **Unverified**: whether the
  Public Data File summaries are truncated to three affiliations, as the UI docs
  describe for record summaries. Check one tarball before building on it.
- **Companies House**: Product 216 requested via the developer forum. No SLA.
  Never on the critical path.

## Compute

- Modal L4 is sufficient for 4-bit QLoRA on an 8B. bf16 27B OOMs there.
- Check dataset size before launching a training run. A sibling repo once
  trained on an empty dataset.
- Keep a warm container for the eval server rather than paying cold starts per
  call.

## Publication

- `hf repos create --space-sdk`, not `--sdk`.
- Collection description limit 150 chars; item note limit 500 chars.
- House style: the title carries the claim, the description is one result line
  plus `Code: <url>`.
- Check `git ls-files`, not `ls`, before claiming a file ships. A sibling repo
  submitted with its video source untracked.
