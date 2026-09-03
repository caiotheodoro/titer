import dataclasses

from titer.corpus.build import build_quarter
from titer.corpus.schema import ExclusionCounts
from titer.corpus.splits import leak_rate, near_duplicate_rate, split


def _rows(quarter_zip):
    return build_quarter(quarter_zip, ExclusionCounts())


def test_no_split_is_empty(population):
    """Guards every test below. A split test against an empty bucket passes
    trivially, which is how a broken leak probe survives a green suite."""
    s = split(population, seed=11)
    for name, n in s.counts().items():
        assert n > 0, f"{name} bucket is empty; downstream assertions are vacuous"


def test_leak_probe_reads_zero_on_a_clean_split(population):
    s = split(population, seed=11)
    assert leak_rate(s.train, s.test) == 0.0
    assert leak_rate(s.train, s.hillclimb) == 0.0


def test_leak_probe_reads_one_on_a_deliberate_leak(population):
    """A probe that cannot detect an intentional leak is not evidence of
    anything. CONTRACTS.md section 7."""
    s = split(population, seed=11)
    assert leak_rate(s.train, s.train) == 1.0


def test_leak_probe_detects_a_partial_leak(population):
    s = split(population, seed=11)
    poisoned = list(s.test) + list(s.train[:len(s.test)])
    rate = leak_rate(s.train, poisoned)
    assert 0.0 < rate < 1.0


def test_split_is_deterministic_across_processes(population):
    """Python's builtin hash is salted per process; ours must not be."""
    a, b = split(population, seed=11), split(population, seed=11)
    assert a.counts() == b.counts()
    assert [r.accession for r in a.test] == [r.accession for r in b.test]


def test_different_seed_gives_a_different_split(population):
    assert split(population, seed=11).counts() != split(population, seed=999).counts()


def test_split_proportions_are_roughly_as_requested(population):
    s = split(population, seed=11, hillclimb_pct=15, test_pct=15)
    n = len(population)
    assert 0.08 < len(s.test) / n < 0.24
    assert 0.08 < len(s.hillclimb) / n < 0.24


def test_same_fact_filed_twice_never_straddles_a_split(quarter_zip):
    """Splitting by row instead of signature would leak the answer."""
    rows = _rows(quarter_zip)
    twins = [dataclasses.replace(r, accession=f"dup-{i}") for i, r in enumerate(rows)]
    s = split(rows + twins, seed=11)
    for bucket in (s.train, s.hillclimb, s.test):
        sigs = {r.signature() for r in bucket}
        others = set()
        for other in (s.train, s.hillclimb, s.test):
            if other is not bucket:
                others |= {r.signature() for r in other}
        assert not (sigs & others)


def test_near_duplicate_rate_is_measured_not_assumed(quarter_zip):
    rows = _rows(quarter_zip)
    assert near_duplicate_rate(rows) == 0.0
    assert near_duplicate_rate(rows + rows) == 0.5
