# AGENTS: the short path

For an agent or a reviewer who should not read the whole README first.

## What this is

An instrument measuring how often a commercial index confidently affirms
something false about a person, and what it is worth paying to find out. Ground
truth is an SEC filing or a publisher DOI. No model assigns a label.

## Read in this order

1. `CONTRACTS.md`: every definition. Frozen. Nothing changes without a
   DECISIONS entry **and** measured evidence.
2. `docs/PRE-REGISTRATION.md`: hypotheses, estimators, falsification
   conditions, and the pre-committed power rule. **Never edit this file.**
3. `docs/DECISIONS.md`: append-only. Read D003 (oracle tiers), D019 (provider
   Terms gate).
4. `docs/ARCHITECTURE.md`: the seams, which is where mistakes leak.
5. `docs/HANDOFF.md`: what not to do.

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

Published. Results exist and are in `docs/BENCHMARK.md`.

- **E1/E3 measured** on verified negatives, n=1,000 across four strata: Exa
  confirms attested expertise at 0.9600 [0.9279, 0.9781] and affirms claims
  about topics the person never published in at 0.1680 (adjacent subfield),
  0.1320 (adjacent field) and 0.0840 (different domain). It states 0.987
  confidence against 0.889 accuracy. The control arm never reaches zero, which
  bounds the prompt-interpretation objection at 8.4 points rather than leaving
  it open.
- **Two formal retractions** (`docs/RETRACTIONS.md`). Five of six headline
  numbers were artefacts of this harness. **No number about Ploid is claimed.**
- `MEASUREMENT_CARD.json` reads `PARTIALLY_VERIFIED` and names ten unmet claims.
  It is **generated** by `scripts/refresh_card.py`. Never hand-edit it.
- Independent cold read: **74/90** against a self-score of 78/90.

Before changing anything, read `docs/RETRACTIONS.md`. Every defect there looked
like a finding about a vendor until someone read the returned rows.

## Verify

```bash
make validate
```
