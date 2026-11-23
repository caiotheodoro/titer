#!/usr/bin/env python3
"""Zero-spend post-hoc statistical analyses on committed artifacts (D049).

Computes two analyses strictly from `results/expertise_e1_v2.json` and
`results/expertise_control.json`:

  A. Unpaired distance-gradient and cross-run baseline tests across NEAR, FAR,
     and CONTROL false-claim strata plus the two attested arms.
  B. Murphy (1973) binned Brier score decomposition (reliability, resolution,
     uncertainty, within-bin residual) and Brier Skill Score for both runs.

No API is called and nothing is spent. Writes `results/posthoc_stats.json`.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = RES / "posthoc_stats.json"
Z95 = 1.959964


def load(name: str) -> dict[str, Any]:
    return json.loads((RES / f"{name}.json").read_text())


def wilson(k: int, n: int, z: float = Z95) -> tuple[float, float, float]:
    p = k / n
    d = 1.0 + z * z / n
    c = (p + z * z / (2.0 * n)) / d
    h = z * math.sqrt(p * (1.0 - p) / n + z * z / (4.0 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """Newcombe (1998) method 10 hybrid score interval for p1 - p2."""
    p1, l1, u1 = wilson(k1, n1)
    p2, l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lo, hi


def pearson_chi2_homogeneity(counts: list[tuple[int, int]]) -> dict[str, float]:
    """Pearson chi-squared test of homogeneity for a 2 x K contingency table.

    For K = 3 (df = 2), the chi-squared survival function is exact: exp(-chi2 / 2).
    """
    if len(counts) != 3:
        raise ValueError("exact df=2 survival function requires K=3 strata")
    n_tot = sum(n for _, n in counts)
    k_tot = sum(k for k, _ in counts)
    p_hat = k_tot / n_tot
    chi2 = 0.0
    for k, n in counts:
        e1 = n * p_hat
        e0 = n * (1.0 - p_hat)
        if e1 > 0:
            chi2 += (k - e1) ** 2 / e1
        if e0 > 0:
            chi2 += ((n - k) - e0) ** 2 / e0
    p_val = math.exp(-chi2 / 2.0)
    return {"chi2": chi2, "df": 2, "p_value": p_val}


def cochran_armitage_trend(
    counts: list[tuple[int, int]],
    scores: list[float],
) -> dict[str, float]:
    """Two-sided Cochran-Armitage linear trend test (Cochran 1954; Armitage 1955)."""
    if len(counts) != len(scores):
        raise ValueError("counts and scores must have equal length")
    n_tot = sum(n for _, n in counts)
    k_tot = sum(k for k, _ in counts)
    p_hat = k_tot / n_tot
    w_bar = sum(n * w for (_, n), w in zip(counts, scores)) / n_tot
    num = sum(k * (w - w_bar) for (k, _), w in zip(counts, scores))
    denom_sq = p_hat * (1.0 - p_hat) * sum(n * (w - w_bar) ** 2 for (_, n), w in zip(counts, scores))
    if denom_sq == 0.0:
        return {"z": 0.0, "chi2_trend": 0.0, "p_value": 1.0}
    z = num / math.sqrt(denom_sq)
    p_val = math.erfc(abs(z) / math.sqrt(2.0))
    return {"z": z, "chi2_trend": z * z, "p_value": p_val}


def fisher_exact_two_sided(k1: int, n1: int, k2: int, n2: int) -> float:
    """Exact two-sided Fisher's exact test p-value for a 2x2 table."""
    total_k = k1 + k2
    total_n = n1 + n2
    denom = math.comb(total_n, total_k)

    def prob(x: int) -> float:
        return (math.comb(n1, x) * math.comb(n2, total_k - x)) / denom

    p_obs = prob(k1)
    lo = max(0, total_k - n2)
    hi = min(n1, total_k)
    tol = p_obs * (1.0 + 1e-12)
    p_sum = sum(prob(x) for x in range(lo, hi + 1) if prob(x) <= tol)
    return min(1.0, p_sum)


def murphy_brier_decomposition(cal: dict[str, Any]) -> dict[str, float]:
    """Murphy (1973) binned decomposition of the Brier score from committed 10-bin summaries."""
    n_tot = int(cal["n"])
    bins = [b for b in cal["bins"] if not b["empty"] and b["n"] > 0]
    y_bar = sum(b["n"] * b["accuracy"] for b in bins) / n_tot
    p_bar = sum(b["n"] * b["mean_confidence"] for b in bins) / n_tot
    uncertainty = y_bar * (1.0 - y_bar)
    reliability = sum(b["n"] * (b["mean_confidence"] - b["accuracy"]) ** 2 for b in bins) / n_tot
    resolution = sum(b["n"] * (b["accuracy"] - y_bar) ** 2 for b in bins) / n_tot
    brier_binned = reliability - resolution + uncertainty
    brier_exact = float(cal["brier"])
    within_bin_residual = brier_exact - brier_binned
    bss = 1.0 - (brier_exact / uncertainty) if uncertainty > 0 else float("nan")
    return {
        "n": n_tot,
        "mean_accuracy": y_bar,
        "mean_confidence": p_bar,
        "ece": float(cal["ece"]),
        "brier_exact": brier_exact,
        "uncertainty": uncertainty,
        "reliability": reliability,
        "resolution": resolution,
        "brier_binned": brier_binned,
        "within_bin_residual": within_bin_residual,
        "brier_excess_over_constant": brier_exact - uncertainty,
        "brier_skill_score": bss,
    }


def build() -> dict[str, Any]:
    e1 = load("expertise_e1_v2")
    ctl = load("expertise_control")
    s1, sc = e1["by_stratum"], ctl["by_stratum"]

    kn, nn = s1["FALSE_near"]["outcomes"]["FALSE_MERGE"], s1["FALSE_near"]["n"]
    kf, nf = s1["FALSE_far"]["outcomes"]["FALSE_MERGE"], s1["FALSE_far"]["n"]
    kc, nc = sc["FALSE_far_domain"]["outcomes"]["FALSE_MERGE"], sc["FALSE_far_domain"]["n"]

    ka1, na1 = s1["ATTESTED"]["outcomes"]["CORRECT"], s1["ATTESTED"]["n"]
    ka2, na2 = sc["ATTESTED"]["outcomes"]["CORRECT"], sc["ATTESTED"]["n"]
    att_diff, att_lo, att_hi = newcombe(ka1, na1, ka2, na2)

    counts_false = [(kn, nn), (kf, nf), (kc, nc)]
    chi2 = pearson_chi2_homogeneity(counts_false)
    trend = cochran_armitage_trend(counts_false, [2.0, 1.0, 0.0])
    fisher_nc = fisher_exact_two_sided(kn, nn, kc, nc)
    fisher_att = fisher_exact_two_sided(ka1, na1, ka2, na2)

    return {
        "decision": "D049",
        "post_hoc": True,
        "spend_usd": 0.0,
        "sources": [
            "results/expertise_e1_v2.json",
            "results/expertise_control.json",
        ],
        "distance_gradient": {
            "caveat": (
                "Unpaired cross-run comparison: NEAR and FAR come from results/expertise_e1_v2.json "
                "and CONTROL from results/expertise_control.json on independent draws of authors "
                "and topics. All p-values assume independent binomial samples and do not absorb "
                "run-to-run or draw-to-draw variance."
            ),
            "strata": {
                "NEAR": {"k": kn, "n": nn, "rate": kn / nn, "score": 2},
                "FAR": {"k": kf, "n": nf, "rate": kf / nf, "score": 1},
                "CONTROL": {"k": kc, "n": nc, "rate": kc / nc, "score": 0},
            },
            "pearson_chi2": chi2,
            "cochran_armitage": trend,
            "fisher_exact_near_vs_control": {
                "p_value": fisher_nc,
                "odds_ratio": (kn / (nn - kn)) / (kc / (nc - kc)),
            },
            "attested_cross_run_check": {
                "main_k": ka1,
                "main_n": na1,
                "control_k": ka2,
                "control_n": na2,
                "diff_main_minus_control": att_diff,
                "newcombe_95": [att_lo, att_hi],
                "fisher_exact_p": fisher_att,
            },
        },
        "brier_decomposition": {
            "method": (
                "Murphy (1973) 10-bin decomposition: Brier_binned = Reliability - Resolution + "
                "Uncertainty, where Uncertainty = y_bar * (1 - y_bar) is the exact Brier score of "
                "a hindsight constant forecaster at the pooled accuracy. within_bin_residual = "
                "brier_exact - brier_binned equals within-bin confidence variance minus twice "
                "within-bin confidence-outcome covariance."
            ),
            "main_run": murphy_brier_decomposition(e1["calibration"]),
            "control_run": murphy_brier_decomposition(ctl["calibration"]),
        },
    }


def main() -> int:
    data = build()
    OUT.write_text(json.dumps(data, indent=2) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
