#!/usr/bin/env python3
"""Generate everything numeric in paper/titer.tex from the committed results (D046).

The paper types no measured number. Each one is a LaTeX macro written here from a file under
`results/`, or a table / figure generated here from the same files. `tests/test_paper.py`
(a) rebuilds this output and requires it byte-identical to the committed copy under
`paper/generated/`, and (b) refuses any decimal literal in `paper/titer.tex` that is not a
generated value, so a number cannot be typed into the prose without an artifact behind it.

Derived quantities (the Newcombe difference intervals, the NEAR/CONTROL ratio, the
overall confidence and accuracy of the E3 pool) are computed here from committed counts, never
by hand. No provider is called and nothing is spent.

    python3 scripts/export_paper_tables.py          # rewrite paper/generated/
"""
from __future__ import annotations

import json
import math
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
RES = ROOT / "results"
OUT = ROOT / "paper" / "generated"
Z = 1.959964

_INTERVAL = re.compile(r"(-?\d+\.\d+) \[(-?\d+\.\d+), (-?\d+\.\d+)\] n=(\d+)")


def load(name: str) -> dict[str, Any]:
    return json.loads((RES / f"{name}.json").read_text())


def wilson(k: int, n: int, z: float = Z) -> tuple[float, float, float]:
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return p, max(0.0, c - h), min(1.0, c + h)


def newcombe(k1: int, n1: int, k2: int, n2: int) -> tuple[float, float, float]:
    """Newcombe (1998) method 10: hybrid score interval for p1 - p2."""
    p1, l1, u1 = wilson(k1, n1)
    p2, l2, u2 = wilson(k2, n2)
    d = p1 - p2
    lo = d - math.sqrt((p1 - l1) ** 2 + (u2 - p2) ** 2)
    hi = d + math.sqrt((u1 - p1) ** 2 + (p2 - l2) ** 2)
    return d, lo, hi


def parse_interval(s: str) -> tuple[float, float, float, int]:
    m = _INTERVAL.search(s)
    if not m:
        raise ValueError(f"not an interval string: {s!r}")
    return float(m[1]), float(m[2]), float(m[3]), int(m[4])


def f4(x: float) -> str:
    return f"{x:.4f}"


def f3(x: float) -> str:
    return f"{x:.3f}"


def f2(x: float) -> str:
    return f"{x:.2f}"


def pct1(x: float) -> str:
    return f"{x * 100:.1f}"


def tex_signed4(x: float) -> str:
    s = f"{x:+.4f}"
    return s.replace("-", "$-$") if s.startswith("-") else s


def check_wilson(label: str, k: int, n: int, shown: str) -> None:
    """The artifact's own interval string must equal a recomputation from its counts."""
    p, lo, hi, nn = parse_interval(shown)
    q, qlo, qhi = wilson(k, n)
    assert nn == n and abs(p - round(q, 4)) < 1e-9, (label, p, q)
    assert abs(lo - round(qlo, 4)) < 1.1e-4 and abs(hi - round(qhi, 4)) < 1.1e-4, (label, shown, qlo, qhi)


# ---------------------------------------------------------------------------- numbers
def numbers() -> dict[str, str]:
    m: dict[str, str] = {}

    def put(name: str, value: Any) -> None:
        assert name not in m, name
        m[name] = str(value)

    def rate(prefix: str, k: int, n: int, shown: str | None = None) -> None:
        if shown is not None:
            check_wilson(prefix, k, n, shown)
        p, lo, hi = wilson(k, n)
        put(f"{prefix}K", k)
        put(f"{prefix}N", n)
        put(f"{prefix}Rate", f4(p))
        put(f"{prefix}Lo", f4(lo))
        put(f"{prefix}Hi", f4(hi))

    e1 = load("expertise_e1_v2")
    ctl = load("expertise_control")
    raw = load("expertise_e1")
    s1, sc, sr = e1["by_stratum"], ctl["by_stratum"], raw["by_stratum"]

    att, far, near = s1["ATTESTED"], s1["FALSE_far"], s1["FALSE_near"]
    catt, cfar = sc["ATTESTED"], sc["FALSE_far_domain"]
    rate("tiAtt", att["outcomes"]["CORRECT"], att["n"], att["correct"])
    rate("tiNear", near["outcomes"]["FALSE_MERGE"], near["n"], near["false_merge"])
    rate("tiFar", far["outcomes"]["FALSE_MERGE"], far["n"], far["false_merge"])
    rate("tiCtl", cfar["outcomes"]["FALSE_MERGE"], cfar["n"], cfar["false_merge"])
    rate("tiCtlAtt", catt["outcomes"]["CORRECT"], catt["n"], catt["correct"])
    put("tiAttMiss", att["outcomes"]["MISS"])
    put("tiCtlAttMiss", catt["outcomes"]["MISS"])
    put("tiSeed", e1["seed"])
    put("tiEoneSpend", f2(e1["spend_usd"]))
    put("tiCtlSpend", f2(ctl["spend_usd"]))
    put("tiCalls", e1["n"] + ctl["n"])
    put("tiPoolAtt", e1["strata"]["ATTESTED"]["available"])
    put("tiPoolFar", e1["strata"]["FALSE_far"]["available"])
    put("tiPoolNear", e1["strata"]["FALSE_near"]["available"])
    put("tiCtlPool", ctl["strata"]["FALSE_far_domain"]["available"])
    put("tiCtlPoolAtt", ctl["strata"]["ATTESTED"]["available"])
    put("tiTotalCalls", e1["n"] + ctl["n"])

    kn, nn_ = near["outcomes"]["FALSE_MERGE"], near["n"]
    kf, nf = far["outcomes"]["FALSE_MERGE"], far["n"]
    kc, nc = cfar["outcomes"]["FALSE_MERGE"], cfar["n"]
    put("tiRatioNearCtl", f2((kn / nn_) / (kc / nc)))
    put("tiRatioFarCtl", f2((kf / nf) / (kc / nc)))
    for tag, (k1, n1) in (("NearCtl", (kn, nn_)), ("FarCtl", (kf, nf))):
        d, lo, hi = newcombe(k1, n1, kc, nc)
        put(f"ti{tag}Diff", f4(d))
        put(f"ti{tag}DiffLo", f4(lo))
        put(f"ti{tag}DiffHi", f4(hi))
    d, lo, hi = newcombe(kn, nn_, kf, nf)
    put("tiNearFarDiff", f4(d))
    put("tiNearFarDiffLo", f4(lo))
    put("tiNearFarDiffHi", f4(hi))
    # the floor argument: control points as a share of the NEAR rate
    put("tiFloorShare", pct1((kc / nc) / (kn / nn_)))
    put("tiNearPoints", f"{kn / nn_ * 100:.1f}")
    put("tiCtlPoints", f"{kc / nc * 100:.1f}")

    # retracted raw run (R002)
    put("tiRawN", sr["FALSE_far"]["n"])
    put("tiRawFar", f4(sr["FALSE_far"]["outcomes"]["FALSE_MERGE"] / sr["FALSE_far"]["n"]))
    put("tiRawNear", f4(sr["FALSE_near"]["outcomes"]["FALSE_MERGE"] / sr["FALSE_near"]["n"]))
    put("tiRawAtt", f4(sr["ATTESTED"]["outcomes"]["CORRECT"] / sr["ATTESTED"]["n"]))
    put("tiRawSpend", f2(raw["spend_usd"]))
    put("tiRawCalls", raw["n"])

    # E3 calibration
    cal, ccal = e1["calibration"], ctl["calibration"]
    top, ctop = cal["bins"][-1], ccal["bins"][-1]
    put("tiCalN", cal["n"])
    put("tiCalTopN", top["n"])
    put("tiCalTopShare", pct1(top["n"] / cal["n"]))
    put("tiCalTopConf", f3(top["mean_confidence"]))
    put("tiCalTopAcc", f3(top["accuracy"]))
    put("tiCalTopGap", f"{(top['mean_confidence'] - top['accuracy']) * 100:.1f}")
    put("tiEce", f4(cal["ece"]))
    put("tiBrier", f4(cal["brier"]))
    put("tiCalZeroN", cal["bins"][0]["n"])
    acc_all = sum(b["n"] * b["accuracy"] for b in cal["bins"]) / cal["n"]
    conf_all = sum(b["n"] * b["mean_confidence"] for b in cal["bins"]) / cal["n"]
    put("tiCalAccAll", f3(acc_all))
    put("tiCalConfAll", f3(conf_all))
    put("tiCtlCalN", ccal["n"])
    put("tiCtlCalTopN", ctop["n"])
    put("tiCtlCalTopConf", f3(ctop["mean_confidence"]))
    put("tiCtlCalTopAcc", f3(ctop["accuracy"]))
    put("tiCtlEce", f4(ccal["ece"]))
    put("tiCtlBrier", f4(ccal["brier"]))
    put("tiCtlEmptyBins", ccal["empty_bins"])
    # what a constant-0.99 forecaster scores on this task mix: the floor for the pooled Brier
    base = (att["outcomes"]["CORRECT"] + far["outcomes"]["CORRECT"] + near["outcomes"]["CORRECT"]) / e1["n"]
    put("tiBaseAcc", f3(base))
    put("tiBrierBase", f4(base * (1 - base)))

    # A12 citation audit
    a12 = load("a12_citation_audit")
    for tag, key in (("Att", "ATTESTED"), ("Far", "FALSE_far"), ("Near", "FALSE_near"), ("Ctl", "FALSE_far_domain")):
        st = a12["strata"][key]
        rate(f"tiAa{tag}", st["backed"], st["n"], st["backed_wilson"])
        put(f"tiAa{tag}NoTitle", st["no_resolvable_title"])
        put(f"tiAa{tag}NoTitleShare", pct1(st["no_resolvable_title"] / st["n"]))
    put("tiAaTotal", a12["audited"])
    # The audit covers every false affirmation in the cache, including those of the retracted
    # run (R002). That is derivable from the committed counts, and the paper says it; if the
    # arithmetic stops holding the sentence is wrong and the build must fail.
    assert a12["strata"]["FALSE_far"]["n"] == far["outcomes"]["FALSE_MERGE"] + sr["FALSE_far"]["outcomes"]["FALSE_MERGE"]
    assert a12["strata"]["FALSE_near"]["n"] == near["outcomes"]["FALSE_MERGE"] + sr["FALSE_near"]["outcomes"]["FALSE_MERGE"]
    assert a12["strata"]["FALSE_far_domain"]["n"] == cfar["outcomes"]["FALSE_MERGE"]
    put("tiAaFarMain", far["outcomes"]["FALSE_MERGE"])
    put("tiAaFarRaw", sr["FALSE_far"]["outcomes"]["FALSE_MERGE"])
    put("tiAaNearMain", near["outcomes"]["FALSE_MERGE"])
    put("tiAaNearRaw", sr["FALSE_near"]["outcomes"]["FALSE_MERGE"])
    put("tiAaAttAvail", att["outcomes"]["CORRECT"] + sr["ATTESTED"]["outcomes"]["CORRECT"] + catt["outcomes"]["CORRECT"])

    # my reading of the 21 CONTROL affirmations (a judgement, committed as an artifact)
    rd = load("control_affirmations_read")
    cats = [i["category"] for i in rd["items"]]
    assert len(cats) == rd["n"] == cfar["outcomes"]["FALSE_MERGE"]
    for tag, cat in (("Broad", "broad_label"), ("Same", "plausible_same_person"), ("Other", "unsupported_or_other_person")):
        put(f"tiRd{tag}", cats.count(cat))
    rate("tiRdErr", cats.count("unsupported_or_other_person"), cfar["n"])
    put("tiRdErrShare", pct1(cats.count("unsupported_or_other_person") / len(cats)))

    # H2
    h2 = load("h2_false_merge")
    for tag, band in (("U", "unique"), ("L", "low"), ("M", "medium"), ("H", "high")):
        b = h2["bands"][band]
        rate(f"tiHtwo{tag}", b["false_merge"], b["n"], b["wilson"])
    put("tiHtwoContam", f4(h2["contamination_bound"]))

    # E2
    for tag, band in (("U", "unique"), ("L", "low"), ("M", "medium"), ("H", "high")):
        d = load(f"e2_exa_{band}")
        for arm, a in (("A", "exa_A_name_only"), ("C", "exa_C_anchor_freetext"), ("D", "exa_D_full_context")):
            rate(f"tiEtwo{tag}{arm}", d["arms"][a]["outcomes"]["CORRECT"], d["arms"][a]["n"], d["arms"][a]["correct"])
        pr = d["e2_paired"]
        for arm, key in (("CA", "exa_A_name_only - exa_C_anchor_freetext"), ("DA", "exa_A_name_only - exa_D_full_context"),
                         ("DC", "exa_C_anchor_freetext - exa_D_full_context")):
            pt, lo, hi, _ = parse_interval(pr[key]["diff"])
            put(f"tiEtwo{tag}{arm}Pt", f4(-pt))
            put(f"tiEtwo{tag}{arm}Lo", f4(-hi))
            put(f"tiEtwo{tag}{arm}Hi", f4(-lo))
    put("tiEtwoN", 80)
    put("tiEtwoCollN", 80)
    put("tiEtwoSeed", load("e2_exa_unique")["seed"])

    # H1
    h1 = load("h1_elapsed")
    put("tiHoneIsoLag", h1["arms"]["exa"]["median_reflection_lag_days"])
    hr = load("h1_random")
    put("tiHoneRandLag", hr["arms"]["exa"]["median_reflection_lag_days"])
    put("tiWOneN", hr["arms"]["exa"]["n"])
    put("tiWOneCorrect", hr["arms"]["exa"]["outcomes"]["CORRECT"])
    pw = hr["arms"]["webfloor"]
    put("tiWebN", pw["n"])
    put("tiWebCorrect", pw["outcomes"]["CORRECT"])
    put("tiWebNotInCorpus", pw.get("resolution_reasons", {}).get("name_not_in_corpus", "NA"))
    ex = hr["arms"]["exa"]
    put("tiWOneFalseMerge", ex["outcomes"]["FALSE_MERGE"])

    # Provider P runs (named in the repository; the paper calls it Provider P)
    fr, pc, p4, pe = load("full_run"), load("ploid_corrected"), load("ploid_v4"), load("e2_ploid_medium")
    put("tiPRunOneN", fr["arms"]["ploid"]["n"])
    put("tiPRunOneCorrect", fr["arms"]["ploid"]["outcomes"]["CORRECT"])
    put("tiPRunOneMiss", fr["arms"]["ploid"]["outcomes"]["MISS"])
    put("tiPRunTwoN", pc["arms"]["ploid"]["n"])
    put("tiPRunTwoCorrect", pc["arms"]["ploid"]["outcomes"]["CORRECT"])
    put("tiPRunTwoMiss", pc["arms"]["ploid"]["outcomes"]["MISS"])
    put("tiPRunFourN", p4["arms"]["ploid"]["n"])
    put("tiPRunFourCorrect", p4["arms"]["ploid"]["outcomes"]["CORRECT"])
    put("tiPRunArmN", pe["arms"]["ploid_A_name_only"]["n"])
    put("tiPRunArmCorrect", pe["arms"]["ploid_A_name_only"]["outcomes"]["CORRECT"]
        + pe["arms"]["ploid_B_company_filter"]["outcomes"]["CORRECT"])
    put("tiPRunArmResolvedFilter", sum(v for k, v in pe["arms"]["ploid_B_company_filter"]["resolution_reasons"].items()
                                       if k in ("unique_name", "narrowed_by_anchor")))
    put("tiPRunArmResolvedName", sum(v for k, v in pe["arms"]["ploid_A_name_only"]["resolution_reasons"].items()
                                     if k in ("unique_name", "narrowed_by_anchor")))
    put("tiPRunArmStale", pe["arms"]["ploid_B_company_filter"]["outcomes"]["STALE"])
    pw_ = load("power")
    put("tiPowerN", pw_["required_n"]["H2 false-merge rate"]["hw=0.1"])
    price = float(re.search(r"\$(\d+\.\d+)", next(iter(pw_["achievable"]))).group(1))
    put("tiPowerPrice", f2(price))
    put("tiPowerCost", f2(pw_["required_n"]["H2 false-merge rate"]["hw=0.1"] * price))

    # Two numbers that exist only in prose records (no results file holds them). They are read
    # from the document that states them, so a rewording of that document breaks the build.
    rt = (ROOT / "docs" / "RED-TEAM.md").read_text()
    mm = re.search(r"Spot-checked at 0/(\d+) contaminated \[0, (0\.\d+)\]", rt)
    assert mm, "RED-TEAM.md no longer states the spot check"
    put("tiSpotN", mm[1])
    put("tiSpotHi", mm[2])
    put("tiSpotHiPct", f"{float(mm[2]) * 100:.1f}")
    cv = (ROOT / "docs" / "COVERAGE.md").read_text()
    mm = re.search(r"\*\*([\d,]+) \(([\d.]+)%\)\*\*", cv)
    assert mm, "COVERAGE.md no longer states the usable share"
    put("tiUsableN", mm[1].replace(",", "{,}"))
    put("tiUsablePct", mm[2])

    # corpora, spend
    cs, ts, ss = load("corpus_stats"), load("task_stats"), load("scholar_stats")
    put("tiCorpusRows", f"{cs['rows']:,}".replace(",", "{,}"))
    put("tiCorpusPeople", f"{cs['distinct_person_cik']:,}".replace(",", "{,}"))
    put("tiTasks", f"{ts['tasks']:,}".replace(",", "{,}"))
    put("tiEntityFilers", ts["excluded_entity_filers"])
    put("tiAuthors", f"{ss['authors']:,}".replace(",", "{,}"))
    put("tiTopics", f"{ss['topics_in_hierarchy']:,}".replace(",", "{,}"))
    card = json.loads((ROOT / "MEASUREMENT_CARD.json").read_text())
    put("tiSpendTotal", f2(card["spend_usd"]["total"]))
    put("tiSpendExa", f2(card["spend_usd"]["exa"]))

    # R4
    eh = load("env_health_real")
    tp = load("train_policy")
    put("tiEnvObs", eh["observations"])
    put("tiSolve", f2(eh["solve_rate_proxy"]))
    for k, tag in (("never_verify", "Never"), ("always_deep_verify", "Deep"), ("abstain_always", "Abst")):
        put(f"tiFloor{tag}", f4(eh["floors"][k]["mean_reward"]).replace("-", "\\ensuremath{-}"))
    sc_ = tp["frozen_test_scores"]
    mean = sum(sc_) / len(sc_)
    sd = math.sqrt(sum((x - mean) ** 2 for x in sc_) / (len(sc_) - 1))
    put("tiFloorNeverCorrect", eh["floors"]["never_verify"]["outcomes"]["CORRECT"])
    put("tiFloorDeepCorrect", eh["floors"]["always_deep_verify"]["outcomes"]["CORRECT"])
    put("tiFloorN", eh["floors"]["never_verify"]["n"])
    ba = tp["behaviour_last_seed"]["action_counts"]
    put("tiPolTasks", ba["query"])
    put("tiPolAnswered", ba["answer"])
    put("tiPolMean", f4(mean))
    put("tiPolSd", f4(sd))
    put("tiPolSeeds", len(sc_))
    put("tiPolSame", sum(1 for x in sc_ if x == min(sc_)))
    put("tiPolMargin", f4(mean - tp["baseline"]["value"]))
    put("tiPolAbstain", pct1(tp["behaviour_last_seed"]["abstain_rate"]))
    put("tiPolPrec", pct1(tp["behaviour_last_seed"]["precision_when_answering"]))

    # Post-hoc statistical analyses (D049, D050; results/posthoc_stats.json)
    ph = load("posthoc_stats")
    dg = ph["distance_gradient"]
    put("tiPostChiSq", f2(dg["pearson_chi2"]["chi2"]))
    put("tiPostChiP", f4(dg["pearson_chi2"]["p_value"]))
    put("tiPostTrendZ", f2(dg["cochran_armitage"]["z"]))
    put("tiPostTrendP", f4(dg["cochran_armitage"]["p_value"]))
    put("tiPostFisherNcP", f4(dg["fisher_exact_near_vs_control"]["p_value"]))
    put("tiPostFisherNcOr", f2(dg["fisher_exact_near_vs_control"]["odds_ratio"]))
    att_ck = dg["attested_cross_run_check"]
    put("tiPostAttDiff", tex_signed4(att_ck["diff_main_minus_control"]))
    put("tiPostAttDiffLo", tex_signed4(att_ck["newcombe_95"][0]))
    put("tiPostAttDiffHi", tex_signed4(att_ck["newcombe_95"][1]))
    put("tiPostAttFisherP", f4(att_ck["fisher_exact_p"]))

    bd = ph["brier_decomposition"]
    for tag, key in (("Main", "main_run"), ("Ctl", "control_run")):
        d = bd[key]
        put(f"tiPost{tag}Unc", f4(d["uncertainty"]))
        put(f"tiPost{tag}Rel", f4(d["reliability"]))
        put(f"tiPost{tag}Res", f4(d["resolution"]))
        put(f"tiPost{tag}Resid", tex_signed4(d["within_bin_residual"]))
        put(f"tiPost{tag}Excess", tex_signed4(d["brier_excess_over_constant"]))
        put(f"tiPost{tag}Bss", tex_signed4(d["brier_skill_score"]))
        put(f"tiPost{tag}Acc", f3(d["mean_accuracy"]))
    return m


# ---------------------------------------------------------------------------- tables
def _row(*cells: str) -> str:
    return " & ".join(cells) + r" \\"


def tab_e1(m: dict[str, str]) -> str:
    def iv(p: str) -> str:
        return f"{m[p + 'Rate']} [{m[p + 'Lo']}, {m[p + 'Hi']}]"

    rows = [
        _row("Attested claim", m["tiAttN"], "confirmed", iv("tiAtt"), m["tiAttK"], m["tiAttMiss"]),
        _row("False, adjacent subfield (NEAR)", m["tiNearN"], "affirmed", iv("tiNear"), m["tiNearK"], "0"),
        _row("False, adjacent field (FAR)", m["tiFarN"], "affirmed", iv("tiFar"), m["tiFarK"], "0"),
        _row("False, different domain (CONTROL)", m["tiCtlN"], "affirmed", iv("tiCtl"), m["tiCtlK"], "0"),
        _row("Attested, control run", m["tiCtlAttN"], "confirmed", iv("tiCtlAtt"), m["tiCtlAttK"], m["tiCtlAttMiss"]),
    ]
    return ("\\begin{tabular}{@{}lrllrr@{}}\n\\toprule\n"
            "Stratum & $n$ & Endpoint & Rate, 95\\% Wilson & Count & No answer \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_a12(m: dict[str, str]) -> str:
    rows = []
    for tag, label in (("Att", "Attested"), ("Far", "False, adjacent field"), ("Near", "False, adjacent subfield"),
                       ("Ctl", "False, different domain")):
        rows.append(_row(label, m[f"tiAa{tag}N"], f"{m[f'tiAa{tag}Rate']} [{m[f'tiAa{tag}Lo']}, {m[f'tiAa{tag}Hi']}]",
                         f"{m[f'tiAa{tag}NoTitle']} ({m[f'tiAa{tag}NoTitleShare']}\\%)"))
    return ("\\begin{tabular}{@{}lrlr@{}}\n\\toprule\n"
            "Affirmed claim & $n$ & Cites a work by that author & No title resolvable \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_h2(m: dict[str, str]) -> str:
    rows = []
    for tag, label in (("U", "1 (unique)"), ("L", "2--3"), ("M", "4--9"), ("H", "$\\ge$10")):
        rows.append(_row(label, m[f"tiHtwo{tag}N"], f"{m[f'tiHtwo{tag}K']}",
                         f"{m[f'tiHtwo{tag}Rate']} [{m[f'tiHtwo{tag}Lo']}, {m[f'tiHtwo{tag}Hi']}]"))
    return ("\\begin{tabular}{@{}lrrl@{}}\n\\toprule\n"
            "Collision degree & $n$ & Wrong identity & Rate, 95\\% Wilson \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_e2(m: dict[str, str]) -> str:
    rows = []
    for tag, label in (("U", "unique"), ("L", "low (2--3)"), ("M", "medium (4--9)"), ("H", "high ($\\ge$10)")):
        cell = lambda arm: f"{m[f'tiEtwo{tag}{arm}Rate']}"  # noqa: E731
        diff = f"{tex_signed4(float(m[f'tiEtwo{tag}CAPt']))} [{tex_signed4(float(m[f'tiEtwo{tag}CALo']))}, {tex_signed4(float(m[f'tiEtwo{tag}CAHi']))}]"
        rows.append(_row(label, cell("A"), cell("C"), cell("D"), diff))
    return ("\\begin{tabular}{@{}lrrrl@{}}\n\\toprule\n"
            "Band & A: name & C: + employer & D: + full anchor & Paired C $-$ A, 95\\% bootstrap \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_h1(m: dict[str, str]) -> str:
    h1 = load("h1_elapsed")["arms"]["exa"]["reflection_by_elapsed"]
    rows = []
    for label, s in h1:
        p, lo, hi, n = parse_interval(s)
        rows.append(_row(label.replace("-inf", "+").replace("d", " d").replace("-", "--"), str(n), f"{p:.4f} [{lo:.4f}, {hi:.4f}]"))
    return ("\\begin{tabular}{@{}lrl@{}}\n\\toprule\n"
            "Elapsed since filing & $n$ & Reflected, 95\\% Wilson \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


def tab_brier(m: dict[str, str]) -> str:
    rows = [
        _row("Main (1/3 attested, 2/3 false)", m["tiCalN"], m["tiBrier"], m["tiPostMainUnc"],
             m["tiPostMainRel"], m["tiPostMainRes"], m["tiPostMainResid"], m["tiPostMainBss"]),
        _row("Control (1/2 attested, 1/2 false)", m["tiCtlCalN"], m["tiCtlBrier"], m["tiPostCtlUnc"],
             m["tiPostCtlRel"], m["tiPostCtlRes"], m["tiPostCtlResid"], m["tiPostCtlBss"]),
    ]
    return ("\\begin{tabular}{@{}lrrrrrrr@{}}\n\\toprule\n"
            "Run (task mix) & $n$ & Brier & Constant & Rel. & Res. & Resid. & BSS \\\\\n\\midrule\n"
            + "\n".join(rows) + "\n\\bottomrule\n\\end{tabular}\n")


# ---------------------------------------------------------------------------- figures
def _axis_common() -> str:
    return ("grid=major,major grid style={dotted,gray!40},tick label style={font=\\footnotesize},"
            "label style={font=\\footnotesize}")


def fig_forest(m: dict[str, str]) -> str:
    body = []
    for i, tag in enumerate(("Near", "Far", "Ctl"), 1):
        p, lo, hi = float(m[f"ti{tag}Rate"]), float(m[f"ti{tag}Lo"]), float(m[f"ti{tag}Hi"])
        body.append(f"\\addplot[black,thick] coordinates {{({lo:.4f},{i}) ({hi:.4f},{i})}};")
        body.append(f"\\addplot[only marks,mark=*,black] coordinates {{({p:.4f},{i})}};")
    return ("\\begin{tikzpicture}\n"
            "\\begin{axis}[width=0.55\\linewidth,height=4.2cm,xlabel={false claims affirmed (rate, 95\\% Wilson)},"
            "xmin=0,xmax=0.26,xtick={0,0.05,0.1,0.15,0.2,0.25},xticklabels={0,0.05,0.10,0.15,0.20,0.25},ytick={1,2,3},yticklabels={NEAR (adjacent subfield),FAR (adjacent field),"
            "CONTROL (different domain)},ymin=0.4,ymax=3.6,y dir=reverse," + _axis_common() + "]\n"
            + "\n".join(body) + "\n\\end{axis}\n\\end{tikzpicture}\n")


def fig_reliability(m: dict[str, str]) -> str:
    e1 = load("expertise_e1_v2")["calibration"]["bins"]
    ctl = load("expertise_control")["calibration"]["bins"]

    def pts(bins: list[dict[str, Any]]) -> str:
        return " ".join(f"({b['mean_confidence']:.4f},{b['accuracy']:.4f})" for b in bins if not b["empty"] and b["n"] >= 5)

    return ("\\begin{tikzpicture}\n"
            "\\begin{axis}[width=0.62\\linewidth,height=6cm,xlabel={mean stated confidence},ylabel={accuracy},"
            "xmin=0.3,xmax=1.02,ymin=0.3,ymax=1.02,legend pos=south east,legend cell align=left,"
            "legend style={font=\\footnotesize,draw=none,fill=none}," + _axis_common() + "]\n"
            "\\addplot[gray,dashed] coordinates {(0.3,0.3) (1.0,1.0)};\n\\addlegendentry{perfect calibration}\n"
            f"\\addplot[only marks,mark=*,black] coordinates {{{pts(e1)}}};\n\\addlegendentry{{main run (bins with $n \\ge 5$)}}\n"
            f"\\addplot[only marks,mark=square*,gray] coordinates {{{pts(ctl)}}};\n\\addlegendentry{{control run}}\n"
            "\\end{axis}\n\\end{tikzpicture}\n")


def fig_h1(m: dict[str, str]) -> str:
    rows = load("h1_elapsed")["arms"]["exa"]["reflection_by_elapsed"]
    coords, bars = [], []
    for i, (label, s) in enumerate(rows, 1):
        p, lo, hi, _ = parse_interval(s)
        bars.append(f"\\addplot[black,thick] coordinates {{({i},{lo:.4f}) ({i},{hi:.4f})}};")
        coords.append(f"({i},{p:.4f})")
    labels = ",".join(l.replace("-inf", "+").replace("d", "\\,d").replace("-", "--") for l, _ in rows)
    return ("\\begin{tikzpicture}\n"
            "\\begin{axis}[width=0.8\\linewidth,height=5cm,xlabel={elapsed since the filing became public},"
            "ylabel={employer reflected},xtick={1,2,3,4,5},xticklabels={" + labels + "},ymin=0,ymax=1,xmin=0.5,xmax=5.5,"
            + _axis_common() + "]\n" + "\n".join(bars)
            + f"\n\\addplot[only marks,mark=*,black] coordinates {{{' '.join(coords)}}};\n"
            "\\end{axis}\n\\end{tikzpicture}\n")


# ---------------------------------------------------------------------------- driver
def numbers_tex(m: dict[str, str]) -> str:
    lines = ["% GENERATED by scripts/export_paper_tables.py from results/*.json. Do not edit."]
    for k in sorted(m):
        lines.append(f"\\newcommand{{\\{k}}}{{{m[k]}}}")
    return "\n".join(lines) + "\n"


def build() -> dict[str, str]:
    m = numbers()
    return {
        "numbers.tex": numbers_tex(m),
        "tab_e1.tex": tab_e1(m),
        "tab_a12.tex": tab_a12(m),
        "tab_h2.tex": tab_h2(m),
        "tab_e2.tex": tab_e2(m),
        "tab_h1.tex": tab_h1(m),
        "tab_brier.tex": tab_brier(m),
        "fig_forest.tex": fig_forest(m),
        "fig_reliability.tex": fig_reliability(m),
        "fig_h1.tex": fig_h1(m),
    }


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in build().items():
        (OUT / name).write_text(text)
    print(f"wrote {len(build())} files to {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
