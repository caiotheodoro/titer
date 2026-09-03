# RUBRIC — how this repository grades itself

Self-scoring is evidence of intent, not of quality. It is published because
refusing to score yourself is worse, and because the gap between the self score
and an independent cold read is itself informative.

| # | Criterion | Weight | W0 self-score | Note |
|---|---|---|---|---|
| 1 | Ground truth is a program, not an opinion | 15 | 15 | Filing-attested; no model assigns any label |
| 2 | Every reported number carries an interval | 10 | — | No numbers yet |
| 3 | Trivial floor is reported and must be beaten | 10 | 10 | `webfloor` fixed in D020 before any measurement |
| 4 | Pre-registration frozen before `src/`, publicly hashed | 10 | 10 | Git history plus a public HF hash at W0 |
| 5 | Unflattering findings lead, not footnoted | 10 | — | Cannot be scored before results exist |
| 6 | Coverage stated in someone else's vocabulary | 5 | 5 | PeopleSearchBench's four scenarios |
| 7 | Red team attacks own claims, with LIVE ones kept | 5 | 5 | 11 attacks, 4 carried as LIVE |
| 8 | Cost asymmetry modelled, ranking stability reported | 10 | — | Profiles fixed; no results |
| 9 | Environment health gate before any training run | 10 | — | Gate specified, not yet built |
| 10 | Across-seed spread published for every trained arm | 10 | — | Rule fixed; nothing trained |
| 11 | Ethics constraint enforced mechanically, not asserted | 5 | 5 | `make privacy-gate` inside `make validate` |

**W0 self-score: 50 of 50 available.** Sixty points are unavailable because they
require results that do not exist. That is the honest state, not a good score.

An independent cold read should be requested at W3 and again at W7, and the
number recorded here beside the self-score even when it is lower. A sibling repo
scored itself 82 and took 75 from an independent pass; both are published.
