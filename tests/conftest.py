"""Synthetic quarterly archives with the real SEC column names.

Column names and the TSV member names are taken from a live 2025Q1 archive, so
a fixture that passes here exercises the same code path real data will. The
rows are constructed to hit every exclusion counter at least once - a counter
that is never exercised is a counter that could silently be wrong.
"""
from __future__ import annotations

import io
import zipfile
from pathlib import Path

import pytest

SUBMISSION_COLS = [
    "ACCESSION_NUMBER", "FILING_DATE", "PERIOD_OF_REPORT", "DATE_OF_ORIG_SUB",
    "NO_SECURITIES_OWNED", "NOT_SUBJECT_SEC16", "FORM3_HOLDINGS_REPORTED",
    "FORM4_TRANS_REPORTED", "DOCUMENT_TYPE", "ISSUERCIK", "ISSUERNAME",
    "ISSUERTRADINGSYMBOL", "REMARKS", "AFF10B5ONE",
]
OWNER_COLS = [
    "ACCESSION_NUMBER", "RPTOWNERCIK", "RPTOWNERNAME", "RPTOWNER_RELATIONSHIP",
    "RPTOWNER_TITLE", "RPTOWNER_TXT", "RPTOWNER_STREET1", "RPTOWNER_STREET2",
    "RPTOWNER_CITY", "RPTOWNER_STATE", "RPTOWNER_ZIPCODE", "RPTOWNER_STATE_DESC",
    "FILE_NUMBER",
]


def _sub(acc, filed, period, icik, iname, tic="TST"):
    return {**{c: "" for c in SUBMISSION_COLS}, "ACCESSION_NUMBER": acc,
            "FILING_DATE": filed, "PERIOD_OF_REPORT": period, "DOCUMENT_TYPE": "4",
            "ISSUERCIK": icik, "ISSUERNAME": iname, "ISSUERTRADINGSYMBOL": tic}


def _own(acc, cik, name, rel, title=""):
    # Address fields are populated on purpose: the ingest must drop them.
    return {**{c: "" for c in OWNER_COLS}, "ACCESSION_NUMBER": acc,
            "RPTOWNERCIK": cik, "RPTOWNERNAME": name, "RPTOWNER_RELATIONSHIP": rel,
            "RPTOWNER_TITLE": title,
            "RPTOWNER_STREET1": "1 Main St", "RPTOWNER_STREET2": "Suite 5",
            "RPTOWNER_CITY": "Springfield", "RPTOWNER_STATE": "IL",
            "RPTOWNER_ZIPCODE": "62701", "RPTOWNER_STATE_DESC": "ILLINOIS"}


SUBMISSIONS = [
    _sub("0001-25-000001", "15-FEB-2025", "13-FEB-2025", "320193", "APPLE INC", "AAPL"),
    _sub("0001-25-000002", "20-FEB-2025", "18-FEB-2025", "789019", "MICROSOFT CORP", "MSFT"),
    _sub("0001-25-000003", "21-FEB-2025", "19-FEB-2025", "320193", "APPLE INC", "AAPL"),
    _sub("0001-25-000004", "22-FEB-2025", "20-FEB-2025", "111111", "ACME CORP", "ACME"),
    _sub("0001-25-000005", "notadate", "20-FEB-2025", "111111", "ACME CORP", "ACME"),
    _sub("0001-25-000006", "01-FEB-2025", "28-FEB-2025", "111111", "ACME CORP", "ACME"),
    _sub("0001-03-000007", "15-FEB-2003", "13-FEB-2003", "111111", "ACME CORP", "ACME"),
    _sub("0001-25-000008", "23-FEB-2025", "21-FEB-2025", "222222", "BETA LLC", "BETA"),
]

OWNERS = [
    # -- kept --
    _own("0001-25-000001", "1000001", "SMITH JOHN A", "Officer", "Chief Executive Officer"),
    _own("0001-25-000002", "1000002", "SMITH JOHN A", "Director,Officer", "CFO"),
    _own("0001-25-000003", "1000003", "DOE JANE", "Director", ""),
    # same name AND same issuer as 1000001 -> contamination suspect
    _own("0001-25-000003", "1000009", "SMITH JOHN A", "Officer", "President"),
    # -- excluded, one per counter --
    _own("0001-25-000004", "1000004", "BLACKROCK INC", "TenPercentOwner", ""),
    _own("0001-25-000004", "1000005", "SOME TRUST", "Other", ""),
    _own("0001-25-000005", "1000006", "BAD DATE", "Officer", "CEO"),
    _own("0001-25-000006", "1000007", "PERIOD AFTER FILED", "Officer", "CEO"),
    _own("0001-03-000007", "1000008", "TOO EARLY", "Officer", "CEO"),
    _own("0001-25-000008", "NOTANUMBER", "BAD CIK", "Officer", "CEO"),
    _own("0001-25-999999", "1000010", "NO SUBMISSION", "Officer", "CEO"),
]


def _tsv(rows, cols) -> bytes:
    buf = io.StringIO()
    buf.write("\t".join(cols) + "\n")
    for r in rows:
        buf.write("\t".join(str(r.get(c, "")) for c in cols) + "\n")
    return buf.getvalue().encode()


@pytest.fixture
def quarter_zip(tmp_path: Path) -> Path:
    p = tmp_path / "2025q1_form345.zip"
    with zipfile.ZipFile(p, "w") as zf:
        zf.writestr("SUBMISSION.tsv", _tsv(SUBMISSIONS, SUBMISSION_COLS))
        zf.writestr("REPORTINGOWNER.tsv", _tsv(OWNERS, OWNER_COLS))
        zf.writestr("FORM_345_readme.htm", b"<html>readme</html>")
    return p


@pytest.fixture
def population():
    """A few hundred distinct attested facts.

    The zip fixture has only four kept rows, i.e. four signatures, which is too
    few to split meaningfully - and a split test against it passes trivially
    because a bucket comes back empty. That trivial pass is exactly what this
    fixture exists to prevent.
    """
    from datetime import date, timedelta

    from titer.corpus.schema import AttestedTuple, RoleClass
    from titer.corpus.title_map import TitleClass

    titles = list(TitleClass)
    rows = []
    for i in range(400):
        rows.append(AttestedTuple(
            accession=f"0001-25-{i:06d}",
            person_cik=str(2_000_000 + i),
            person_name_raw=f"PERSON{i:04d} TEST",
            issuer_cik=str(500_000 + (i % 37)),
            issuer_name_raw=f"ISSUER {i % 37}",
            issuer_ticker=f"T{i % 37:02d}",
            role_class=frozenset({RoleClass.OFFICER if i % 2 else RoleClass.DIRECTOR}),
            title_raw="Chief Executive Officer",
            title_class=titles[i % len(titles)],
            period=date(2020, 1, 1) + timedelta(days=i * 3),
            filed=date(2020, 1, 5) + timedelta(days=i * 3),
        ))
    return rows
