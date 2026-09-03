# EVALS CARD

**Status: specified, not run.**

## Ladder

| Rung | Purpose | Gate |
|---|---|---|
| smoke | harness wiring | gold trajectory scores 1.0, no-op scores 0.0 |
| frozen regression | catch silent breakage | drawn once by seed; never used for checkpoint selection |
| hill-climb | checkpoint selection | signature-disjoint from the frozen split |
| online | post-publication | n/a in v1 |

## Integrity probes, all required

| Probe | Pass condition |
|---|---|
| gold trajectories | reward exactly 1.0 |
| no-op / empty agent | reward exactly 0.0 |
| inverted labels | score collapses |
| `flat` cost profile | expected-loss ranking equals accuracy ranking |
| leak probe | 1.0 on an intentional leak, 0.0 on a clean split |
| `abstain_always` | must lose under every reportable profile, or the abstention credit is mis-set |

Any probe failing blocks the wave. These are tests, not diagnostics.

## Environment health report

Emitted by `scripts/env_health.py` before any training run:

```
env:  harness:  n_tasks:  k_rollouts:
verifier_gold:  verifier_noop:
solve_rate_hist: [bins]
pct_in_band_10_80:
pct_groups_zero_adv:
sampler_trainer_kl:
train_vs_eval_protocol_diff:
leakage: train ∩ eval = 0   near_dup:
```

No report, no training run.

## Contamination

Task signature = SHA-256 over sorted ground-truth fields. Splits are
signature-disjoint. Near-duplicate rate (same person, different quarter) is
measured and published rather than assumed to be zero.
