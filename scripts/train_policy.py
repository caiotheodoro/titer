#!/usr/bin/env python3
"""Train a value-of-information policy on the R4 simulator. No API spend.

Order is the one `post-training-pipeline` fixes and W5/W6 make binding:

  health gate -> SFT warm start -> filter to the 10-80% solve band -> GRPO
  -> select on hill-climb, never on frozen test -> >=4 seeds -> seed verdict

Rollouts are free: the simulator is fitted to real cached observations, so no
provider is called. That is what makes >=4 seeds affordable, which is the whole
reason a margin here can carry its spread.

After D037 this is a different problem than it looks. Both active floors are
beaten by `abstain_always`: at a 37% solve rate under gtm_outbound, answering is
negative expected value. The task is not "verify more cheaply", it is "answer
only when likely right, and say how sure you are".
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from titer.costs.profiles import REPORTABLE
from titer.env.policies import abstain_always, always_deep_verify, never_verify
from titer.env.titer_env import TiterEnv
from titer.sim.fit import SimulatedProvider
from titer.sim.real import build
from titer.train.policy import LinearPolicy, features
from titer.train.seeds import format_report, verdict

PROFILE = "gtm_outbound"
BUDGET = 1.0


def bucket(task_id: str, n: int = 10) -> int:
    """Deterministic signature bucket. Splits are signature-disjoint."""
    return int(task_id[:8], 16) % n


def split_tasks(tasks):
    """train / hill-climb / frozen test, disjoint by task signature."""
    tr, hc, te = [], [], []
    for t in tasks:
        b = bucket(t.task_id)
        (tr if b < 6 else hc if b < 8 else te).append(t)
    return tr, hc, te


def make_env(tasks, parts, ref, price, seed):
    prov = SimulatedProvider("exa", "search", parts.model, ref, price, seed=seed)
    return TiterEnv(tasks, {"exa": prov}, parts.index, parts.issuer_index,
                    budget_usd=BUDGET, profile_name=PROFILE)


def describe(env, policy, tasks, ref):
    """What the policy actually DOES. A mean reward hides the mechanism.

    Reported because the first inspection found the interesting half: it
    learned selectivity and did not learn calibration.
    """
    import collections

    from titer.train.policy import ACTIONS
    acts, confs, outs = collections.Counter(), collections.Counter(), collections.Counter()
    for i, tk in enumerate(tasks):
        ref["task"] = tk
        ref["decoy_employer"] = tk.anchor_issuer_name
        env.reset(i)
        obs = env.state()
        for _ in range(env.turn_cap + 2):
            a = policy.greedy(features(obs, env.turn_cap, BUDGET))
            kind, c = ACTIONS[a]
            acts[kind] += 1
            if kind == "answer":
                confs[c] += 1
            r = env.step(policy.to_action(a, obs))
            obs = r.observation
            if r.done:
                break
        if env.record is not None:
            outs[env.record.outcome.value] += 1
    n = max(sum(outs.values()), 1)
    answered = n - outs.get("ABSTAIN", 0)
    return {
        "action_counts": dict(acts),
        "stated_confidence": {str(k): v for k, v in sorted(confs.items())},
        "outcomes": dict(outs),
        "abstain_rate": round(outs.get("ABSTAIN", 0) / n, 4),
        "precision_when_answering": round(outs.get("CORRECT", 0) / answered, 4)
        if answered else None,
    }


def run_one(env, policy_fn, tasks, ref, sampled=False):
    """One pass over `tasks`. Returns (mean reward, records)."""
    rs, recs = [], []
    for i, tk in enumerate(tasks):
        ref["task"] = tk
        ref["decoy_employer"] = tk.anchor_issuer_name
        env.reset(i)
        obs = env.state()
        for _ in range(env.turn_cap + 2):
            act = policy_fn(env, obs)
            r = env.step(act)
            obs = r.observation
            if r.done:
                break
        if env.record is not None:
            rs.append(env.record.reward)
            recs.append(env.record)
    return (statistics.fmean(rs) if rs else 0.0), recs


def demo_trace(env, policy: LinearPolicy, tk, ref, i):
    """A scripted query-then-answer rollout, recorded in the policy's own
    action indices so it can be cloned.

    The demonstrator is `never_verify`'s shape - one query, then commit to the
    top candidate - but the stated confidence is drawn from the bucket grid
    rather than hardcoded at 0.9, because after D037 confidence is scored and
    0.9 on a 37%-accurate answer is exactly the miscalibration the Brier term
    charges for.
    """
    from titer.train.policy import ACTIONS, CONF_BUCKETS
    ref["task"] = tk
    ref["decoy_employer"] = tk.anchor_issuer_name
    env.reset(i)
    obs = env.state()
    trace = []
    # 1. query
    x = features(obs, env.turn_cap, BUDGET)
    trace.append((x, 0))
    r = env.step(policy.to_action(0, obs))
    obs = r.observation
    if r.done:
        return trace, (env.record.reward if env.record else 0.0)
    # 2. answer, at the bucket nearest the top candidate's own confidence
    cands = obs.candidates or []
    top_conf = float(cands[0].get("confidence") or 0.0) if cands else 0.0
    b = min(CONF_BUCKETS, key=lambda c: abs(c - top_conf))
    a = ACTIONS.index(("answer", b))
    x = features(obs, env.turn_cap, BUDGET)
    trace.append((x, a))
    r = env.step(policy.to_action(a, obs))
    return trace, (env.record.reward if env.record else 0.0)


def episode_trace(env, policy: LinearPolicy, tk, ref, i):
    """Sampled rollout, keeping (features, action) for the gradient."""
    ref["task"] = tk
    ref["decoy_employer"] = tk.anchor_issuer_name
    env.reset(i)
    obs = env.state()
    trace = []
    for _ in range(env.turn_cap + 2):
        x = features(obs, env.turn_cap, BUDGET)
        a = policy.sample(x)
        trace.append((x, a))
        r = env.step(policy.to_action(a, obs))
        obs = r.observation
        if r.done:
            break
    return trace, (env.record.reward if env.record else 0.0)


def train_seed(parts, ref, price, seed, args):
    """SFT warm start, band filter, then GRPO. Returns (policy, history)."""
    rng_pol = LinearPolicy(turn_cap=32, budget_usd=BUDGET)
    rng_pol.rng.seed(seed)
    train, hill, test = split_tasks(parts.tasks)
    train = train[:args.train_tasks]

    # --- 1. SFT warm start on rejection-sampled PASSING trajectories from a
    # competent behaviour policy. Cloning a uniformly-initialised policy is
    # the cold-start trap: correct trajectories are too rare to find, every
    # GRPO group returns the identical reward, the advantage is zero, and the
    # run collapses onto whichever floor is safest. SFT makes RL possible; it
    # is not an optional warm-up.
    env = make_env(train, parts, ref, price, seed)
    demos = []
    for i, tk in enumerate(train):
        for _ in range(args.sft_k):
            trace, r = demo_trace(env, rng_pol, tk, ref, i)
            if env.record is not None and env.record.outcome.value == "CORRECT":
                demos.append(trace)
                break
    for trace in demos:
        for x, a in trace:
            rng_pol.clone_step(x, a, args.lr_sft)

    # --- 2. Keep only tasks in the 10-80% solve band at this checkpoint.
    # Always-fail and always-pass groups contribute noise, not advantage.
    keep = []
    for i, tk in enumerate(train):
        wins = 0
        for _ in range(args.band_k):
            _, r = episode_trace(env, rng_pol, tk, ref, i)
            wins += 1 if (env.record and env.record.outcome.value == "CORRECT") else 0
        p = wins / args.band_k
        if 0.10 <= p <= 0.80:
            keep.append((i, tk))
    if not keep:
        keep = list(enumerate(train))

    # --- 3. GRPO: group-relative advantage over k rollouts per task.
    hill_env = make_env(hill, parts, ref, price, seed)
    best_w, best_hc, history = rng_pol.snapshot(), -1e9, []
    for epoch in range(args.epochs):
        for i, tk in keep:
            traces, rewards = [], []
            for _ in range(args.k):
                tr, r = episode_trace(env, rng_pol, tk, ref, i)
                traces.append(tr)
                rewards.append(r)
            mu = statistics.fmean(rewards)
            sd = statistics.pstdev(rewards) or 1.0
            for tr, r in zip(traces, rewards):
                adv = (r - mu) / sd
                if adv == 0.0:
                    continue
                for x, a in tr:
                    rng_pol.grad_step(x, a, adv, args.lr)
        hc, _ = run_one(hill_env, rng_pol.act, hill, ref)
        history.append(round(hc, 4))
        # Checkpoint selection is on hill-climb, never on the frozen test split.
        if hc > best_hc:
            best_hc, best_w = hc, rng_pol.snapshot()
    rng_pol.restore(best_w)
    return rng_pol, history, (train, hill, test)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=6)
    ap.add_argument("--epochs", type=int, default=6)
    ap.add_argument("--k", type=int, default=8, help="GRPO group size")
    ap.add_argument("--sft-k", type=int, default=6)
    ap.add_argument("--band-k", type=int, default=8)
    ap.add_argument("--train-tasks", type=int, default=180)
    ap.add_argument("--lr", type=float, default=0.05)
    ap.add_argument("--lr-sft", type=float, default=0.02)
    ap.add_argument("--out", default="train_policy.json")
    args = ap.parse_args()

    parts = build(ROOT)
    price = parts.model.fallback.mean_spend_usd
    ref: dict = {}
    print(f"fitted on {len(parts.observations)} real observations; "
          f"{len(parts.tasks)} tasks", flush=True)

    _, hill, test = split_tasks(parts.tasks)
    print(f"splits: hill-climb {len(hill)}, frozen test {len(test)}", flush=True)

    # --- floors, on the identical footing: same tasks, same seed, same profile
    floors: dict[str, float] = {}
    for name, pol in (("never_verify", never_verify(("exa", "search"))),
                      ("always_deep_verify",
                       always_deep_verify([("exa", "search")] * 3)),
                      ("abstain_always", abstain_always)):
        env = make_env(test, parts, ref, price, 11)
        m, _ = run_one(env, pol, test, ref)
        floors[name] = round(m, 4)
    baseline_name = max(floors, key=floors.get)
    baseline = floors[baseline_name]
    print(f"floors on frozen test: {floors}")
    print(f"baseline to beat: {baseline_name} at {baseline}", flush=True)

    scores, histories = [], []
    for s in range(11, 11 + args.seeds):
        pol, hist, (_tr, _hc, te) = train_seed(parts, ref, price, s, args)
        env = make_env(te, parts, ref, price, 11)
        m, _recs = run_one(env, pol.act, te, ref)
        scores.append(round(m, 4))
        histories.append(hist)
        print(f"  seed {s}: frozen-test {m:.4f}   hill-climb {hist}", flush=True)

    # What it does, and the full cost-profile surface. One number hides both.
    env = make_env(test, parts, ref, price, 11)
    behaviour = describe(env, pol, test, ref)
    by_profile = {}
    for prof in REPORTABLE:
        penv = SimulatedProvider("exa", "search", parts.model, ref, price, seed=11)
        e = TiterEnv(test, {"exa": penv}, parts.index, parts.issuer_index,
                     budget_usd=BUDGET, profile_name=prof)
        pm, _ = run_one(e, pol.act, test, ref)
        fenv = TiterEnv(test, {"exa": SimulatedProvider(
            "exa", "search", parts.model, ref, price, seed=11)},
            parts.index, parts.issuer_index, budget_usd=BUDGET,
            profile_name=prof)
        fm, _ = run_one(fenv, abstain_always, test, ref)
        by_profile[prof] = {"trained": round(pm, 4), "abstain_always": round(fm, 4)}

    v = verdict("trained_policy", scores, baseline)
    print("\n" + format_report([v]))

    # The full profile, never one number.
    report = {
        "generated": __import__("datetime").date.today().isoformat(),
        "fitted_observations": len(parts.observations),
        "splits": {"hill_climb": len(hill), "frozen_test": len(test)},
        "profile": PROFILE, "budget_usd": BUDGET,
        "floors_on_frozen_test": floors,
        "baseline": {"name": baseline_name, "value": baseline},
        "seeds": list(range(11, 11 + args.seeds)),
        "frozen_test_scores": scores,
        "behaviour_last_seed": behaviour,
        "by_cost_profile": by_profile,
        "hill_climb_histories": histories,
        "seed_verdict": {
            "arm": v.arm, "seeds": v.seeds, "mean": round(v.mean, 4),
            "sd": round(v.sd, 4), "baseline": round(v.baseline, 4),
            "margin": round(v.margin, 4), "ratio": round(v.ratio, 4),
            "claimable": v.claimable, "reason": v.reason},
        "note": ("Rollouts are free against a simulator fitted to real cached "
                 "observations, which is what makes >=4 seeds affordable. If "
                 "claimable is false, that is the published result."),
    }
    (ROOT / "results" / args.out).write_text(json.dumps(report, indent=2) + "\n")
    print(f"\nwrote results/{args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
