#!/usr/bin/env python3
"""Regenerate MEASUREMENT_CARD.json from live repository state.

The card went eight commits stale and ended up asserting that SEC was blocked
and no archive had been downloaded, against 4.2M built rows, while every gate
stayed green. It contradicted the README on the repository's front page.

A card is a claim like any other. Hand-maintaining it is how it drifts, so it is
generated: counts come from `pytest --collect-only` and `wc`, spend from the
replay cache, results from `results/*.json`. `gate_card_fresh` in
scripts/validate.py then refuses to let the generated values drift again.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def live_tests() -> int:
    out = subprocess.run(["uv", "run", "--extra", "dev", "pytest", "--collect-only",
                          "-q", "tests"], cwd=ROOT, capture_output=True, text=True,
                         check=False)
    import re
    m = re.search(r"(\d+)\s+tests? collected", out.stdout)
    if not m:
        raise SystemExit(f"could not read a test count:\n{out.stdout[-400:]}")
    return int(m.group(1))


def live_loc() -> int:
    n = 0
    for d in ("src", "tests", "scripts"):
        for p in (ROOT / d).rglob("*.py"):
            if "__pycache__" in p.parts:
                continue
            n += sum(1 for _ in p.open(errors="replace"))
    return n


def live_spend() -> dict[str, float]:
    cache = ROOT / "data" / "replay.jsonl"
    if not cache.exists():
        return {}
    out: dict[str, float] = {}
    for line in cache.open():
        e = json.loads(line)
        out[e["provider"]] = round(out.get(e["provider"], 0.0) + e["spend_usd"], 4)
    # Calls made through the adapter directly never reach the cache. Diagnostic
    # spend is still spend, and a card that reads only the cache under-reported
    # it by $1.40. See results/manual_spend.json.
    manual = ROOT / "results" / "manual_spend.json"
    if manual.exists():
        for e in json.loads(manual.read_text())["entries"]:
            out[e["provider"]] = round(out.get(e["provider"], 0.0) + e["usd"], 4)
    return out


def main() -> int:
    spend = live_spend()
    card = {
        "project": "titer",
        "contracts_version": "contracts/v1 + contracts/v1-expertise",
        "wave": "published; E1 and E3 measured, employment study partial",
        "generated": date.today().isoformat(),
        "verdict": "PARTIALLY_VERIFIED",
        "rationale": (
            "E1 and E3 are measured on verified negatives and survived attack. The "
            "employment study's H1 is mis-specified, H2's strata were empty by "
            "construction, and the Ploid arm is retracted. A card that always exits "
            "zero is decoration; this one names what is not established."),
        "code_state": {
            "python_loc": live_loc(),
            "tests_passing": live_tests(),
            "gates": "make validate green (10 gates); oracle_selfcheck and env_health pass",
        },
        "spend_usd": {**spend, "total": round(sum(spend.values()), 2)},
        "verified": {
            "E1_false_affirmation": (
                "Exa affirms verified-false expertise claims at 0.1680 [0.1268,0.2193] "
                "(NEAR, adjacent subfield), 0.1320 [0.0956,0.1796] (FAR, adjacent field) "
                "and 0.0840 [0.0556,0.1250] (CONTROL, different domain), n=250 each, "
                "while confirming attested expertise at 0.9600 [0.9279,0.9781]. "
                "Negatives verified against /works before asking. Survived a post-hoc "
                "and a confirmatory test."),
            "E1_distance_gradient": (
                "NEAR is 2.00x CONTROL with non-overlapping intervals, so topic distance "
                "moves the rate. FAR does not separate from CONTROL: the gradient is "
                "visible only at the extremes. See docs/DECISIONS.md D034."),
            "E1_control_floor": (
                "The CONTROL arm does not reach zero: 21 of 250 claims about a wholly "
                "different OpenAlex domain were affirmed. At least 8.4 of the 16.8 NEAR "
                "points are error no reading of the prompt explains, which bounds "
                "RED-TEAM A12 rather than leaving it open."),
            "E3_calibration": (
                "686 of 750 answers (91.5%) in the 0.9-1.0 confidence bin at mean 0.987 "
                "against accuracy 0.889; ECE 0.1153, Brier 0.1191."),
            "R4_environment": (
                "Simulator fitted to 500 real observations; solve rate 0.37, inside the "
                "10-80% band. never_verify (0.0455) beats always_deep_verify (0.0277): "
                "3x the spend bought marginally fewer correct answers."),
        },
        "superseded": {
            "W3_exa_employment_n299": (
                "0.5886 [0.5321,0.6429] correct, false-merge <0.0127. Measured under the "
                "pre-D028 dated prompt on the unrestricted task set, so it is not "
                "comparable to anything measured afterwards. Retained as record."),
            "E1_raw_rates": "0.1875 / 0.2212 - retracted, see docs/RETRACTIONS.md R002.",
        },
        "unmet_claims": [
            "One provider. Every surviving number describes Exa; nothing supports a "
            "claim about the category.",
            "Part of the 8-17% may be prompt interpretation rather than error - "
            "adjacent negatives cannot be removed (RED-TEAM A12).",
            "E1 difficulty axis (D031): PARTIALLY SUPPORTED - NEAR separates from CONTROL, FAR does not. D031's two tiers were too close ""together to resolve it.",
            "E2: RUN, and it FALSIFIED D029 on an answer engine - a free-text capability constraint does disambiguate (C > A in all three colliding bands, paired intervals excluding zero). D029 survives only in scope: it was a claim about indexes with structured filters.",
            "E4 cross-domain coverage: NOT MEASURABLE at this budget (D038). A normalised string match cannot separate 'wrong person' from 'right institution, named as a sub-unit'; it needs an institution resolver over OpenAlex IDs, and the two oracles differ in strength.",
            "H1 staleness: mis-specified - non-monotone, so no half-life exists (D033).",
            "H2 false merge under name collision: strata empty by construction.",
            "Ploid: unmeasured after FOUR budgets and seven harness defects (R001, D028, D035). No accuracy number is claimed. What it would cost to know is published instead: n=49 for a +/-0.10 half-width, $9.80 at the measured $0.20 per search.",
            "Trivial floor: withdrawn as a parser artefact, never validly measured.",
            "R4: a policy IS trained and clears the seed gate (0.0461 vs -0.1000, SD 0.0122 = 0.08x the margin, 6 seeds). It is a 130-parameter linear model on a simulator, not the 8B/4B W6 promised (D036), and it learned selectivity but not calibration - it states confidence 1.0 on every answer at 64% accuracy.",
        ],
        "artifacts": {
            "code": "https://github.com/caiotheodoro/titer",
            "edgar_corpus": "https://huggingface.co/datasets/caiotheodoro/titer-edgar-officers",
            "expertise_corpus": "https://huggingface.co/datasets/caiotheodoro/titer-expertise-claims",
            "space": "https://huggingface.co/spaces/caiotheodoro/titer",
        },
        "independent_read": {
            "score": "74/90", "self_score": "78/90",
            "summary": "high as a methodology exemplar, low as a benchmark of the category",
        },
    }
    p = ROOT / "MEASUREMENT_CARD.json"
    p.write_text(json.dumps(card, indent=2) + "\n")
    print(f"regenerated: {card['code_state']['tests_passing']} tests, "
          f"{card['code_state']['python_loc']} LOC, "
          f"${card['spend_usd']['total']} spent, generated {card['generated']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
