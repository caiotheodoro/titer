import math

from titer.metrics.intervals import (Interval, paired_bootstrap, required_n,
                                     separates, wilson)
from titer.metrics.survival import binned_rates, pava


# --- Wilson ---

def test_wilson_matches_a_hand_computation():
    """Derived by hand, not read off the implementation. k=3, n=50, z=1.959964:

        p      = 0.06
        denom  = 1 + z^2/n          = 1.0768290
        centre = (p + z^2/2n)/denom = 0.0913933
        margin = z*sqrt(p(1-p)/n + z^2/4n^2)/denom
               = 1.959964*sqrt(0.001128 + 0.00038415)/1.0768290
               = 0.0707779
        lo, hi = 0.0206154, 0.1621712
    """
    i = wilson(3, 50)
    assert abs(i.point - 0.06) < 1e-12
    assert abs(i.lo - 0.0206154) < 1e-6
    assert abs(i.hi - 0.1621712) < 1e-6


def test_wilson_stays_in_bounds_at_the_extremes():
    """The normal approximation goes negative near 0. Ours must not - and rates
    near 0 are exactly what a false-merge measurement produces."""
    for n in (5, 50, 500):
        assert wilson(0, n).lo >= 0.0
        assert wilson(n, n).hi <= 1.0


def test_wilson_of_zero_n_is_maximally_uncertain():
    i = wilson(0, 0)
    assert (i.lo, i.hi) == (0.0, 1.0)


def test_half_width_shrinks_with_n():
    assert wilson(15, 100).half_width < wilson(3, 20).half_width


# --- power ---

def test_required_n_reproduces_the_preregistered_table():
    """PRE-REGISTRATION section 3 publishes this table. If the code and the
    frozen document disagree, one of them is wrong."""
    assert required_n(0.15, 0.14) <= 25
    assert 40 <= required_n(0.15, 0.10) <= 50
    assert 90 <= required_n(0.15, 0.07) <= 110
    assert 190 <= required_n(0.15, 0.05) <= 200
    assert 380 <= required_n(0.15, 0.035) <= 410


def test_required_n_grows_as_the_target_tightens():
    ns = [required_n(0.15, hw) for hw in (0.14, 0.10, 0.07, 0.05, 0.035)]
    assert ns == sorted(ns)


# --- paired bootstrap ---

def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def test_paired_bootstrap_is_deterministic_under_a_seed():
    a = [1.0] * 60 + [0.0] * 40
    b = [1.0] * 50 + [0.0] * 50
    x = paired_bootstrap(a, b, _mean, resamples=2000, seed=11)
    y = paired_bootstrap(a, b, _mean, resamples=2000, seed=11)
    assert (x.point, x.lo, x.hi) == (y.point, y.lo, y.hi)


def test_paired_bootstrap_finds_no_difference_between_identical_arms():
    a = [1.0] * 60 + [0.0] * 40
    i = paired_bootstrap(a, list(a), _mean, resamples=2000, seed=11)
    assert i.point == 0.0
    assert not separates(i)


def test_paired_bootstrap_detects_a_large_difference():
    a = [1.0] * 90 + [0.0] * 10
    b = [1.0] * 20 + [0.0] * 80
    i = paired_bootstrap(a, b, _mean, resamples=2000, seed=11)
    assert i.point > 0.6 and separates(i)


def test_paired_bootstrap_refuses_unequal_arms():
    """Silently zipping to the shorter arm would break the pairing that makes a
    small n worth anything."""
    try:
        paired_bootstrap([1.0, 0.0], [1.0], _mean)
    except ValueError as e:
        assert "equal lengths" in str(e)
    else:
        raise AssertionError("unequal arms were accepted")


def test_pairing_is_tighter_than_treating_arms_independently():
    """The whole reason the design is paired. Correlated arms must give a
    narrower difference interval than the same marginals uncorrelated."""
    n = 200
    base = [1.0 if i % 10 < 7 else 0.0 for i in range(n)]
    correlated_b = [x for x in base]
    correlated_a = [1.0 if (x == 1.0 or i % 20 == 0) else 0.0 for i, x in enumerate(base)]
    tight = paired_bootstrap(correlated_a, correlated_b, _mean, resamples=2000, seed=11)
    shuffled = list(reversed(correlated_b))
    loose = paired_bootstrap(correlated_a, shuffled, _mean, resamples=2000, seed=11)
    assert tight.half_width <= loose.half_width


# --- current status / isotonic ---

def test_pava_is_monotone_even_on_noisy_input():
    obs = [(10, True), (20, False), (30, False), (40, True), (50, False), (60, True)]
    c = pava(obs)
    assert c.is_monotone()


def test_pava_pools_adjacent_violators():
    obs = [(10, False), (20, False), (30, True), (40, False), (50, True)]
    c = pava(obs)
    pooled = [s for s in c.steps if 0.0 < s.prob < 1.0]
    assert pooled, "a True-then-False pair must be pooled, not left decreasing"


def test_pava_recovers_a_clean_step():
    obs = [(d, d >= 100) for d in range(0, 200, 10)]
    c = pava(obs)
    assert c.at(50) == 0.0
    assert c.at(150) == 1.0
    assert c.median_lag() == 100


def test_median_lag_is_none_when_never_reached():
    """Reporting "not reached within N days" is a result. Extrapolating a
    median would be an invention."""
    obs = [(d, False) for d in range(0, 300, 10)]
    assert pava(obs).median_lag() is None


def test_pava_handles_ties_in_elapsed_time():
    obs = [(30, True), (30, False), (30, True), (60, True)]
    c = pava(obs)
    first = c.steps[0]
    assert first.delta == 30 and first.n == 3
    assert abs(first.prob - 2 / 3) < 1e-9


def test_pava_of_nothing_is_empty_not_a_crash():
    c = pava([])
    assert c.steps == [] and c.n == 0 and c.median_lag() is None


def test_binned_rates_cover_every_observation():
    obs = [(d, d > 100) for d in (1, 45, 120, 300, 900, 5000)]
    bins = binned_rates(obs)
    assert sum(i.n for _, i in bins) == len(obs)
    assert all(isinstance(i, Interval) for _, i in bins)


def test_flat_reflection_is_visibly_flat():
    """H1's falsification condition: no slope in delta."""
    obs = [(d, d % 2 == 0) for d in range(0, 400, 4)]
    c = pava(obs)
    probs = {round(s.prob, 6) for s in c.steps}
    assert len(probs) == 1, f"expected a flat curve, got steps {probs}"


def test_no_nan_anywhere():
    for i in (wilson(0, 10), wilson(10, 10), wilson(5, 10)):
        assert not any(math.isnan(v) for v in (i.point, i.lo, i.hi))
