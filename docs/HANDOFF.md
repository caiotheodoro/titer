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

## Published rate limits must reach the transport

Ploid Free is **10 requests/minute**. That number was in the budget ledger below
from W2 and never made it into `http.py`, which fired at 60/min and drew 14
consecutive 429s - wasting most of a run on a grant denominated in credits.
Rate-limited calls are not charged, so nothing was lost but time; a paid 429
would have been worse.

`PROVIDER_INTERVAL_S` now carries one interval per provider, taken from each
provider's published limit. Writing a limit in a document is not the same as
enforcing it.

## The rule R001 cost us

**Before spending a budget on an arm, run one task through it and READ THE
RETURNED ROWS VERBATIM.** A pilot that only counts outcomes cannot tell a bad
query from a bad index - both look like a MISS. We spent $4.60 of a $5 grant
producing a 0/21 result that turned out to measure our own wire format, and the
rows had been saying so from the first call: the right names attached to
eponymous small businesses is what a malformed query looks like, not what a
missing person looks like.

Corollary: check the provider's documented request shape against what the
adapter actually sends. Ploid documents structured `filters`; we were putting
the company in the free text.

## The cited-path gate and clean clones

`scripts/validate.py` checks that every cited path resolves. It passed locally
and failed in CI on the first run, because `data/replay.jsonl` and
`docs/private/` exist on the machine that wrote the docs and are gitignored
everywhere else.

**A gate that only passes where its author sits is not a gate.** Cited paths
absent from a clean checkout are now declared in one of three files, so the
reason stays visible and a typo still fails:

| File | Meaning |
|---|---|
| `PLANNED-PATHS.txt` | promised by a later wave |
| `EXTERNAL-PATHS.txt` | lives in a sibling repository |
| `GITIGNORED-PATHS.txt` | generated locally, never committed |

Before trusting a green `validate`, run it against a fresh `git clone` of the
repo, not the working tree.

## Collections

House style across the six collections: **the title carries the claim** in two
contrasting clauses ("ReconForge: lost on accuracy. Caught every HIGH."), the
**description is one result line plus `Code: <url>`**, and **item notes lead
with the caveat**, not the win — assay's model note opens "A negative result,
published so the ablation row is checkable."

Hard limits, both enforced server-side and both hit on the first attempt:
**description 150 characters, item note 500.** Check lengths before calling the
API; the failure is a validation error, not a truncation.

`create_collection(title, namespace, description, exists_ok=True)` then
`add_collection_item(slug, item_id, item_type, note, exists_ok=True)`. The
collection URL redirects to a slug without the trailing hash.

## Publishing to the Hub

`hf upload` re-attempts `repos/create` on every call and gets **402 Payment
Required** even for a **static** Space, which HF documents as free. D016
anticipated the 402 from assay's experience and was right about the wall,
wrong about the cause - it is not the SDK, it is the redundant create.

Use the Python path against an already-created repo:

```python
from huggingface_hub import HfApi
HfApi().upload_folder(folder_path="space", repo_id="<user>/<name>",
                      repo_type="space", commit_message="...")
```

`short_description` in a Space README is capped at **60 characters** and the
upload fails validation, not silently.

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

- **SEC**: declare a `User-Agent` of the form `Company Name contact@domain`.
  Stated limit 10 req/s; real behaviour is burst-sensitive well below that, so
  `MIN_INTERVAL_S` is 1.5. The corpus needs ~80 requests total; do not crawl
  EDGAR page by page when a bulk file exists.

  **Two traps, both diagnosed the hard way on 2026-09-03:**

  1. **SEC's 403 page is titled "Request Rate Threshold Exceeded" regardless of
     cause.** Do not diagnose from the page title. It says rate limit when the
     actual problem is the User-Agent, which cost this project a wrong
     conclusion and a needless VPN connection.
  2. **A GitHub `users.noreply` address is rejected.** Measured with the same
     format and the same spacing across four domains:

     | User-Agent contact domain | Result |
     |---|---|
     | `example.com` | 200 |
     | a mainstream mail provider | 200 |
     | a project-owned domain | 200 |
     | GitHub `users.noreply` | **403** |

     SEC requires a *contactable* address; a noreply address is not one. Declare
     a real address you control. Do not declare one you do not - the policy is
     about being reachable, and a fake address defeats it.

     Addresses are not written into this repository. `TITER_SEC_UA` is read from
     the environment, and `scripts/validate.py` fails the build on any
     email-shaped string in a tracked file - it caught an earlier draft of this
     very table.

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
