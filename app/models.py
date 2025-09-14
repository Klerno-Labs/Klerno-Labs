# app/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


# ----------------------------
# Dataclass used in tests / core logic
# ----------------------------
@dataclass
class Transaction:
    # Fields your tests pass in
    tx_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    chain: str = "XRP"
    from_addr: str | None = None
    to_addr: str | None = None
    amount: Decimal = Decimal("0")
    symbol: str = "XRP"
    direction: str = "out"

    # Common extras used by your code
    fee: Decimal = Decimal("0")
    memo: str | None = ""
    notes: str | None = ""  # <─ added so emails/CSV don’t break
    tags: list[str] = field(default_factory=list)
    is_internal: bool = False

    # Back-compat for code that expects from_address/to_address
    @property
    def from_address(self) -> str | None:
        return self.from_addr

    @property
    def to_address(self) -> str | None:
        return self.to_addr


# ----------------------------
# Pydantic models for API I/O
# ----------------------------
class TaggedTransaction(BaseModel):
    """
    Transaction + tagging results for API responses.
    Accepts inputs with either 'from_addr'/'to_addr' or 'from_address'/'to_address'.
    Also accepts old 'score'/'flags' but serializes as 'risk_score'/'risk_flags'.
    """

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    # Base tx fields
    tx_id: str
    timestamp: datetime
    chain: str = "XRP"

    # Canonical fields are from_addr/to_addr; also accept from_address/to_address
    from_addr: str | None = Field(default=None, alias="from_address")
    to_addr: str | None = Field(default=None, alias="to_address")

    amount: Decimal
    symbol: str = "XRP"
    direction: str

    fee: Decimal = Decimal("0")
    memo: str | None = None
    notes: str | None = None
    tags: list[str] = Field(default_factory=list)
    is_internal: bool = False

    # Tagging outputs
    category: str | None = None

    # Accept both 'risk_score' and legacy 'score' on input; serialize as 'risk_score'
    risk_score: float | None = Field(
        default=None, validation_alias=AliasChoices("risk_score", "score")
    )
    # Accept both 'risk_flags' and legacy 'flags' on input; serialize as 'risk_flags'
    risk_flags: list[str] = Field(
        default_factory=list, validation_alias=AliasChoices("risk_flags", "flags")
    )

    # Convenience accessors so code can read .from_address/.to_address or .score/.flags too
    @property
    def from_address(self) -> str | None:
        return self.from_addr

    @property
    def to_address(self) -> str | None:
        return self.to_addr

    @property
    def score(self) -> float | None:
        return self.risk_score

    @property
    def flags(self) -> list[str]:
        return self.risk_flags


class ReportRequest(BaseModel):
    """Input model for generating reports/exports."""

    model_config = ConfigDict(populate_by_name=True)

    address: str | None = None
    chain: str | None = "XRP"
    start: datetime | None = None
    end: datetime | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    wallet_addresses: list[str] = Field(default_factory=list)  # <─ used in /report/csv


class ReportSummary(BaseModel):
    """
    Output model for summary endpoints/exports.
    Flexible defaults so reporter code can set more fields if needed.
    """

    model_config = ConfigDict(extra="allow")  # tolerate extra fields if reporter adds them

    address: str | None = None
    chain: str | None = "XRP"
    start: datetime | None = None
    end: datetime | None = None

    # Totals & counts
    count_in: int = 0
    count_out: int = 0
    total_in: Decimal = Decimal("0")
    total_out: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    net: Decimal = Decimal("0")

    # Optional breakdowns
    categories: dict[str, int] = Field(default_factory=dict)
