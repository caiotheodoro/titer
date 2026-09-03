#!/usr/bin/env python3
"""Environment health gate. No report, no training run.

A run that 'completes' on a broken environment produces a policy that hacks the
broken environment, and every number downstream measures the harness. This
emits the one-page report and exits nonzero if any gate fails.

At W5 the provider is a stochastic stand-in fitted to the replay cache, because
live rollouts at $5 a verification are impossible. The sim-to-real gap is
measured separately and is R4's stated limitation - not hidden here.
"""
from __future__ import annotations

import argparse
import json
import random
import statistics
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from titer.adapters.base import Call, RawAnswer, Spend  # noqa: E402
from titer.corpus.collision import build_index  # noqa: E402
from titer.corpus.schema import AttestedTuple, RoleClass  # noqa: E402
from titer.corpus.tasks import build_tasks  # noqa: E402
from titer.corpus.title_map import TitleClass  # noqa: E402
from titer.env.policies import abstain_always, never_verify, run_episode  # noqa: E402
from titer.env.titer_env import TiterEnv  # noqa: E402
from titer.oracle.outcome import Outcome  # noqa: E402
from titer.oracle.resolve import build_issuer_index  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IN_BAND = (0.10, 0.80)


def synthetic_world(n_people=120, seed=11):
    """Stand-in corpus with a controlled collision structure, used until the
    real corpus exists. Every gate below is structural and does not depend on
    the corpus being real."""
    rng = random.Random(seed)
    # Enough distinct names that collision degree VARIES. A stand-in where
    # every name collides ~10 ways is pathological, and a pathological stand-in
    # hides defects instead of exposing them.
    surnames = ["SMITH", "PATEL", "GARCIA", "CHEN", "OKAFORE", "MULLER", "NOVAK",
                "HAAS", "ROSSI", "DUBOIS", "KIM", "SILVA", "TANAKA", "OSEI",
                "LARSEN", "MOREAU", "WEBER", "COSTA", "IVANOV", "AHMED"]
    givens = ["JOHN", "MARIA", "ALEX", "PRIYA", "SAM", "LENA", "OMAR", "YUKI"]
    rows = []
    for i in range(n_people):
        # Names are deliberately reused so collision degree varies across tasks.
        name = f"{surnames[i % len(surnames)]} {givens[(i // 7) % len(givens)]}"
        start = date(2015, 1, 1) + timedelta(days=rng.randrange(1500))
        later = start + timedelta(days=400 + rng.randrange(900))
        cik = str(10_000 + i)
        rows.append(AttestedTuple(
            accession=f"a{i}-1", person_cik=cik, person_name_raw=name,
            issuer_cik=str(700 + i % 23), issuer_name_raw=f"ISSUER {i % 23}",
            issuer_ticker="T", role_class=frozenset({RoleClass.OFFICER}),
            title_raw="CEO", title_class=TitleClass.CEO,
            period=start, filed=start + timedelta(days=2)))
        rows.append(AttestedTuple(
            accession=f"a{i}-2", person_cik=cik, person_name_raw=name,
            issuer_cik=str(900 + i), issuer_name_raw=f"NEWCO {i}",
            issuer_ticker="N", role_class=frozenset({RoleClass.OFFICER}),
            title_raw="CFO", title_class=TitleClass.CFO,
            period=later, filed=later + timedelta(days=2)))
    return rows


class StochasticProvider:
    """Stand-in whose accuracy falls with collision degree, so the solve-rate
    histogram has structure to measure rather than being all-0 or all-1."""

    name = "sim"

    def __init__(self, env_ref, p_base=0.65, seed=11, price=0.05):
        self._env = env_ref
        self.p_base = p_base
        self.rng = random.Random(seed)
        self.price = price

    def actions(self):
        return [Call(self.name, "search", self.price)]

    def query(self, action, prompt, **kw):
        t = self._env["task"]
        p = self.p_base / (1 + 0.35 * max(t.collision_degree - 1, 0))
        if self.rng.random() < p:
            a = RawAnswer(person_name=t.person_name_raw, employer_name=t.truth_issuer_name,
                          title_text=t.truth_title_class.value, confidence=0.9, rank=0)
        elif self.rng.random() < 0.5:
            a = RawAnswer(person_name=t.person_name_raw, employer_name=t.anchor_issuer_name,
                          title_text=t.anchor_title_class.value, confidence=0.85, rank=0)
        else:
            a = RawAnswer(person_name=None, employer_name=None, confidence=0.0, rank=0)
        return [a], Spend(self.price, 1.0, "unit")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=16, help="rollouts per task")
    ap.add_argument("--tasks", type=int, default=60)
    ap.add_argument("--seed", type=int, default=11)
    args = ap.parse_args()

    rows = synthetic_world()
    idx = build_index(rows)
    iidx = build_issuer_index(rows)
    tasks, tstats = build_tasks(rows, idx)
    tasks = tasks[: args.tasks]

    ref: dict = {}
    provider = StochasticProvider(ref, seed=args.seed)
    env = TiterEnv(tasks, {"sim": provider}, idx, iidx, budget_usd=1.0)
    fails: list[str] = []

    # --- 1. verifier integrity ------------------------------------------
    gold_rewards, noop_rewards = [], []
    for i, t in enumerate(tasks):
        ref["task"] = t
        env.reset(i)
        r = env.step({"type": "answer", "person_name": t.person_name_raw,
                      "employer_name": t.truth_issuer_name,
                      "title_text": t.truth_title_class.value, "confidence": 0.95})
        gold_rewards.append(r.reward)
        env.reset(i)
        r = env.step({"type": "answer", "person_name": None, "employer_name": None,
                      "confidence": 0.0})
        noop_rewards.append(r.reward)
    if min(gold_rewards) < 0.999:
        fails.append(f"gold reward min {min(gold_rewards):.4f} != 1.0")
    if max(noop_rewards) != 0.0:
        fails.append(f"noop reward max {max(noop_rewards):.4f} != 0.0")

    # --- 2. solve-rate histogram ----------------------------------------
    solve = []
    for i, t in enumerate(tasks):
        ref["task"] = t
        wins = 0
        for _ in range(args.k):
            rec = run_episode(env, never_verify(("sim", "search")), index=i)
            wins += rec.outcome is Outcome.CORRECT
        solve.append(wins / args.k)
    in_band = [p for p in solve if IN_BAND[0] <= p <= IN_BAND[1]]
    pct_in_band = len(in_band) / len(solve)
    zero_adv = sum(1 for p in solve if p in (0.0, 1.0)) / len(solve)
    hist = Counter(min(int(p * 10), 9) for p in solve)

    if pct_in_band < 0.20:
        fails.append(f"only {pct_in_band:.1%} of tasks in the 10-80% band; "
                     "GRPO will have almost nothing to normalise against")

    # --- 3. hack probes --------------------------------------------------
    # The invariant is NOT "abstain_always loses to whatever policy we happen to
    # have". Against a bad enough provider, abstaining genuinely IS better - that
    # is the loss matrix working, and it is a finding about the provider, not a
    # bug. The reward is hackable only if abstaining beats being RIGHT.
    abst = [run_episode(env, abstain_always, index=i).reward for i in range(len(tasks))]
    honest = [run_episode(env, never_verify(("sim", "search")), index=i).reward
              for i in range(len(tasks))]
    if statistics.mean(abst) >= min(gold_rewards):
        fails.append("abstain_always is competitive with a GOLD answer; the "
                     "abstention credit is mis-set and the reward is hackable")
    # Reported, never gated: abstaining beating this particular policy tells you
    # the provider is weak, which is what R2 exists to measure.
    abstain_beats_honest = statistics.mean(abst) > statistics.mean(honest)

    report = {
        "env": "titer/v0", "harness": "TiterEnv+keel", "provider": "StochasticProvider",
        "n_tasks": len(tasks), "k_rollouts": args.k, "seed": args.seed,
        "verifier_gold": min(gold_rewards), "verifier_noop": max(noop_rewards),
        "solve_rate_hist": {f"{b/10:.1f}-{(b+1)/10:.1f}": hist.get(b, 0) for b in range(10)},
        "mean_solve_rate": statistics.mean(solve),
        "pct_in_band_10_80": pct_in_band,
        "pct_groups_zero_adv": zero_adv,
        "sampler_trainer_kl": None,
        "train_vs_eval_protocol_diff": "none at W5: no policy is trained yet",
        "hack_probes": {"abstain_always_mean": statistics.mean(abst),
                        "honest_mean": statistics.mean(honest),
                        "gold_min": min(gold_rewards),
                        "abstain_beats_this_policy": abstain_beats_honest,
                        "note": ("abstain_beats_this_policy is a diagnostic about "
                                 "the provider, not a gate; only abstain >= gold "
                                 "fails the build"),
                        "shaping_terms_present": False},
        "task_population": {"people_total": tstats.people_total,
                            "people_with_a_move": tstats.people_with_a_move,
                            "retained_fraction": tstats.retained_fraction},
        "pass": not fails,
        "failures": fails,
    }
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "env_health.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if fails:
        print("\nENV HEALTH FAILED - do not start a training run", file=sys.stderr)
        return 1
    print("\nenv_health: gates pass")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
