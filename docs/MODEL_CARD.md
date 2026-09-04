# MODEL CARD: titer value-of-information policy

**Status: not trained.** Scheduled for W6.

## Intended capability

Given a person-resolution task, a set of priced provider actions and a budget,
decide which calls to make, when to stop paying, and whether to answer or
abstain. The objective is expected loss per dollar under a stated cost profile,
not accuracy.

## Planned arms

| Arm | Base | Method |
|---|---|---|
| headline | Qwen3-8B | 4-bit QLoRA, LoRA on all layers incl. MLP, SFT then GRPO/RLVR |
| ablation | Qwen3-4B | same recipe; "how small can the spender be" |

Baselines it must beat: `webfloor`, `never_verify`, `always_deep_verify`,
`abstain_always`, the untrained base, and GPT-5.6-mini with identical tools and
no budget discipline.

## Training data and reward

Rollouts in the titer OpenEnv environment. Reward is three program-checked atoms
against the filing, minus spend, minus a heavy penalty for being confidently
wrong, plus a small credit for correct abstention. No shaping terms.

## The central limitation, stated before training

The policy is **trained on a cost/error simulator** fitted to a small real
sample, because live rollouts at $5 per verification are arithmetically
impossible. It is **evaluated on held-out real provider calls**, and the
sim-to-real gap is published as a number rather than as a caveat.

Behaviour under live traffic, at a different budget, or against a provider not
in the fit, is unmeasured.

## Reporting rules fixed in advance

- No margin is quoted without its across-seed spread. Minimum four seeds. If the
  spread exceeds the margin, there is no claim.
- Checkpoints are selected on the hill-climb split at peak held-out, on the full
  metric profile, never on the frozen test split and never on one scalar.
- Results are reported across all four cost profiles.

## Out of scope

Not a people-search product. Not a matcher. It decides what to buy, not who
someone is.
