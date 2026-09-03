"""The common provider surface, and the spend ledger.

Every arm - paid API or free web floor - implements `Provider`. The environment
and the measurement scripts never talk to a vendor SDK directly, so adding a
provider cannot change the scoring path.

Cost is **recorded by the adapter, never estimated by the caller.** An estimated
price would make the entire value-of-information claim circular: the policy
would be optimising against our guess about the vendor rather than the vendor.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Protocol, runtime_checkable

# Fields that must never reach disk. Stripped at ingest, not at publication.
# docs/ETHICS.md section 2.1.
CONTACT_KEYS = frozenset({
    "email", "work_email", "personal_email", "emails",
    "phone", "mobile_phone", "phone_number", "phones",
    "address", "street", "street1", "street2", "city", "postal_code", "zip",
    "linkedin_url", "linkedin", "twitter", "x_url", "github_url", "facebook",
    "social", "socials", "profile_url", "url", "urls", "evidence_links",
    "date_of_birth", "dob", "age",
})


@dataclass(frozen=True, slots=True)
class RawAnswer:
    """What a provider said, before any resolution to CIKs.

    Names, not identifiers: providers do not know about CIKs. Resolution happens
    once, deterministically, in `titer.oracle.resolve`, after this object exists.
    """

    person_name: str | None = None
    employer_name: str | None = None
    title_text: str | None = None
    confidence: float = 0.0
    abstained: bool = False
    employment_start: date | None = None
    employment_end: date | None = None
    rank: int | None = None
    resolution_source: str | None = None
    identity_verified: bool | None = None
    last_seen: date | None = None


@dataclass(frozen=True, slots=True)
class Spend:
    """What one call actually cost, as reported by the provider."""

    usd: float
    units: float = 0.0
    unit_name: str = ""

    def __add__(self, other: "Spend") -> "Spend":
        return Spend(self.usd + other.usd, self.units + other.units,
                     self.unit_name or other.unit_name)


ZERO = Spend(0.0)


@dataclass
class Ledger:
    """Running spend, with a hard ceiling that raises rather than overspending."""

    budget_usd: float
    spent: Spend = field(default_factory=lambda: ZERO)
    calls: int = 0

    @property
    def remaining_usd(self) -> float:
        return self.budget_usd - self.spent.usd

    def can_afford(self, usd: float) -> bool:
        return usd <= self.remaining_usd + 1e-12

    def charge(self, spend: Spend) -> None:
        if not self.can_afford(spend.usd):
            raise BudgetExceeded(
                f"call costs ${spend.usd:.4f} but only ${self.remaining_usd:.4f} remains "
                f"of a ${self.budget_usd:.2f} budget after {self.calls} calls"
            )
        self.spent = self.spent + spend
        self.calls += 1


class BudgetExceeded(RuntimeError):
    """Raised rather than silently overspending real money."""


@dataclass(frozen=True, slots=True)
class Call:
    """One priced action available to a policy."""

    provider: str
    action: str
    list_price_usd: float


@runtime_checkable
class Provider(Protocol):
    name: str

    def actions(self) -> list[Call]:
        """The priced actions this provider exposes."""

    def query(self, action: str, prompt: str, **kwargs) -> tuple[list[RawAnswer], Spend]:
        """Run one action. Returns candidate answers and what it cost."""
