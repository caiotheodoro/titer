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
from collections import Counter  # noqa: E402
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
                          title_text=t.truth_title_class.value,
                          employment_start=t.truth_period - timedelta(days=1),
                          confidence=0.9, rank=0)
        elif self.rng.random() < 0.5:
            a = RawAnswer(person_name=t.person_name_raw, employer_name=t.anchor_issuer_name,
                          title_text=t.anchor_title_class.value,
                          employment_start=t.anchor_date, confidence=0.85, rank=0)
        else:
            a = RawAnswer(person_name=None, employer_name=None, confidence=0.0, rank=0)
        return [a], Spend(self.price, 1.0, "unit")


def run_real(args) -> int:
    """Fit sim/ from the real replay cache and report the environment's health.

    Published whatever it says. If the solve-rate band is too thin for GRPO,
    that is a finding about the environment, not a reason to quietly not report
    it - and it is exactly the number `environments.md` says gates a training
    run.
    """
    import json as _json
    from datetime import date as _date

    from titer.adapters.cache import CacheKey, ReplayCache
    from titer.corpus.collision import CollisionIndex
    from titer.corpus.schema import AttestedTuple as _AT
    from titer.corpus.tasks import Task as _Task
    from titer.oracle.outcome import Answer as _Answer
    from titer.oracle.outcome import judge as _judge
    from titer.oracle.resolve import resolve as _resolve
    from titer.oracle.resolve import resolve_issuer as _resolve_issuer
    from titer.sim.fit import Observation, fit

    tasks_p = ROOT / "data" / "tasks.jsonl"
    rindex_p = ROOT / "data" / "resolve_index.json"
    if not tasks_p.exists() or not rindex_p.exists():
        print("need data/tasks.jsonl and data/resolve_index.json "
              "(scripts/build_tasks.py)", file=sys.stderr)
        return 2

    d = _json.loads(rindex_p.read_text())
    index = CollisionIndex(
        ciks_by_name={k: set(v) for k, v in d["ciks_by_name"].items()},
        issuers_by_cik={k: set(v) for k, v in d["issuers_by_cik"].items()},
        ciks_by_presented={k: set(v) for k, v in d.get("ciks_by_presented", {}).items()})
    issuer_index = {k: set(v) for k, v in d["ciks_by_company"].items()}

    tasks = {}
    for line in tasks_p.open():
        r = _json.loads(line)
        tasks[r["person_cik"]] = r

    cache = ReplayCache(ROOT / "data" / "replay.jsonl")
    obs: list[Observation] = []
    by_key = {e.key: e for e in cache}
    for r in tasks.values():
        t = _Task(
            person_name_raw=r["person_name_raw"], anchor_issuer_cik=r["anchor_issuer_cik"],
            anchor_issuer_name=r["anchor_issuer_name"],
            anchor_title_class=TitleClass(r["anchor_title_class"]),
            anchor_date=_date.fromisoformat(r["anchor_date"]),
            target_date=_date.fromisoformat(r["target_date"]),
            person_cik=r["person_cik"], truth_issuer_cik=r["truth_issuer_cik"],
            truth_issuer_name=r["truth_issuer_name"],
            truth_title_class=TitleClass(r["truth_title_class"]),
            truth_period=_date.fromisoformat(r["truth_period"]),
            truth_filed=_date.fromisoformat(r["truth_filed"]),
            truth_accession=r["truth_accession"],
            collision_degree=r["collision_degree"])
        key = CacheKey("exa", "answer", f"{t.task_id}|{t.prompt() + ' Give your confidence as a number between 0 and 1.'}", "2026-09")
        e = by_key.get(key.digest())
        if e is None:
            continue
        got = ReplayCache.to_answers(e)
        top = got[0] if got else None
        emp = _resolve_issuer(top.employer_name if top else None, issuer_index)
        res = _resolve(top.person_name if top else None, emp, index,
                       anchor_issuer_cik=t.anchor_issuer_cik)
        ans = _Answer(person_cik=res.person_cik,
                      confidence=top.confidence if top else 0.0, employer_cik=emp)
        truth = _AT(accession=t.truth_accession, person_cik=t.person_cik,
                    person_name_raw=t.person_name_raw, issuer_cik=t.truth_issuer_cik,
                    issuer_name_raw=t.truth_issuer_name, issuer_ticker="",
                    role_class=frozenset({RoleClass.OFFICER}), title_raw="",
                    title_class=t.truth_title_class, period=t.truth_period,
                    filed=t.truth_filed)
        obs.append(Observation("exa", "answer", t.collision_band,
                               _judge(ans, truth), ans.confidence, e.spend_usd))

    if not obs:
        print("no cached observations matched the current task set - the prompt "
              "or task construction changed since they were recorded, so the "
              "cache keys no longer line up. Re-run a measurement or rebuild "
              "tasks to match.", file=sys.stderr)
        return 2

    model = fit(obs, split="train")
    hist = Counter(o.outcome.value for o in obs)
    report = {
        "mode": "real", "source": "data/replay.jsonl",
        "observations": len(obs),
        "outcome_distribution": dict(hist),
        "fitted_cells": model.coverage(),
        "fallback_cell": None if model.fallback is None else {
            "n": model.fallback.n,
            "p_correct": round(model.fallback.p_correct, 4),
            "p_stale": round(model.fallback.p_stale, 4),
            "p_wrong_person": round(model.fallback.p_wrong_person, 4),
            "p_miss": round(model.fallback.p_miss, 4),
        },
    }
    p_correct = model.fallback.p_correct if model.fallback else 0.0
    report["solve_rate_proxy"] = round(p_correct, 4)
    report["in_10_80_band"] = 0.10 <= p_correct <= 0.80
    report["verdict"] = (
        "TRAINABLE: the fitted solve rate sits in the 10-80% band, so GRPO has "
        "advantages to compute." if report["in_10_80_band"] else
        "NOT TRAINABLE AS FITTED: the solve rate is outside the 10-80% band, so "
        "most groups would be all-win or all-lose and GRPO has nothing to "
        "normalise against. Published as a property of the environment.")
    # --- the floors, against the simulator fitted to real data ---
    import random as _random
    import statistics as _stats

    from titer.env.policies import abstain_always, always_deep_verify, never_verify
    from titer.env.policies import run_episode as _run
    from titer.env.titer_env import TiterEnv
    from titer.sim.fit import SimulatedProvider

    task_objs = []
    for r in list(tasks.values())[:300]:
        task_objs.append(_Task(
            person_name_raw=r["person_name_raw"], anchor_issuer_cik=r["anchor_issuer_cik"],
            anchor_issuer_name=r["anchor_issuer_name"],
            anchor_title_class=TitleClass(r["anchor_title_class"]),
            anchor_date=_date.fromisoformat(r["anchor_date"]),
            target_date=_date.fromisoformat(r["target_date"]),
            person_cik=r["person_cik"], truth_issuer_cik=r["truth_issuer_cik"],
            truth_issuer_name=r["truth_issuer_name"],
            truth_title_class=TitleClass(r["truth_title_class"]),
            truth_period=_date.fromisoformat(r["truth_period"]),
            truth_filed=_date.fromisoformat(r["truth_filed"]),
            truth_accession=r["truth_accession"],
            collision_degree=r["collision_degree"]))

    ref: dict = {}
    price = model.fallback.mean_spend_usd or 0.005
    floors = {}
    for name, policy in (("never_verify", never_verify(("exa", "search"))),
                         ("always_deep_verify", always_deep_verify([("exa", "search")] * 3)),
                         ("abstain_always", abstain_always)):
        prov = SimulatedProvider("exa", "search", model, ref, price, seed=args.seed)
        env = TiterEnv(task_objs, {"exa": prov}, index, issuer_index,
                       budget_usd=1.0, profile_name="gtm_outbound")
        rewards, spends, outs = [], [], Counter()
        for i, tk in enumerate(task_objs):
            ref["task"] = tk
            ref["decoy_employer"] = tk.anchor_issuer_name
            rec = _run(env, policy, index=i)
            rewards.append(rec.reward); spends.append(rec.spend_usd)
            outs[rec.outcome.value] += 1
        floors[name] = {"n": len(rewards),
                        "mean_reward": round(_stats.fmean(rewards), 4),
                        "mean_spend_usd": round(_stats.fmean(spends), 5),
                        "outcomes": dict(outs)}
    report["floors"] = floors
    best = max(floors, key=lambda k: floors[k]["mean_reward"])
    report["best_floor"] = best
    report["floor_note"] = (
        f"{best} has the highest mean reward on the simulator fitted to real "
        "data. A trained policy has to beat it, and this is the number it must "
        "beat - not a synthetic one.")

    # --- gates. This used to `return 0` unconditionally: it was a reporter
    # wearing a gate's name, and W5 says "no health report, no training run".
    # A reporter cannot refuse anything. See D037 C5.
    rfails: list[str] = []
    if not report["in_10_80_band"]:
        rfails.append(f"fitted solve rate {p_correct:.4f} is outside the "
                      f"10-80% band; GRPO has no advantages to compute")
    if report["observations"] < 100:
        rfails.append(f"only {report['observations']} real observations; "
                      f"the fitted cells are not worth training against")

    # Reward-hack probes against the REAL fitted environment. Both of these
    # paid before D037, and neither was probed anywhere.
    probe_task = task_objs[0]
    hp: dict = {}

    prov = SimulatedProvider("exa", "search", model, ref, price, seed=args.seed)
    penv = TiterEnv(task_objs, {"exa": prov}, index, issuer_index,
                    budget_usd=1.0, profile_name="gtm_outbound")
    ref["task"] = probe_task
    ref["decoy_employer"] = probe_task.anchor_issuer_name
    penv.reset(0)
    penv.step({"type": "query", "provider": "exa", "action": "search"})
    r = penv.step({"type": "answer", "person_name": "nobody at all",
                   "employer_name": None, "confidence": 0.0,
                   "employment_start": _date(1, 1, 1), "employment_end": None})
    hp["sentinel_date_earns_window_atom"] = bool(penv.record.atoms.window)
    if hp["sentinel_date_earns_window_atom"]:
        rfails.append("a policy-asserted sentinel date still earns the window "
                      "atom; that is ~+0.33 reward per episode for nothing")

    # A proper scoring rule cannot make hedging bad on a KNOWN-wrong answer -
    # that is the rule working. The property that matters is that TRUTHFUL
    # confidence is optimal: swept over constant-confidence policies, the
    # argmax must sit at the empirical accuracy, not at 0 and not at 1. Before
    # D037 the reward was flat in confidence for every correct answer and
    # strictly decreasing in it for every wrong one, so the argmax was pinned
    # at 0 and "state nothing, ever" was optimal.
    def _mean_reward_at(conf, n=120):
        e = TiterEnv(task_objs, {"exa": SimulatedProvider(
            "exa", "search", model, ref, price, seed=args.seed)},
            index, issuer_index, budget_usd=1.0, profile_name="gtm_outbound")
        tot = []
        for i, tk in enumerate(task_objs[:n]):
            ref["task"] = tk
            ref["decoy_employer"] = tk.anchor_issuer_name
            e.reset(i)
            e.step({"type": "query", "provider": "exa", "action": "search"})
            c = e.state().candidates
            top = c[0] if c else {}
            res = e.step({"type": "answer", "person_name": top.get("name"),
                          "employer_name": top.get("employer"),
                          "title_text": top.get("title"), "confidence": conf})
            tot.append(res.reward)
        return _stats.fmean(tot)

    grid = [round(x / 10, 2) for x in range(11)]
    curve = {c: round(_mean_reward_at(c), 4) for c in grid}
    best_conf = max(curve, key=curve.get)
    hp["confidence_reward_curve"] = curve
    hp["argmax_confidence"] = best_conf
    hp["empirical_accuracy"] = round(p_correct, 4)
    # The argmax must track accuracy rather than sit pinned at an endpoint.
    hp["confidence_is_a_free_knob"] = best_conf in (0.0, 1.0)
    if hp["confidence_is_a_free_knob"]:
        rfails.append(
            f"the reward-maximizing constant confidence is {best_conf}, an "
            f"endpoint: confidence is a free knob and every calibration claim "
            f"downstream is void")
    report["hack_probes"] = hp
    report["pass"] = not rfails
    report["failures"] = rfails

    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "results" / "env_health_real.json").write_text(
        _json.dumps(report, indent=2) + "\n")
    print(_json.dumps(report, indent=2))
    if rfails:
        print("\nENV HEALTH (real) FAILED - do not start a training run",
              file=sys.stderr)
        for f in rfails:
            print("  " + f, file=sys.stderr)
        return 1
    print("\nenv_health --real: gates pass")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--k", type=int, default=16, help="rollouts per task")
    ap.add_argument("--tasks", type=int, default=60)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--real", action="store_true",
                    help="fit the simulator from the REAL replay cache instead "
                         "of the synthetic stand-in. The synthetic world exists "
                         "to exercise the gates; it cannot tell you whether the "
                         "environment is trainable on the data you actually have.")
    args = ap.parse_args()

    if args.real:
        return run_real(args)

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
    # Gold must be REACHED, not asserted. D037 moved the employment dates from
    # the policy's action dict to the provider's returned candidate, because
    # read from the action dict they were a free atom on every episode. So a
    # gold probe that steps `answer` without ever querying now has no dates and
    # cannot earn the window atom: it scored 0.5000 and failed its own gate.
    # The probe therefore queries a provider that returns the gold row, then
    # commits to it. That is a stricter test than before - it exercises the
    # query path, the resolver and the scorer, not just the scorer.
    class _GoldProvider:
        def __init__(self, ref):
            self._ref = ref

        def actions(self):
            return [Call("sim", "search", 0.0)]

        def query(self, action, prompt, **kw):
            t = self._ref["task"]
            return [RawAnswer(person_name=t.person_name_raw,
                              employer_name=t.truth_issuer_name,
                              title_text=t.truth_title_class.value,
                              employment_start=t.truth_period - timedelta(days=1),
                              employment_end=None,
                              confidence=1.0, rank=0)], Spend(0.0, 1.0, "usd")

    gold_env = TiterEnv(tasks, {"sim": _GoldProvider(ref)}, idx, iidx,
                        budget_usd=1.0)
    gold_rewards, noop_rewards = [], []
    for i, t in enumerate(tasks):
        ref["task"] = t
        gold_env.reset(i)
        gold_env.step({"type": "query", "provider": "sim", "action": "search"})
        r = gold_env.step({"type": "answer", "person_name": t.person_name_raw,
                           "employer_name": t.truth_issuer_name,
                           "title_text": t.truth_title_class.value,
                           # Gold is right by construction, so it states 1.0.
                           # Anything less is under-confidence and the D037
                           # Brier term prices it, which would fail the gate
                           # below for a calibration reason rather than a
                           # verifier-health one.
                           "confidence": 1.0})
        gold_rewards.append(r.reward)
        env.reset(i)
        r = env.step({"type": "answer", "person_name": None, "employer_name": None,
                      "confidence": 0.0})
        noop_rewards.append(r.reward)
    if min(gold_rewards) < 0.999:
        fails.append(f"gold reward min {min(gold_rewards):.4f} != 1.0")
    # A no-op is now PRICED, not free: it is a MISS and costs profile[MISS].
    # The gate is that it must be strictly worse than gold, not that it is zero.
    if max(noop_rewards) >= min(gold_rewards):
        fails.append(f"no-op reward {max(noop_rewards):.4f} is not worse than gold "
                     f"{min(gold_rewards):.4f}")

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
