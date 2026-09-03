"""The attested tuple, and the exclusion accounting that must reconcile.

Field names mirror the SEC Insider Transactions Data Sets exactly, so that a
reader can trace any value back to a column in a published file.

Note what is absent. `REPORTINGOWNER.tsv` ships `RPTOWNER_STREET1`,
`RPTOWNER_STREET2`, `RPTOWNER_CITY`, `RPTOWNER_STATE` and `RPTOWNER_ZIPCODE`.
None of them appear here, and `build.py` drops them before a row is ever
constructed. See docs/ETHICS.md section 2.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from titer.corpus.name_norm import normalize
from titer.corpus.title_map import TitleClass

CONTRACTS_VERSION = "contracts/v1"


class RoleClass(str, Enum):
    DIRECTOR = "DIRECTOR"
    OFFICER = "OFFICER"
    TEN_PERCENT_OWNER = "TEN_PERCENT_OWNER"
    OTHER = "OTHER"


_RELATIONSHIP_MAP = {
    "director": RoleClass.DIRECTOR,
    "officer": RoleClass.OFFICER,
    "tenpercentowner": RoleClass.TEN_PERCENT_OWNER,
    "other": RoleClass.OTHER,
}


def parse_relationship(raw: str | None) -> frozenset[RoleClass]:
    """`RPTOWNER_RELATIONSHIP` is a comma-joined closed set. We parse it and
    never rewrite it. An unrecognised token is dropped and counted, not guessed.
    """
    if not raw:
        return frozenset()
    out = set()
    for tok in raw.split(","):
        key = tok.strip().lower().replace(" ", "").replace("-", "")
        if key in _RELATIONSHIP_MAP:
            out.add(_RELATIONSHIP_MAP[key])
    return frozenset(out)


@dataclass(frozen=True, slots=True)
class AttestedTuple:
    """One row of Tier A ground truth. See CONTRACTS.md section 2."""

    accession: str
    person_cik: str
    person_name_raw: str
    issuer_cik: str
    issuer_name_raw: str
    issuer_ticker: str
    role_class: frozenset[RoleClass]
    title_raw: str
    title_class: TitleClass
    period: date
    filed: date

    @property
    def person_name_norm(self) -> str:
        return normalize(self.person_name_raw)

    def signature(self) -> str:
        """SHA-256 over sorted ground-truth fields. CONTRACTS.md section 7.

        Deliberately excludes the accession number: two filings reporting the
        same person in the same role at the same issuer on the same date are
        the same *task*, and must not land on opposite sides of a split.
        """
        parts = [
            self.person_cik,
            self.issuer_cik,
            ",".join(sorted(r.value for r in self.role_class)),
            self.title_class.value,
            self.period.isoformat(),
        ]
        return hashlib.sha256("|".join(sorted(parts)).encode()).hexdigest()

    def name_hash(self, salt: str) -> str:
        """Salted hash of the normalized name. This, not the name, is published."""
        return hashlib.sha256((salt + "|" + self.person_name_norm).encode()).hexdigest()


@dataclass
class ExclusionCounts:
    """Every rule that drops a row increments a counter here.

    `reconcile` fails the build if the counters do not account for every input
    row. A row cannot be dropped silently. See CONTRACTS.md section 2.1.
    """

    input_rows: int = 0
    kept: int = 0
    no_officer_or_director: int = 0
    entity_not_human: int = 0
    bad_person_cik: int = 0
    unparseable_date: int = 0
    period_after_filed: int = 0
    quarter_before_2003q3: int = 0
    unjoined_accession: int = 0
    unknown_relationship_token: int = 0
    title_unknown: int = 0  # counted, NOT excluded - see CONTRACTS 3.2
    detail: dict[str, int] = field(default_factory=dict)

    @property
    def dropped(self) -> int:
        return (
            self.no_officer_or_director
            + self.entity_not_human
            + self.bad_person_cik
            + self.unparseable_date
            + self.period_after_filed
            + self.quarter_before_2003q3
            + self.unjoined_accession
        )

    def reconcile(self) -> None:
        if self.kept + self.dropped != self.input_rows:
            raise AssertionError(
                "exclusion counters do not reconcile: "
                f"kept={self.kept} + dropped={self.dropped} != input={self.input_rows}. "
                "A row was dropped without being counted, which is a defect: "
                "docs/COVERAGE.md publishes these rates and an unpublished "
                "exclusion is an unstated coverage gap."
            )

    def as_dict(self) -> dict[str, int]:
        d = {k: v for k, v in self.__dict__.items() if isinstance(v, int)}
        d["dropped"] = self.dropped
        return d
