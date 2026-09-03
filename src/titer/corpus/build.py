"""Join REPORTINGOWNER to SUBMISSION and apply the inclusion rules.

Every rule that drops a row increments a counter, and `ExclusionCounts.reconcile`
fails the build if the counters do not account for every input row. An
unpublished exclusion is an unstated coverage gap.

Address fields present in the source (`RPTOWNER_STREET1`, `_STREET2`, `_CITY`,
`_STATE`, `_ZIPCODE`) are dropped here, at ingest, before an AttestedTuple
exists. Not at publication time. See docs/ETHICS.md section 2.1.
"""
from __future__ import annotations

import csv
import io
import zipfile
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from titer.corpus.schema import (
    AttestedTuple,
    ExclusionCounts,
    RoleClass,
    parse_relationship,
)
from titer.corpus.title_map import TitleClass, classify

# Fields we refuse to carry past ingest, even though the source provides them.
CONTACT_FIELDS = frozenset({
    "RPTOWNER_STREET1", "RPTOWNER_STREET2", "RPTOWNER_CITY",
    "RPTOWNER_STATE", "RPTOWNER_ZIPCODE", "RPTOWNER_STATE_DESC",
})

# The corpus starts when mandatory electronic Section 16 filing did.
MIN_YEAR, MIN_QUARTER = 2003, 3

_DATE_FORMATS = ("%d-%b-%Y", "%Y-%m-%d", "%m/%d/%Y", "%d%b%Y", "%Y%m%d")


def parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    s = raw.strip()
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _read_tsv(zf: zipfile.ZipFile, name: str) -> Iterator[dict[str, str]]:
    candidates = [n for n in zf.namelist() if n.upper().endswith(name.upper())]
    if not candidates:
        raise FileNotFoundError(f"{name} not in archive: {zf.namelist()}")
    with zf.open(candidates[0]) as fh:
        text = io.TextIOWrapper(fh, encoding="utf-8", errors="replace", newline="")
        for row in csv.DictReader(text, delimiter="\t"):
            yield row


def _quarter_of(d: date) -> tuple[int, int]:
    return d.year, (d.month - 1) // 3 + 1


def build_quarter(zip_path: Path, counts: ExclusionCounts) -> list[AttestedTuple]:
    """Build the attested tuples for one quarterly archive."""
    with zipfile.ZipFile(zip_path) as zf:
        submissions: dict[str, dict[str, str]] = {}
        for row in _read_tsv(zf, "SUBMISSION.tsv"):
            acc = (row.get("ACCESSION_NUMBER") or "").strip()
            if acc:
                submissions[acc] = row
        owners = list(_read_tsv(zf, "REPORTINGOWNER.tsv"))

    out: list[AttestedTuple] = []
    for row in owners:
        counts.input_rows += 1
        # Drop contact fields immediately. Nothing downstream can reach them.
        for f in CONTACT_FIELDS:
            row.pop(f, None)

        acc = (row.get("ACCESSION_NUMBER") or "").strip()
        sub = submissions.get(acc)
        if sub is None:
            counts.unjoined_accession += 1
            continue

        roles = parse_relationship(row.get("RPTOWNER_RELATIONSHIP"))
        if not roles and (row.get("RPTOWNER_RELATIONSHIP") or "").strip():
            counts.unknown_relationship_token += 1
        # Rule 1: officers and directors only. This is also what removes the
        # ~5-8% of reporting owners that are legal entities, not humans.
        if not (RoleClass.OFFICER in roles or RoleClass.DIRECTOR in roles):
            if roles == frozenset({RoleClass.TEN_PERCENT_OWNER}):
                counts.entity_not_human += 1
            else:
                counts.no_officer_or_director += 1
            continue

        # Rule 3: person CIK non-empty and numeric.
        cik = (row.get("RPTOWNERCIK") or "").strip()
        if not cik or not cik.isdigit():
            counts.bad_person_cik += 1
            continue

        # Rule 2: dates parse and period <= filed.
        period = parse_date(sub.get("PERIOD_OF_REPORT"))
        filed = parse_date(sub.get("FILING_DATE"))
        if period is None or filed is None:
            counts.unparseable_date += 1
            continue
        if period > filed:
            counts.period_after_filed += 1
            continue

        # Rule 4: 2003q3 or later.
        y, q = _quarter_of(filed)
        if (y, q) < (MIN_YEAR, MIN_QUARTER):
            counts.quarter_before_2003q3 += 1
            continue

        title_raw = (row.get("RPTOWNER_TITLE") or "").strip()
        title_class = classify(title_raw)
        if title_class is TitleClass.UNKNOWN:
            counts.title_unknown += 1  # counted, not excluded

        out.append(AttestedTuple(
            accession=acc,
            person_cik=cik,
            person_name_raw=(row.get("RPTOWNERNAME") or "").strip(),
            issuer_cik=(sub.get("ISSUERCIK") or "").strip(),
            issuer_name_raw=(sub.get("ISSUERNAME") or "").strip(),
            issuer_ticker=(sub.get("ISSUERTRADINGSYMBOL") or "").strip(),
            role_class=roles,
            title_raw=title_raw,
            title_class=title_class,
            period=period,
            filed=filed,
        ))
        counts.kept += 1
    return out
