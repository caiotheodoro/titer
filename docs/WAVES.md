# WAVES

Execution order. Each wave ends: build → **fresh-context** review → fix fan-out
→ re-verify. A re-read in the same context is not a review.

| Wave | Deliverable | Exit condition |
|---|---|---|
| **W0** | Frozen docs, no `src/` | `make validate` green on docs gates; PRE-REGISTRATION hash published to a public HF repo; Apollo consent request sent; Companies House Product 216 request filed |
| **W1** | EDGAR corpus, oracle, leak probe | Leak probe reads 1.0 on an intentional leak and 0.0 on a clean split; exclusion counters reconcile; **HF dataset release #1** |
| **W2** | Adapters, replay cache, cost accounting | Measured cost per task per provider recorded; achievable matched `n` computed; PRE-REGISTRATION §3 branch selected and recorded |
| **W3** | R1 staleness, R2 false merge | Paired bootstrap intervals; matched-`n` table plus max-`n` table; contamination bound measured |
| **W4** | R3 calibration and abstention | Reliability diagram with unmerged bins; coverage and floor returned as a pair |
| **W5** | Simulator, OpenEnv env, keel facade | Env health report emitted: gold 1.0, noop 0.0, flat probe passes, solve-rate histogram, in-band %, zero-advantage group % — **then `assay` audits this environment and the audit is published** |
| **W6** | SFT → GRPO, 8B and 4B | ≥4 seeds per arm; across-seed spread computed **before** any margin is written; checkpoint selected on hill-climb, never on the frozen test split |
| **W7** | Publication | Datasets ×2, models ×2, static Space, collection, video, RED-TEAM updated, repo made public, then the outreach email |

## Ordering constraints that are not negotiable

- W0 before `src/`. Git history is the evidence.
- No provider call before D019's Terms gate is resolved. (Resolved 2026-09-02.)
- W1 before W2: the oracle must work before a credit is spent on a provider.
- W2 before W5: the simulator is fitted only to the W2 cache's training portion.
- W5's health gate before W6. No health report, no training run.
- Nothing is published from a training run whose across-seed spread exceeds its
  claimed margin.
