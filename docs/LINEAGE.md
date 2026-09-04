# LINEAGE

What predates this repository, and from where. Written so that no idea here is
presented as more original than it is.

## Directly inherited, and reused rather than re-derived

| From | What | Where it lands |
|---|---|---|
| `assay` | Cost profiles as "severity is a property of the defect, cost is a property of the caller"; the trivial floor as the arm that must be beaten; the flat-profile integrity probe; published claim gates | `src/titer/costs/`, `docs/RUBRIC.md`, `tests/` |
| `assay` | `assay/src/assay/adapters/openenv.py` shape | `src/titer/env/` |
| `regretbench` / LossBench | Calibration and escalation machinery: reliability diagrams, ECE, Brier, isotonic recalibration, risk-coverage curves, the cost registry shape | `src/titer/metrics/`, `src/titer/costs/` |
| `vernier` | Conformal risk control / Learn-then-Test framing; the abstention cascade returning coverage and floor as an inseparable pair; ECE with 10 equal-width bins and empty bins never merged; pre-registration frozen before `src/` | `src/titer/metrics/`, `docs/PRE-REGISTRATION.md` |
| `reconforge` | The seed rule: no margin is quoted without its across-seed spread. Learned by publishing a headline whose across-seed SD was 2.86x the claimed margin and retracting it in its own README | `src/titer/train/`, `docs/PRE-REGISTRATION.md` H4 |
| `keel` | The `reset/step/state` protocol, `Actor = agent \| human \| probe`, `turnCap: 32`. A frozen spec with no implementation; this repo is its first | `src/titer/env/` facade |
| `blotter` | The left/right match-pair shape, in bank-reconciliation clothing. Structurally the same problem: two records, one match decision, an escalation cost | `src/titer/oracle/` |
| the forge line (`suture`, `specula`, `plumb`, `habeas`) | "Find a task where the ground truth is a program, not an opinion"; contamination control by task signature; the docs-before-`src/` discipline | throughout |

## The Space's design lineage

`space/index.html` follows **`regretbench/packaging/hf/static_space.py`**, the
LossBench control-plane Space (`caiotheodoro/lossbench-demo`), which is itself a
port of the design system in `cv-related/cv/src/styles/global.css`.

Taken from the sibling Space rather than reinvented: the short token names
(`--accent`, `--border`, `--text-2/3`), the 960px column, the 36px graph-paper
`body` grid fading at 45%, the mono `.kicker` with an accent `<b>`, `h1 .dot`,
`.standfirst`, `h2` demoted to an uppercase hairline rule, `.pill` / `.pill.esc`,
the `data-fade` / `data-delay` ladder and the
`prefers-reduced-motion` guard, which the CV itself lacks.

Taken from the CV directly: the `AboutStats` stat-tile block and the `.label` +
`.count` pill header.

**A note on how this was nearly got wrong.** A first exploration reported "no HF
Space uses the CV design system", and that claim was repeated to the user as
fact. It came from a repo-wide grep that was killed after 300s having written
zero bytes - silence from an unrun command, reported as a negative result. The
sibling Space existed the whole time. It is the same failure mode this project
documents elsewhere: a measurement that could not have observed the thing,
mistaken for evidence that the thing is absent.

## External prior art

- **PeopleSearchBench** (arXiv 2603.27476, ~Jul 2026). The closest existing
  work, and careful: 119 queries, four platforms, 95% bootstrap intervals, a
  judge validated at kappa = 0.84 against human annotators, code and queries
  public. titer differs on the oracle (filing versus model-with-web-search) and
  on what is measured (identity resolution, false merges, cost), which its
  authors explicitly list as out of scope. It is not superseded by this work and
  should not be described as such.
- **openbenchmarks.com/company-enrichment**. Independent, 282 companies,
  human-verified ground truth, public repository, no confidence intervals,
  companies rather than people. The stratified-cohort construction is a good
  model and is echoed in the `d`-band stratification here.
- **Vendor-published comparisons.** Not prior art in any useful sense. The same
  provider appears at 42.4% in one and 78% in another, both published by
  competitors, with no methodology and no intervals. They are the reason the
  power rule in `docs/PRE-REGISTRATION.md` §3 is pre-committed.
- **Entity resolution literature.** Record linkage as pairwise match/non-match
  classification is decades old. The contribution here is not a matcher; it is a
  cost-priced, filing-attested *evaluation* of commercial matchers, plus a policy
  that decides when to pay for one.
- **datamule**'s ~1M-row executive officer dataset from 8-K Item 5.02. Useful as
  a comparison baseline, not as ground truth: it is LLM-extracted from narrative
  prose, which is the construction this project excludes.

## Data provenance

- **SEC Insider Transactions Data Sets**: US Government public domain. Forms
  3/4/5, quarterly TSVs, coverage from 2006 in the packaged sets; corpus start
  is 2003q3 because mandatory electronic Section 16 filing began mid-2003.
- **ORCID Public Data File**: CC0 1.0, annual October release, hosted on
  Figshare. Tier B only.
- **Companies House**: Open Government Licence v3.0. Not used unless Product
  216 access is granted.
