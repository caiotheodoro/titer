"""Tests for the zero-spend post-hoc statistical analyses (D049, D050)."""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import posthoc_stats as ps  # noqa: E402


def test_posthoc_artifact_matches_fresh_build() -> None:
    committed = json.loads((ROOT / "results" / "posthoc_stats.json").read_text())
    assert committed == ps.build(), "results/posthoc_stats.json drifted; run scripts/posthoc_stats.py"


def test_fisher_exact_known_tables() -> None:
    # Identical proportions -> p = 1.0
    assert math.isclose(ps.fisher_exact_two_sided(5, 10, 5, 10), 1.0, abs_tol=1e-12)
    # Classic Lady Tasting Tea 4/4 vs 0/4: two-sided p = 2 / C(8,4) = 2/70 = 1/35
    assert math.isclose(ps.fisher_exact_two_sided(4, 4, 0, 4), 2.0 / 70.0, abs_tol=1e-12)


def test_cochran_armitage_null_and_sign() -> None:
    null = ps.cochran_armitage_trend([(10, 100), (10, 100), (10, 100)], [2.0, 1.0, 0.0])
    assert null["z"] == 0.0 and null["p_value"] == 1.0
    pos = ps.cochran_armitage_trend([(30, 100), (20, 100), (10, 100)], [2.0, 1.0, 0.0])
    assert pos["z"] > 0 and pos["p_value"] < 0.01
    # Reversing scores flips sign only
    neg = ps.cochran_armitage_trend([(30, 100), (20, 100), (10, 100)], [0.0, 1.0, 2.0])
    assert math.isclose(pos["z"], -neg["z"], abs_tol=1e-12)
    assert math.isclose(pos["p_value"], neg["p_value"], abs_tol=1e-12)


def test_murphy_decomposition_identities() -> None:
    data = ps.build()
    for run_key in ("main_run", "control_run"):
        d = data["brier_decomposition"][run_key]
        assert math.isclose(
            d["uncertainty"],
            d["mean_accuracy"] * (1.0 - d["mean_accuracy"]),
            abs_tol=1e-12,
        )
        assert math.isclose(
            d["brier_binned"],
            d["reliability"] - d["resolution"] + d["uncertainty"],
            abs_tol=1e-12,
        )
        assert math.isclose(
            d["brier_exact"],
            d["brier_binned"] + d["within_bin_residual"],
            abs_tol=1e-12,
        )
        assert math.isclose(
            d["brier_skill_score"],
            1.0 - d["brier_exact"] / d["uncertainty"],
            abs_tol=1e-12,
        )
        # Both runs are worse than a constant forecast
        assert d["brier_skill_score"] < 0.0
        assert d["reliability"] > d["resolution"]
