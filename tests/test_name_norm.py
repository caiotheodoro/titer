"""name_norm/v1 is frozen. Over-normalizing manufactures false merges that
never happened; under-normalizing hides real ones. Both directions are tested.
"""
import pytest

from titer.corpus.name_norm import VERSION, normalize


def test_version_is_pinned():
    assert VERSION == "name_norm/v1"


def test_filing_order_and_provider_order_collapse():
    """SEC files "LAST FIRST MIDDLE"; providers return "First Last"."""
    assert normalize("SMITH JOHN A") == normalize("John A. Smith")
    assert normalize("Smith, John A., Jr.") == normalize("John A Smith")


@pytest.mark.parametrize("raw", ["", None, "   ", ",,,"])
def test_empty_is_empty(raw):
    assert normalize(raw) == ""


def test_generational_and_professional_suffixes_are_dropped():
    base = normalize("Jane Doe")
    for suffix in ["Jr.", "Sr.", "III", "PhD", "M.D.", "CPA", "Esq."]:
        assert normalize(f"Jane Doe {suffix}") == base


def test_initials_are_kept():
    """Dropping initials would merge distinct people and inflate collisions."""
    assert normalize("John A Smith") != normalize("John Smith")
    assert normalize("John A Smith") != normalize("John B Smith")


def test_distinct_people_stay_distinct():
    assert normalize("John Smith") != normalize("Jane Smith")
    assert normalize("Robert Lee") != normalize("Roberta Lee")


def test_nicknames_are_not_unified():
    """Deliberate. Unifying Bob/Robert is a guess, and a guess here becomes a
    manufactured false merge in the published rate."""
    assert normalize("Bob Smith") != normalize("Robert Smith")


def test_presented_name_drops_initials_and_strict_keeps_them():
    """Two normalizations on purpose. Measured over the real corpus: keeping
    initials gives 1.24% colliding names and max degree 7; dropping them gives
    5.45% and max degree 28. The first is right for resolution (never invent a
    merge), the second for difficulty (a provider is not handed the initial).
    See docs/DECISIONS.md D027."""
    from titer.corpus.name_norm import normalize_presented

    assert normalize("John A Smith") != normalize("John Smith")
    assert normalize_presented("John A Smith") == normalize_presented("John Smith")


def test_presented_name_still_separates_different_people():
    from titer.corpus.name_norm import normalize_presented
    assert normalize_presented("John Smith") != normalize_presented("Jane Smith")
    assert normalize_presented("John Smith") != normalize_presented("John Smyth")


def test_presented_name_drops_suffixes_too():
    from titer.corpus.name_norm import normalize_presented
    assert normalize_presented("SMITH JOHN A JR") == normalize_presented("John Smith")
