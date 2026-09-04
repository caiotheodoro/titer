"""Build the R4 environment from the real replay cache.

Both `scripts/env_health.py --real` and `scripts/train_policy.py` need the same
fitted simulator, the same task objects and the same indices. Two copies of this
would drift, and a training run fitted differently from the health report that
blessed it is exactly the train/eval skew `mlops-pipeline-design` warns about.

Stdlib only, like the rest of `titer` core.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from titer.adapters.cache import CacheKey, ReplayCache
from titer.corpus.collision import CollisionIndex
from titer.corpus.schema import AttestedTuple, RoleClass
from titer.corpus.tasks import Task
from titer.corpus.title_map import TitleClass
from titer.oracle.outcome import Answer, judge
from titer.oracle.resolve import resolve, resolve_issuer
from titer.sim.fit import FittedModel, Observation, fit

#: The exact rendering the W2 measurement used. The cache key includes it, so a
#: character out of place silently matches nothing and the fit sees zero rows.
ANSWER_SUFFIX = " Give your confidence as a number between 0 and 1."
WINDOW = "2026-09"


class NoObservations(RuntimeError):
    """The cache holds nothing matching the current task set."""


@dataclass(frozen=True)
class RealEnvParts:
    model: FittedModel
    observations: list[Observation]
    tasks: list[Task]
    index: CollisionIndex
    issuer_index: dict[str, set[str]]


def _task_from_row(r: dict) -> Task:
    return Task(
        person_name_raw=r["person_name_raw"],
        anchor_issuer_cik=r["anchor_issuer_cik"],
        anchor_issuer_name=r["anchor_issuer_name"],
        anchor_title_class=TitleClass(r["anchor_title_class"]),
        anchor_date=date.fromisoformat(r["anchor_date"]),
        target_date=date.fromisoformat(r["target_date"]),
        person_cik=r["person_cik"],
        truth_issuer_cik=r["truth_issuer_cik"],
        truth_issuer_name=r["truth_issuer_name"],
        truth_title_class=TitleClass(r["truth_title_class"]),
        truth_period=date.fromisoformat(r["truth_period"]),
        truth_filed=date.fromisoformat(r["truth_filed"]),
        truth_accession=r["truth_accession"],
        collision_degree=r["collision_degree"])


def load_indices(root: Path) -> tuple[CollisionIndex, dict[str, set[str]]]:
    d = json.loads((root / "data" / "resolve_index.json").read_text())
    index = CollisionIndex(
        ciks_by_name={k: set(v) for k, v in d["ciks_by_name"].items()},
        issuers_by_cik={k: set(v) for k, v in d["issuers_by_cik"].items()},
        ciks_by_presented={k: set(v)
                           for k, v in d.get("ciks_by_presented", {}).items()})
    return index, {k: set(v) for k, v in d["ciks_by_company"].items()}


def build(root: Path, split: str = "train") -> RealEnvParts:
    """Fit the simulator from cached provider bodies. No network, no spend."""
    index, issuer_index = load_indices(root)
    rows = {}
    for line in (root / "data" / "tasks.jsonl").open():
        r = json.loads(line)
        rows[r["person_cik"]] = r

    cache = ReplayCache(root / "data" / "replay.jsonl")
    by_key = {e.key: e for e in cache}
    obs: list[Observation] = []
    tasks: list[Task] = []
    for r in rows.values():
        t = _task_from_row(r)
        key = CacheKey("exa", "answer",
                       f"{t.task_id}|{t.prompt() + ANSWER_SUFFIX}", WINDOW)
        e = by_key.get(key.digest())
        if e is None:
            continue
        got = ReplayCache.to_answers(e)
        top = got[0] if got else None
        emp = resolve_issuer(top.employer_name if top else None, issuer_index)
        res = resolve(top.person_name if top else None, emp, index,
                      anchor_issuer_cik=t.anchor_issuer_cik)
        ans = Answer(person_cik=res.person_cik,
                     confidence=top.confidence if top else 0.0, employer_cik=emp)
        truth = AttestedTuple(
            accession=t.truth_accession, person_cik=t.person_cik,
            person_name_raw=t.person_name_raw, issuer_cik=t.truth_issuer_cik,
            issuer_name_raw=t.truth_issuer_name, issuer_ticker="",
            role_class=frozenset({RoleClass.OFFICER}), title_raw="",
            title_class=t.truth_title_class, period=t.truth_period,
            filed=t.truth_filed)
        obs.append(Observation("exa", "answer", t.collision_band,
                               judge(ans, truth), ans.confidence, e.spend_usd))
        tasks.append(t)

    if not obs:
        raise NoObservations(
            "no cached observations matched the current task set - the prompt "
            "or task construction changed since they were recorded, so the "
            "cache keys no longer line up")
    return RealEnvParts(fit(obs, split=split), obs, tasks, index, issuer_index)
