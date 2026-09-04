"""A linear-softmax policy over the R4 action space. Stdlib only.

The fitted environment exposes three action types - query, answer(confidence),
abstain - so the trainable action set is small enough that a 130-parameter
linear policy is the right size. The declared `train` extra
(torch/trl/peft/bitsandbytes, sized for an 8B QLoRA) is enormously oversized for
this, and importing it would break the stdlib-only contract the core keeps.

Confidence is discretised into buckets so the whole thing is one softmax. That
matters after D037: confidence is now scored by a proper rule, so the policy has
to *choose* it rather than inherit a hardcoded 0.9.

`collision_band` is deliberately NOT a feature. The simulator conditions on it,
but the real observation does not expose it, and a policy trained on it would be
learning from something a live provider never hands over.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

#: Confidence buckets the policy may state.
CONF_BUCKETS = [round(i / 10, 1) for i in range(11)]
#: query, abstain, then one answer action per bucket.
ACTIONS: list[tuple[str, float | None]] = (
    [("query", None), ("abstain", None)]
    + [("answer", c) for c in CONF_BUCKETS])
N_ACTIONS = len(ACTIONS)

FEATURES = ("bias", "turns_left", "budget_left", "n_cand", "has_cand",
            "top_conf", "conf_gap", "has_employer", "id_verified", "queried")
N_FEATURES = len(FEATURES)


def features(obs, turn_cap: int = 32, budget_usd: float = 1.0) -> list[float]:
    """Bounded features from the observation the env actually emits."""
    cands = obs.candidates or []
    top = cands[0] if cands else {}
    second = cands[1] if len(cands) > 1 else {}
    tc = float(top.get("confidence") or 0.0)
    sc = float(second.get("confidence") or 0.0)
    return [
        1.0,
        obs.turns_left / max(turn_cap, 1),
        obs.budget_remaining_usd / max(budget_usd, 1e-9),
        min(len(cands), 5) / 5.0,
        1.0 if cands else 0.0,
        max(0.0, min(tc, 1.0)),
        max(0.0, min(tc - sc, 1.0)),
        1.0 if top.get("employer") else 0.0,
        1.0 if top.get("identity_verified") else 0.0,
        0.0 if obs.turns_left >= turn_cap else 1.0,
    ]


@dataclass
class LinearPolicy:
    """Softmax over ACTIONS, linear in `features`."""

    w: list[list[float]] = field(
        default_factory=lambda: [[0.0] * N_FEATURES for _ in range(N_ACTIONS)])
    rng: random.Random = field(default_factory=lambda: random.Random(11))
    turn_cap: int = 32
    budget_usd: float = 1.0

    def logits(self, x: list[float]) -> list[float]:
        return [sum(wi * xi for wi, xi in zip(row, x)) for row in self.w]

    def probs(self, x: list[float]) -> list[float]:
        z = self.logits(x)
        m = max(z)
        e = [math.exp(v - m) for v in z]
        s = sum(e) or 1.0
        return [v / s for v in e]

    def sample(self, x: list[float]) -> int:
        p = self.probs(x)
        r = self.rng.random()
        acc = 0.0
        for i, pi in enumerate(p):
            acc += pi
            if r <= acc:
                return i
        return len(p) - 1

    def greedy(self, x: list[float]) -> int:
        p = self.probs(x)
        return max(range(len(p)), key=p.__getitem__)

    def to_action(self, i: int, obs) -> dict:
        kind, conf = ACTIONS[i]
        if kind == "query":
            avail = [a for a in (obs.available or []) if a.get("affordable")]
            if not avail:
                return {"type": "abstain"}
            a = avail[0]
            return {"type": "query", "provider": a["provider"],
                    "action": a["action"]}
        if kind == "abstain":
            return {"type": "abstain"}
        cands = obs.candidates or []
        top = cands[0] if cands else {}
        return {"type": "answer", "person_name": top.get("name"),
                "employer_name": top.get("employer"),
                "title_text": top.get("title"), "confidence": conf}

    # --- learning --------------------------------------------------------
    def grad_step(self, x: list[float], a: int, advantage: float, lr: float):
        """REINFORCE: d/dw log pi(a|x) * advantage, one sample."""
        p = self.probs(x)
        for j in range(N_ACTIONS):
            g = ((1.0 if j == a else 0.0) - p[j]) * advantage
            if g:
                row = self.w[j]
                for f in range(N_FEATURES):
                    row[f] += lr * g * x[f]

    def clone_step(self, x: list[float], a: int, lr: float):
        """Behaviour cloning: push probability toward a demonstrated action."""
        self.grad_step(x, a, 1.0, lr)

    def act(self, env, obs) -> dict:
        return self.to_action(self.greedy(features(
            obs, self.turn_cap, self.budget_usd)), obs)

    def act_sampled(self, env, obs) -> dict:
        return self.to_action(self.sample(features(
            obs, self.turn_cap, self.budget_usd)), obs)

    def snapshot(self) -> list[list[float]]:
        return [row[:] for row in self.w]

    def restore(self, w: list[list[float]]) -> None:
        self.w = [row[:] for row in w]
