#!/usr/bin/env python3
"""Verifier integrity. Gold scores 1.0, a no-op scores 0.0, inverted collapses.

If gold is not exactly 1.0 you are training against noise, and every number
downstream is measuring the harness rather than the subject. This exits nonzero
on any failure, and a nonzero exit is the product.
"""
from __future__ import annotations

import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.corpus.schema import AttestedTuple, RoleClass  # noqa: E402
from titer.corpus.title_map import TitleClass  # noqa: E402
from titer.costs.profiles import (FLAT, accuracy, expected_loss,  # noqa: E402
                                  flat_probe_has_power)
from titer.oracle.outcome import Answer, Outcome, atoms, judge  # noqa: E402


def population(n=200):
    titles = [t for t in TitleClass if t is not TitleClass.UNKNOWN]
    return [
        AttestedTuple(
            accession=f"acc-{i}", person_cik=str(1000 + i),
            person_name_raw=f"PERSON{i} TEST", issuer_cik=str(9000 + i % 11),
            issuer_name_raw=f"ISSUER{i % 11}", issuer_ticker=f"T{i % 11}",
            role_class=frozenset({RoleClass.OFFICER}),
            title_raw="x", title_class=titles[i % len(titles)],
            period=date(2022, 1, 1) + timedelta(days=i),
            filed=date(2022, 1, 3) + timedelta(days=i),
        )
        for i in range(n)
    ]


def main() -> int:
    rows = population()
    fails = []

    gold = [Answer(person_cik=r.person_cik, confidence=1.0, employer_cik=r.issuer_cik,
                   title_class=r.title_class, employment_start=r.period - timedelta(days=1))
            for r in rows]
    g_atoms = [atoms(a, r).total for a, r in zip(gold, rows)]
    g_out = [judge(a, r) for a, r in zip(gold, rows)]
    if min(g_atoms) != 1.0:
        fails.append(f"gold atoms min={min(g_atoms)} != 1.0")
    if set(g_out) != {Outcome.CORRECT}:
        fails.append(f"gold outcomes not all CORRECT: {set(g_out)}")

    noop = [Answer() for _ in rows]
    n_atoms = [atoms(a, r).total for a, r in zip(noop, rows)]
    n_out = [judge(a, r) for a, r in zip(noop, rows)]
    if max(n_atoms) != 0.0:
        fails.append(f"no-op atoms max={max(n_atoms)} != 0.0")
    if set(n_out) != {Outcome.MISS}:
        fails.append(f"no-op outcomes not all MISS: {set(n_out)}")

    # Inverted: answer with someone else's CIK, confidently.
    inv = [Answer(person_cik=rows[(i + 1) % len(rows)].person_cik, confidence=1.0)
           for i in range(len(rows))]
    i_out = [judge(a, r) for a, r in zip(inv, rows)]
    if set(i_out) != {Outcome.FALSE_MERGE}:
        fails.append(f"inverted outcomes not all FALSE_MERGE: {set(i_out)}")
    if accuracy(i_out) != 0.0:
        fails.append("inverted accuracy did not collapse to 0.0")

    # Flat profile. Under FLAT, expected_loss == 1 - accuracy identically, so
    # "the rankings agree" is an ALGEBRAIC IDENTITY and cannot fail. It is
    # reported as an identity, never as evidence the harness works. See D024 C8.
    arms = {"gold": g_out, "noop": n_out, "inverted": i_out,
            "mixed": g_out[:100] + n_out[100:]}
    by_acc = sorted(arms, key=lambda k: (-accuracy(arms[k]), k))
    by_flat = sorted(arms, key=lambda k: (expected_loss(arms[k], FLAT), k))
    if by_acc != by_flat:
        fails.append(f"flat identity violated (a real harness bug): {by_acc} vs {by_flat}")

    # The falsifiable companion: a NON-flat profile must be able to reorder the
    # arms, or the cost lookup is not wired into the scoring path at all.
    if not flat_probe_has_power(arms):
        fails.append("no reportable cost profile can reorder these arms; the cost "
                     "lookup is not reaching the scoring path")

    print(f"gold atoms       min={min(g_atoms):.3f}  outcomes={set(o.value for o in g_out)}")
    print(f"no-op atoms      max={max(n_atoms):.3f}  outcomes={set(o.value for o in n_out)}")
    print(f"inverted         accuracy={accuracy(i_out):.3f} outcomes={set(o.value for o in i_out)}")
    print(f"flat identity    accuracy order == flat-loss order: {by_acc == by_flat} "
          f"(an identity, not evidence)")
    print(f"probe power      a non-flat profile CAN reorder arms: "
          f"{flat_probe_has_power(arms)}")
    if fails:
        print("\nFAILED:", file=sys.stderr)
        for f in fails:
            print("  " + f, file=sys.stderr)
        return 1
    print("\noracle_selfcheck: all integrity probes pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
