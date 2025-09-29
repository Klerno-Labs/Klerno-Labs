# app / models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import AliasChoices, BaseModel, ConfigDict, EmailStr, Field

# ----------------------------
# Enhanced User and Role System
# ----------------------------


class UserRole(str, Enum):
    """User role hierarchy with specific permissions."""

    OWNER = "owner"  # Full access to everything
    ADMIN = "admin"  # Can see everything, limited editing of sensitive data
    MANAGER = "manager"  # Can see admin page but not edit
    USER = "user"  # Only paid content access


class AccountStatus(str, Enum):
    """Account status for restriction management."""

    ACTIVE = "active"
    TEMPORARILY_BLOCKED = "temp_blocked"
    PERMANENTLY_BLOCKED = "perm_blocked"
    RESTRICTED = "restricted"


class ActionType(str, Enum):
    """Types of admin actions for logging."""

    BLOCK_TEMPORARY = "block_temporary"
    BLOCK_PERMANENT = "block_permanent"
    UNBLOCK = "unblock"
    RESTRICT = "restrict"
    UNRESTRICT = "unrestrict"
    ROLE_CHANGE = "role_change"
    PASSWORD_CHANGE = "password_change"
    CREATE_ADMIN = "create_admin"
    DELETE_ADMIN = "delete_admin"


class User:
    """Compatibility User model: accepts legacy kwargs such as
    `hashed_password`, `is_active`, and `is_admin` while preserving the
    richer internal representation used across the codebase.
    """

    def __init__(
        self,
        id: int | None = None,
        email: str = "",
        password_hash: str | None = None,
        hashed_password: str | None = None,
        role: UserRole | str = UserRole.USER,
        is_active: bool | None = None,
        is_admin: bool | None = None,
        **kwargs,
    ) -> None:
        # Basic validation
        if email and "@" not in email:
            raise ValueError("invalid email")

        self.id = id
        self.email = email

        # map legacy hashed_password -> password_hash
        self.password_hash = password_hash or hashed_password or ""

        # role mapping: legacy is_admin -> admin role
        if isinstance(role, str):
            try:
                self.role = UserRole(role)
            except Exception:
                self.role = UserRole.USER
        else:
            self.role = role

        if is_admin:
            self.role = UserRole.ADMIN

        # map is_active into status and expose legacy boolean
        if is_active is False:
            self.status = AccountStatus.TEMPORARILY_BLOCKED
            self.is_active = False
        else:
            self.status = AccountStatus.ACTIVE
            self.is_active = True

        # legacy is_admin boolean flag
        if is_admin is not None:
            self.is_admin = bool(is_admin)
        else:
            self.is_admin = self.role == UserRole.ADMIN

        # Minimal timestamps / metadata
        self.created_at = kwargs.get("created_at") or datetime.now(UTC)
        self.last_login = kwargs.get("last_login")
        self.blocked_until = kwargs.get("blocked_until")
        self.blocked_reason = kwargs.get("blocked_reason")
        self.blocked_by = kwargs.get("blocked_by")
        self.is_premium = kwargs.get("is_premium", False)

        # MFA fields
        self.totp_secret = kwargs.get("totp_secret")
        self.mfa_enabled = kwargs.get("mfa_enabled", False)
        self.mfa_type = kwargs.get("mfa_type")
        self.recovery_codes = kwargs.get("recovery_codes", [])
        self.has_hardware_key = kwargs.get("has_hardware_key", False)

    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER

    def is_admin_or_higher(self) -> bool:
        return self.role in [UserRole.OWNER, UserRole.ADMIN]

    def is_manager_or_higher(self) -> bool:
        return self.role in [UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER]

    def can_edit_role(self, target_role: UserRole) -> bool:
        if self.role == UserRole.OWNER:
            return True
        elif self.role == UserRole.ADMIN:
            return target_role in [UserRole.MANAGER, UserRole.USER]
        return False

    def can_block_users(self) -> bool:
        return self.role in [UserRole.OWNER, UserRole.ADMIN]

    def can_permanent_block(self) -> bool:
        return self.role == UserRole.OWNER

    def is_blocked(self) -> bool:
        if self.status == AccountStatus.PERMANENTLY_BLOCKED:
            return True
        if self.status == AccountStatus.TEMPORARILY_BLOCKED and self.blocked_until:
            return datetime.now(UTC) < self.blocked_until
        return False


@dataclass
class AdminAction:
    """Log entry for admin actions."""

    id: int | None = None
    admin_email: str = ""
    target_email: str = ""
    action: ActionType = ActionType.ROLE_CHANGE
    reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    additional_data: str | None = None  # JSON string for extra data


class UserCreateRequest(BaseModel):
    """Request model for creating new users."""

    email: EmailStr
    password: str
    role: UserRole = UserRole.USER
    is_premium: bool = False


class UserUpdateRequest(BaseModel):
    """Request model for updating users."""

    role: UserRole | None = None
    is_premium: bool | None = None
    status: AccountStatus | None = None


class BlockUserRequest(BaseModel):
    """Request model for blocking users."""

    target_email: EmailStr
    reason: str = Field(min_length=1, max_length=500)
    duration_hours: int | None = None  # None for permanent block


class AdminActionResponse(BaseModel):
    """Response model for admin actions."""

    success: bool
    message: str
    action_id: int | None = None


# ----------------------------
# Dataclass used in tests / core logic
# ----------------------------
class Transaction:
    """Compatibility Transaction model that accepts legacy kwargs used in
    tests (id, user_id, currency, status) while still providing the
    common attributes used elsewhere (tx_id, amount, symbol, etc.).
    """

    def __init__(
        self,
        id: int | None = None,
        tx_id: str | None = None,
        user_id: int | None = None,
        amount: Decimal | float | str = Decimal("0"),
        currency: str | None = None,
        status: str | None = None,
        **kwargs,
    ) -> None:
        # map id -> tx_id if present
        self.id = id
        self.tx_id = tx_id or (str(id) if id is not None else "")
        self.user_id = user_id

        # Parse amount; if parsing fails raise ValueError so callers/tests
        # receive a clear error. Negative amounts are allowed for native
        # blockchain currency (defaulting to XRP) for outgoing txs, but
        # for fiat/explicit currency values we treat negatives as invalid
        # at the model level (some unit tests expect a ValueError).
        try:
            self.amount = Decimal(str(amount))
        except Exception as e:
            raise ValueError("invalid amount") from e

        # Decide whether negative amounts are acceptable. Tests expect that
        # negative values are allowed for the default/native currency (XRP)
        # but are rejected for explicit fiat currencies like 'USD'. We also
        # allow negative amounts for explicit 'XRP' symbol.
        symbol = currency or kwargs.get("symbol", "XRP")
        if self.amount < 0:
            # Allow negative only for XRP (or when chain explicitly is XRP)
            chain = kwargs.get("chain")
            if not (
                str(symbol).upper() == "XRP" or (chain and str(chain).upper() == "XRP")
            ):
                raise ValueError("amount must be non-negative for fiat currencies")

        # currency maps to symbol
        self.symbol = currency or kwargs.get("symbol", "XRP")
        self.currency = currency or self.symbol

        self.status = status or kwargs.get("status")
        self.timestamp = kwargs.get("timestamp") or datetime.now(UTC)

        self.chain = kwargs.get("chain", "XRP")
        self.from_addr = kwargs.get("from_addr") or kwargs.get("from_address")
        self.to_addr = kwargs.get("to_addr") or kwargs.get("to_address")
        self.direction = kwargs.get("direction", "out")
        self.fee = Decimal(str(kwargs.get("fee", "0")))
        self.memo = kwargs.get("memo")
        self.notes = kwargs.get("notes")
        self.tags = kwargs.get("tags", [])
        self.is_internal = kwargs.get("is_internal", False)

    @property
    def from_address(self) -> str | None:
        return self.from_addr

    @property
    def to_address(self) -> str | None:
        return self.to_addr


# ----------------------------
# Pydantic models for API I / O
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

    # Canonical fields are from_addr / to_addr; also accept from_address / to_address
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

    # Accept arbitrary kwargs at construction time to allow legacy dicts and
    # runtime coercion by pydantic without confusing static type checkers.
    def __init__(self, *args, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)


class ReportRequest(BaseModel):
    """Input model for generating reports / exports."""

    model_config = ConfigDict(populate_by_name=True)

    address: str | None = None
    chain: str | None = "XRP"
    start: datetime | None = None
    end: datetime | None = None
    min_amount: Decimal | None = None
    max_amount: Decimal | None = None
    wallet_addresses: list[str] = Field(
        default_factory=list
    )  # <─ used in /report / csv


class ReportSummary(BaseModel):
    """
    Output model for summary endpoints / exports.
    Flexible defaults so reporter code can set more fields if needed.
    """

    model_config = ConfigDict(
        extra="allow"
    )  # tolerate extra fields if reporter adds them

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

    # Backwards-compatible fields expected by older tests/code. Use distinct
    # alias fields so pydantic/mypy do not see duplicate class attributes.
    legacy_total_transactions: int | None = Field(
        default=None, alias="total_transactions"
    )
    legacy_total_volume: Decimal | None = Field(default=None, alias="total_volume")
    legacy_high_risk_count: int | None = Field(default=None, alias="high_risk_count")

    def model_post_init(self, __context: Any | None = None) -> None:  # pydantic v2 hook
        """Sync legacy alias fields into canonical fields after parsing.
        This keeps runtime behavior compatible with older tests and code while
        avoiding duplicate attribute definitions that confuse static analysis.
        """
        # If legacy fields were provided, map them into the canonical counters.
        if self.legacy_total_transactions is not None:
            # Historically tests used total_transactions as the primary count; map
            # that to count_in for backwards compatibility.
            self.count_in = int(self.legacy_total_transactions)
        if self.legacy_total_volume is not None:
            self.total_out = Decimal(self.legacy_total_volume)
        # Only populate the categories high_risk_count slot when the caller
        # did not provide their own categories dict AND the legacy value is
        # a positive count. Tests expect an explicitly supplied categories
        # dict (even if empty) to remain unchanged, and a zero legacy
        # high_risk_count should not inject a key.
        if (
            self.legacy_high_risk_count is not None
            and not self.categories
            and int(self.legacy_high_risk_count) > 0
        ):
            self.categories.setdefault("high_risk_count", 0)
            self.categories["high_risk_count"] = int(self.legacy_high_risk_count)

    # Backwards-compatible attribute accessors expected by older tests/code.
    @property
    def total_transactions(self) -> int:
        # Prefer explicit legacy value if provided, otherwise fall back to count_in
        if self.legacy_total_transactions is not None:
            return int(self.legacy_total_transactions)
        return int(self.count_in)

    @property
    def total_volume(self) -> Decimal:
        if self.legacy_total_volume is not None:
            return Decimal(self.legacy_total_volume)
        return Decimal(self.total_out)

    @property
    def high_risk_count(self) -> int:
        if self.legacy_high_risk_count is not None:
            return int(self.legacy_high_risk_count)
        return int(self.categories.get("high_risk_count", 0))
