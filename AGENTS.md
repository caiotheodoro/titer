# AGENTS — the short path

For an agent or a reviewer who should not read the whole README first.

## What this is

An instrument measuring how often commercial people-search indexes confidently
name the wrong human, and what it is worth paying to find out. Ground truth is a
SEC filing, not a model's judgement.

## Read in this order

1. `CONTRACTS.md` — every definition. Frozen. Nothing changes without a
   DECISIONS entry **and** measured evidence.
2. `docs/PRE-REGISTRATION.md` — hypotheses, estimators, falsification
   conditions, and the pre-committed power rule. **Never edit this file.**
3. `docs/DECISIONS.md` — append-only. Read D003 (oracle tiers), D019 (provider
   Terms gate).
4. `docs/ARCHITECTURE.md` — the seams, which is where mistakes leak.
5. `docs/HANDOFF.md` — what not to do.

## Hard rules

- **No model assigns a ground-truth label.** Not the title class, not the
  identity-to-CIK mapping, not the outcome class. The script owns mechanism; the
  model owns meaning; the only decision a model makes here is whether to spend.
- **Do not sign an Exa Order Form or MSA.** It retroactively bans publishing this
  analysis. Self-serve only.
- **Do not call Apollo or People Data Labs.** Excluded by their Terms.
- **Do not call any enrichment or contact-reveal endpoint.** Ever.
- **Do not edit `docs/PRE-REGISTRATION.md`.** Supersede with a dated DECISIONS
  entry carrying a reversal clause.
- **No margin without its across-seed spread.** Minimum four seeds.
- **No shaping terms in the reward.** Outcome only.
- **Scrape SEC quarterly filenames; never generate them.** A generated recent
  quarter 404s and truncates the corpus silently.

## Current state

W0. `src/` is empty by design. `MEASUREMENT_CARD.json` reads `NOT_VERIFIED` and
will until every gate passes. No result exists. Any number you find in this repo
today is an illustration of format, not a finding.

## Verify

```bash
make validate
```
