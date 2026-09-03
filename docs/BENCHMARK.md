# BENCHMARK

Results tables. **Empty by design at W0.** No measurement has been taken.

Every table below will carry, without exception:

- the achieved `n`, and which branch of `docs/PRE-REGISTRATION.md` §3 fired
- a 95% interval on every rate, by paired bootstrap over tasks
- the measurement window, recorded to the day
- expected loss under all four cost profiles, not one
- the `flat` integrity probe result as a precondition
- for R2, false merges both raw and net of the contamination bound
- for any trained arm, the across-seed spread

A number appearing here without its interval is a defect, and the claim gates in
`tests/` are intended to catch it.

## R1 — staleness half-life

*Not measured.*

## R2 — false merge under name collision

*Not measured.*

## R3 — calibration of the free signals

*Not measured.*

## R4 — value-of-information policy

*Not measured.*

## Baselines

| Arm | Status |
|---|---|
| `webfloor` — free web search (trivial floor) | not measured |
| `never_verify` | not measured |
| `always_deep_verify` | not measured |
| `abstain_always` (degenerate floor) | not measured |
| untrained Qwen3-8B base | not measured |
| GPT-5.6-mini, no budget discipline | not measured |
