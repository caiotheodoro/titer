"""Cost profiles. Severity is a property of the error; cost is a property of
the caller.

A single hand-picked false-merge penalty is unfalsifiable, so expected loss is
reported under four named profiles and **ranking stability across them is the
result** - a ranking that flips is more interesting than a win.

`FLAT` is exported separately, through a different symbol, so it cannot be
accidentally published as a result. It is an integrity probe: under it the
expected-loss ranking must equal the accuracy ranking, and if it does not the
harness has a bug. See CONTRACTS.md section 5.
"""
from __future__ import annotations

from typing import Mapping

from titer.oracle.outcome import Outcome

Profile = Mapping[Outcome, float]


def _p(miss, false_merge, unsure_wrong, abstain, stale) -> Profile:
    return {
        Outcome.CORRECT: 0.0,
        Outcome.MISS: miss,
        Outcome.FALSE_MERGE: false_merge,
        Outcome.UNSURE_WRONG: unsure_wrong,
        Outcome.ABSTAIN: abstain,
        Outcome.STALE: stale,
    }


#                      miss  fmerge  unsure  abstain  stale
RECRUITER     = _p(1.0,   2.0,    1.0,    0.5,    1.0)
GTM_OUTBOUND  = _p(1.0,   5.0,    2.0,    0.5,    2.0)
KYC_SANCTIONS = _p(3.0,  50.0,   10.0,    1.0,    5.0)
JOURNALISM    = _p(1.0, 100.0,   20.0,    0.5,    3.0)

#: The four reportable profiles. `PRIMARY` is fixed in the pre-registration.
REPORTABLE: dict[str, Profile] = {
    "recruiter": RECRUITER,
    "gtm_outbound": GTM_OUTBOUND,
    "kyc_sanctions": KYC_SANCTIONS,
    "journalism": JOURNALISM,
}
PRIMARY = "gtm_outbound"

#: NOT a result. A test. Never add this to REPORTABLE.
FLAT: Profile = _p(1.0, 1.0, 1.0, 1.0, 1.0)


def expected_loss(outcomes, profile: Profile) -> float | None:
    """None for an empty arm, never 0.0.

    Returning 0.0 made an arm with no outcomes rank BEST on loss while ranking
    worst on accuracy - the single case where the flat integrity probe fires,
    and it fired on a bug of ours rather than on anything about a provider."""
    outcomes = list(outcomes)
    if not outcomes:
        return None
    return sum(profile[o] for o in outcomes) / len(outcomes)


def accuracy(outcomes) -> float | None:
    outcomes = list(outcomes)
    if not outcomes:
        return None
    return sum(1 for o in outcomes if o is Outcome.CORRECT) / len(outcomes)


def flat_probe_has_power(arms: dict[str, list]) -> bool:
    """Does the harness distinguish profiles at all?

    Under FLAT, expected_loss == 1 - accuracy identically, so "the flat ranking
    equals the accuracy ranking" is an algebraic tautology and cannot fail. It
    is therefore NOT evidence that the harness works, and must not be reported
    as if it were. This is the falsifiable companion: a NON-flat profile must be
    able to produce a different ranking, or the cost lookup is not wired in.
    """
    by_flat = sorted(arms, key=lambda k: (expected_loss(arms[k], FLAT), k))
    for prof in REPORTABLE.values():
        if sorted(arms, key=lambda k: (expected_loss(arms[k], prof), k)) != by_flat:
            return True
    return False
