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


def test_repeat_filings_and_near_duplicates_are_not_conflated(quarter_zip):
    """They were, and on the real corpus the conflated number read 0.91 - an
    active insider files dozens of Form 4s a year at one employer. That is not
    near-duplication: signature() already collapses the same fact filed twice.
    """
    import dataclasses
    from datetime import timedelta
    from titer.corpus.splits import duplication_rates

    rows = _rows(quarter_zip)
    assert duplication_rates(rows) == {"repeat_filing_rate": 0.0,
                                       "near_duplicate_rate": 0.0}

    # Same fact filed again: a repeat, NOT a near-duplicate.
    d = duplication_rates(rows + rows)
    assert d["repeat_filing_rate"] == 0.5 and d["near_duplicate_rate"] == 0.0

    # Same relationship re-attested at a later period: a near-duplicate.
    later = [dataclasses.replace(r, accession=r.accession + "-b",
                                 period=r.period + timedelta(days=200))
             for r in rows]
    d2 = duplication_rates(rows + later)
    assert d2["near_duplicate_rate"] == 0.5 and d2["repeat_filing_rate"] == 0.0
    assert near_duplicate_rate(rows + later) == 0.5


def test_signature_bucketing_leaks_people_and_person_bucketing_does_not(population):
    """The old scheme's real defect, and the proof this probe has power.

    Signature bucketing satisfied CONTRACTS 7 literally while letting the same
    executive appear in train and test under different signatures - and
    leak_rate over signatures read exactly 0.0 for any input, because the bucket
    is a pure function of the signature. It verified the implementation, not the
    corpus.
    """
    import dataclasses
    from datetime import timedelta
    multi = []
    for r in population:
        for j in range(3):
            multi.append(dataclasses.replace(
                r, accession=f"{r.accession}-{j}", issuer_cik=f"{r.issuer_cik}{j}",
                period=r.period + timedelta(days=400 * j)))

    sig = split(multi, seed=11, by="signature")
    per = split(multi, seed=11, by="person")

    assert leak_rate(sig.train, sig.test, level="signature") == 0.0   # tautology
    assert leak_rate(sig.train, sig.test, level="person") > 0.5       # the real leak
    assert leak_rate(per.train, per.test, level="person") == 0.0      # closed
    assert leak_rate(per.train, per.train, level="person") == 1.0     # control


def test_a_person_never_straddles_a_split(population):
    import dataclasses
    from datetime import timedelta
    multi = [dataclasses.replace(r, accession=f"{r.accession}-{j}",
                                 issuer_cik=f"{r.issuer_cik}{j}",
                                 period=r.period + timedelta(days=400 * j))
             for r in population for j in range(3)]
    s = split(multi, seed=11)
    buckets = [{r.person_cik for r in b} for b in (s.train, s.hillclimb, s.test)]
    for i, a in enumerate(buckets):
        for b in buckets[i + 1:]:
            assert not (a & b)
