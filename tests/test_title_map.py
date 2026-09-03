"""title_map/v1 is frozen. These tests are the freeze.

A change that reddens this file is a contract change and needs a DECISIONS
entry plus measured evidence, not a quick fix here.
"""
import pytest

from titer.corpus.title_map import VERSION, TitleClass, classify


def test_version_is_pinned():
    assert VERSION == "title_map/v1"


@pytest.mark.parametrize("raw,expected", [
    # --- CEO wins over PRESIDENT and CHAIR; order is part of the contract ---
    ("CEO", TitleClass.CEO),
    ("C.E.O.", TitleClass.CEO),
    ("Chief Executive Officer", TitleClass.CEO),
    ("President and CEO", TitleClass.CEO),
    ("Chairman & CEO", TitleClass.CEO),
    ("Chairman, President and Chief Executive Officer", TitleClass.CEO),
    # --- the specific chiefs ---
    ("CFO", TitleClass.CFO),
    ("Chief Financial Officer", TitleClass.CFO),
    ("Principal Financial Officer", TitleClass.CFO),
    ("COO", TitleClass.COO),
    ("Chief Operating Officer", TitleClass.COO),
    ("CTO", TitleClass.CTO_CIO),
    ("Chief Information Officer", TitleClass.CTO_CIO),
    ("General Counsel", TitleClass.GC_LEGAL),
    ("EVP and General Counsel", TitleClass.GC_LEGAL),
    # --- president, and the trap ---
    ("President", TitleClass.PRESIDENT),
    ("Chair", TitleClass.CHAIR),
    ("Chairman of the Board", TitleClass.CHAIR),
    # --- catch-all ---
    ("EVP, Sales", TitleClass.OFFICER_OTHER),
    ("Chief Accounting Officer", TitleClass.OFFICER_OTHER),
    ("Corporate Secretary", TitleClass.OFFICER_OTHER),
    ("Controller", TitleClass.OFFICER_OTHER),
    # --- unmatched is UNKNOWN, never a guess ---
    ("", TitleClass.UNKNOWN),
    ("   ", TitleClass.UNKNOWN),
    (None, TitleClass.UNKNOWN),
    ("Director of Nursing", TitleClass.UNKNOWN),
])
def test_classify(raw, expected):
    assert classify(raw) is expected


@pytest.mark.parametrize("raw", [
    "Vice President",
    "Senior Vice President",
    "Executive Vice President",
    "SVP",
    "EVP",
    "VP Finance",
    "V.P.",
    "Vice-President, Engineering",
])
def test_vice_president_is_never_president(raw):
    """`\\bpresident\\b` matches inside "Vice President". It must not win.

    This was a live defect caught by smoke-testing before any data existed:
    "Senior Vice President" classified as PRESIDENT.
    """
    assert classify(raw) is TitleClass.OFFICER_OTHER


def test_treasurer_is_not_cfo():
    """Distinct offices. Merging them is a judgement that could bias an atom."""
    assert classify("Treasurer") is TitleClass.OFFICER_OTHER
    assert classify("VP and Treasurer") is TitleClass.OFFICER_OTHER


def test_no_model_is_reachable():
    """The module imports stdlib only, by contract."""
    import titer.corpus.title_map as m
    src = open(m.__file__).read()
    for banned in ("import torch", "import openai", "transformers", "httpx", "requests"):
        assert banned not in src


@pytest.mark.parametrize("raw", [
    "Vice Chairman", "Vice Chair", "VICE CHAIRMAN", "Executive Vice Chairman",
    "Vice Chairman of the Board", "Deputy Chairman", "SEVP", "CAO",
])
def test_real_filed_titles_that_were_falling_to_unknown(raw):
    """Measured against the built corpus: these are the actual strings that
    were landing in UNKNOWN. "Vice Chairman" is an office - excluding it from
    CHAIR (correctly) must not drop it out of the taxonomy altogether."""
    assert classify(raw) is TitleClass.OFFICER_OTHER


def test_vice_chair_is_still_not_the_chair():
    assert classify("Vice Chairman") is not TitleClass.CHAIR
    assert classify("Chairman") is TitleClass.CHAIR


def test_see_remarks_stays_unknown():
    """39k rows say 'See Remarks' - a pointer to prose, not a title. Guessing
    what the prose says would put a judged step in the corpus."""
    for s in ("See Remarks", "See remarks.", "SEE REMARKS", "See Remarks below."):
        assert classify(s) is TitleClass.UNKNOWN
