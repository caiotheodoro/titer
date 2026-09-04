#!/usr/bin/env python3
"""H2 - false merges under name collision, resolved from the E2 draw.

H2 asks whether `FALSE_MERGE` is (a) non-zero, (b) increasing in name-collision
degree `d`, and (c) large enough to dominate expected loss under the
`kyc_sanctions` and `journalism` profiles.

**It was recorded for months as "strata empty by construction."** That was true
of the W3 draw: simple random sampling put 251 of 299 observations into a single
collision band (D027), so three of four bands held almost nothing and no
gradient in `d` could exist. The fix was never more budget - it was to stop
sampling randomly.

E2 drew n=80 in EVERY band by construction. That is the design H2 always
needed, and the observations are already paid for, so H2 resolves for **$0**
from data collected for another hypothesis.

Falsified if `FALSE_MERGE` net of the contamination bound is indistinguishable
from zero at the achieved n, **or** is flat in `d`. Either outcome is published
as prominently as a positive one.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from titer.costs.profiles import REPORTABLE, expected_loss
from titer.metrics.intervals import wilson
from titer.oracle.outcome import Outcome

BANDS = ["unique", "low", "medium", "high"]
#: Share of colliding names that may be one human under two registrations
#: (CONTRACTS 4.2, measured in results/corpus_stats.json). A FALSE_MERGE on a
#: colliding name can be this artefact rather than a provider error, so the
#: NET rate subtracts it as an upper bound. `unique` names are not affected.
def contamination() -> float:
    d = json.loads((ROOT / "results" / "corpus_stats.json").read_text())
    return float(d["contamination_bound"]["suspect_name_rate"])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--arm", default="exa_D_full_context",
                    help="the instrument held constant across bands")
    ap.add_argument("--out", default="h2_false_merge.json")
    args = ap.parse_args()

    bound = contamination()
    rows, report = [], {
        "generated": __import__("datetime").date.today().isoformat(),
        "arm": args.arm,
        "spend_usd": 0.0,
        "source": "the E2 stratified draw; no new calls",
        "contamination_bound": round(bound, 4),
        "why_this_resolves_it": (
            "H2 was blocked because a random draw left three of four collision "
            "bands nearly empty (D027). E2 drew n=80 in every band by "
            "construction, which is the design H2 always needed."),
        "bands": {},
    }
    for b in BANDS:
        p = ROOT / "results" / f"e2_exa_{b}.json"
        if not p.exists():
            report["bands"][b] = {"note": "not run"}
            continue
        arm = json.loads(p.read_text())["arms"].get(args.arm)
        if not arm:
            report["bands"][b] = {"note": f"arm {args.arm} absent"}
            continue
        outs = arm["outcomes"]
        n = arm["n"]
        fm = outs.get(Outcome.FALSE_MERGE.value, 0)
        iv = wilson(fm, n)
        # NET: subtract the contamination bound from the upper limit, since a
        # FALSE_MERGE on a colliding name may be one human under two CIKs.
        share = 0.0 if b == "unique" else bound
        net_hi = max(0.0, iv.hi - share)
        net_lo = max(0.0, iv.lo - share)
        rows.append((b, fm, n, iv.lo, iv.hi, net_lo, net_hi))
        losses = {}
        counts = {Outcome(k): v for k, v in outs.items() if v}
        seq = [o for o, c in counts.items() for _ in range(c)]
        for prof in REPORTABLE:
            losses[prof] = round(expected_loss(seq, REPORTABLE[prof]), 4)
        report["bands"][b] = {
            "n": n, "false_merge": fm, "rate": round(fm / n, 4),
            "wilson": str(iv),
            "net_of_contamination": [round(net_lo, 4), round(net_hi, 4)],
            "expected_loss": losses,
        }

    # (a) non-zero?  (b) increasing in d?
    measured = [r for r in rows]
    nonzero = [b for b, fm, *_ in measured if fm > 0]
    rates = [fm / n for _, fm, n, *_ in measured]
    monotone = all(x <= y for x, y in zip(rates, rates[1:])) and len(set(rates)) > 1
    # "net of the contamination bound", per the pre-registration. A FALSE_MERGE
    # on a colliding name may be one human under two registrations, so the net
    # interval subtracts that bound; if it reaches zero the rate is
    # indistinguishable from zero at this n.
    all_ci_touch_zero = all(net_lo <= 0.0 for *_, net_lo, _hi in measured)
    report["verdict"] = {
        "bands_with_any_false_merge": nonzero,
        "rates_in_band_order": [round(r, 4) for r in rates],
        "increasing_in_d": monotone,
        "every_interval_includes_zero": all_ci_touch_zero,
        "falsified": (not monotone) or all_ci_touch_zero,
        "reason": None,
    }
    v = report["verdict"]
    if v["falsified"]:
        why = []
        if all_ci_touch_zero:
            why.append("every band's Wilson interval includes zero, so the rate "
                       "is indistinguishable from zero at the achieved n")
        if not monotone:
            why.append("the rate is not increasing in d")
        v["reason"] = ("H2 is FALSIFIED: " + "; and ".join(why)
                       + ". The pre-registration commits to publishing this as "
                         "prominently as a positive result.")
    (ROOT / "results" / args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
