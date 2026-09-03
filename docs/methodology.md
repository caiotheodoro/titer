# methodology

This repository follows the workspace forge recipe, adapted from adjudicating
documents to adjudicating identities.

1. **Find a task whose ground truth is a program, not an opinion.** Here: a
   Section 16 filing, with a filer identifier the SEC never recycles.
2. **Deterministic oracle.** Outcome classes and reward atoms are recomputed
   from the attested tuple. No model, no judge, anywhere in the label path.
3. **Contamination control.** Task signature = SHA-256 over sorted ground-truth
   fields; splits are signature-disjoint; a leak probe must read 1.0 on an
   intentional leak and 0.0 on a clean split.
4. **Cost before accuracy.** Severity is a property of the error; cost is a
   property of the caller. Report expected loss under named profiles and treat
   ranking stability across them as the finding.
5. **Train.** QLoRA 4-bit SFT on rejection-sampled passing rollouts, then
   GRPO/RLVR against the oracle. Filter the RL mix to the 10-80% solve band.
6. **Judges** are not used. There is no residual prose to grade.

The domain bet, stated once: identity resolution is normally judged, and the one
population where it is *attested* is the one where a law compels the person to
state the fact themselves.

See `METHOD.md` for the reasoning, `ARCHITECTURE.md` for the seams.
