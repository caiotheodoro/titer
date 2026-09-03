import random

from titer.metrics.calibration import (brier, coverage_floor, fit_isotonic,
                                       reliability, risk_coverage_curve)


def test_always_ten_bins_even_when_most_are_empty():
    """CONTRACTS: empty bins are never merged. Merging them flatters
    calibration by deleting the regions with no data."""
    d = reliability([0.95] * 20, [True] * 20)
    assert len(d.bins) == 10
    assert d.empty_bins == 9
    assert d.as_dict()["n_bins"] == 10


def test_empty_bins_contribute_nothing_rather_than_perfect_calibration():
    d = reliability([0.95] * 20, [True] * 20)
    empty = [b for b in d.bins if b.empty]
    assert all(b.gap == 0.0 and b.n == 0 for b in empty)
    # ECE reflects only the occupied bin
    assert abs(d.ece - 0.05) < 1e-9


def test_confidence_of_exactly_one_is_not_dropped():
    """An off-by-one at the top edge silently discards the most confident
    answers, which are the ones a false-merge measurement cares about most."""
    d = reliability([1.0] * 7, [False] * 7)
    assert d.n == 7
    assert sum(b.n for b in d.bins) == 7


def test_perfect_calibration_has_near_zero_ece():
    rng = random.Random(11)
    confs, correct = [], []
    for _ in range(4000):
        p = rng.random()
        confs.append(p)
        correct.append(rng.random() < p)
    assert reliability(confs, correct).ece < 0.05


def test_overconfidence_is_visible():
    d = reliability([0.9] * 100, [True] * 50 + [False] * 50)
    assert abs(d.ece - 0.4) < 1e-9


def test_reliability_rejects_mismatched_lengths():
    try:
        reliability([0.5, 0.5], [True])
    except ValueError:
        pass
    else:
        raise AssertionError("mismatched lengths accepted")


def test_brier_bounds():
    assert brier([1.0] * 10, [True] * 10) == 0.0
    assert brier([1.0] * 10, [False] * 10) == 1.0
    assert abs(brier([0.5] * 10, [True] * 5 + [False] * 5) - 0.25) < 1e-12


def test_isotonic_is_monotone_and_improves_a_miscalibrated_signal():
    rng = random.Random(7)
    raw = [rng.random() for _ in range(2000)]
    # true probability is the square of the stated confidence: overconfident
    correct = [rng.random() < c ** 2 for c in raw]
    half = len(raw) // 2
    f = fit_isotonic(raw[:half], correct[:half])
    out = [f(c) for c in raw[half:]]
    assert brier(out, correct[half:]) < brier(raw[half:], correct[half:])
    xs = sorted(raw[half:])
    ys = [f(x) for x in xs]
    assert all(a <= b + 1e-12 for a, b in zip(ys, ys[1:]))


def test_isotonic_fit_on_empty_is_identity():
    f = fit_isotonic([], [])
    assert f(0.3) == 0.3


def test_coverage_and_risk_come_as_one_object():
    """A risk floor at an unstated coverage is meaningless: you can always
    drive risk to zero by answering nothing."""
    confs = [0.9] * 10 + [0.1] * 90
    correct = [True] * 10 + [False] * 90
    cf = coverage_floor(confs, correct, 0.5)
    assert (cf.coverage, cf.risk, cf.n_answered, cf.n_total) == (0.1, 0.0, 10, 100)
    assert not hasattr(cf, "__iter__")   # cannot be unpacked into risk alone


def test_abstaining_entirely_reports_zero_coverage_not_zero_risk_alone():
    cf = coverage_floor([0.1] * 50, [False] * 50, 0.99)
    assert cf.coverage == 0.0 and cf.n_answered == 0


def test_risk_falls_as_coverage_falls_for_an_informative_signal():
    rng = random.Random(3)
    confs = [rng.random() for _ in range(2000)]
    correct = [rng.random() < c for c in confs]
    curve = risk_coverage_curve(confs, correct)
    populated = [c for c in curve if c.n_answered > 50]
    assert populated[0].risk > populated[-1].risk


def test_risk_coverage_curve_covers_the_full_range():
    curve = risk_coverage_curve([0.5] * 10, [True] * 10)
    assert curve[0].threshold == 0.0 and abs(curve[-1].threshold - 1.0) < 1e-12
