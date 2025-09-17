# app/models.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Dict
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict, AliasChoices, EmailStr


# ----------------------------
# Enhanced User and Role System
# ----------------------------
class UserRole(str, Enum):
    """User role hierarchy with specific permissions."""
    OWNER = "owner"           # Full access to everything
    ADMIN = "admin"           # Can see everything, limited editing of sensitive data
    MANAGER = "manager"       # Can see admin page but not edit
    USER = "user"             # Only paid content access

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

@dataclass
class User:
    """Enhanced user model with role-based access control."""
    id: Optional[int] = None
    email: str = ""
    password_hash: str = ""
    role: UserRole = UserRole.USER
    status: AccountStatus = AccountStatus.ACTIVE
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_login: Optional[datetime] = None
    blocked_until: Optional[datetime] = None  # For temporary blocks
    blocked_reason: Optional[str] = None
    blocked_by: Optional[str] = None
    is_premium: bool = False
    
    # MFA fields
    totp_secret: Optional[str] = None  # Encrypted TOTP seed
    mfa_enabled: bool = False
    mfa_type: Optional[str] = None  # 'totp', 'webauthn', etc.
    recovery_codes: Optional[List[str]] = field(default_factory=list)
    has_hardware_key: bool = False

    def is_owner(self) -> bool:
        return self.role == UserRole.OWNER
    
    def is_admin_or_higher(self) -> bool:
        return self.role in [UserRole.OWNER, UserRole.ADMIN]
    
    def is_manager_or_higher(self) -> bool:
        return self.role in [UserRole.OWNER, UserRole.ADMIN, UserRole.MANAGER]
    
    def can_edit_role(self, target_role: UserRole) -> bool:
        """Check if user can edit a specific role."""
        if self.role == UserRole.OWNER:
            return True
        elif self.role == UserRole.ADMIN:
            return target_role in [UserRole.MANAGER, UserRole.USER]
        return False
    
    def can_block_users(self) -> bool:
        """Check if user can block other users."""
        return self.role in [UserRole.OWNER, UserRole.ADMIN]
    
    def can_permanent_block(self) -> bool:
        """Check if user can permanently block users."""
        return self.role == UserRole.OWNER
    
    def is_blocked(self) -> bool:
        """Check if user is currently blocked."""
        if self.status == AccountStatus.PERMANENTLY_BLOCKED:
            return True
        if self.status == AccountStatus.TEMPORARILY_BLOCKED and self.blocked_until:
            return datetime.now(timezone.utc) < self.blocked_until
        return False

@dataclass 
class AdminAction:
    """Log entry for admin actions."""
    id: Optional[int] = None
    admin_email: str = ""
    target_email: str = ""
    action: ActionType = ActionType.ROLE_CHANGE
    reason: str = ""
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    additional_data: Optional[str] = None  # JSON string for extra data

class UserCreateRequest(BaseModel):
    """Request model for creating new users."""
    email: EmailStr
    password: str
    role: UserRole = UserRole.USER
    is_premium: bool = False

class UserUpdateRequest(BaseModel):
    """Request model for updating users."""
    role: Optional[UserRole] = None
    is_premium: Optional[bool] = None
    status: Optional[AccountStatus] = None

class BlockUserRequest(BaseModel):
    """Request model for blocking users."""
    target_email: EmailStr
    reason: str = Field(min_length=1, max_length=500)
    duration_hours: Optional[int] = None  # None for permanent block

class AdminActionResponse(BaseModel):
    """Response model for admin actions."""
    success: bool
    message: str
    action_id: Optional[int] = None


# ----------------------------
# Dataclass used in tests / core logic
# ----------------------------
@dataclass
class Transaction:
    # Fields your tests pass in
    tx_id: str = ""
    timestamp: datetime = field(default_factory=datetime.utcnow)
    chain: str = "XRP"
    from_addr: Optional[str] = None
    to_addr: Optional[str] = None
    amount: Decimal = Decimal("0")
    symbol: str = "XRP"
    direction: str = "out"

    # Common extras used by your code
    fee: Decimal = Decimal("0")
    memo: Optional[str] = ""
    notes: Optional[str] = ""                     # <─ added so emails/CSV don’t break
    tags: List[str] = field(default_factory=list)
    is_internal: bool = False

    # Back-compat for code that expects from_address/to_address
    @property
    def from_address(self) -> Optional[str]:
        return self.from_addr

    @property
    def to_address(self) -> Optional[str]:
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
    from_addr: Optional[str] = Field(default=None, alias="from_address")
    to_addr: Optional[str]   = Field(default=None, alias="to_address")

    amount: Decimal
    symbol: str = "XRP"
    direction: str

    fee: Decimal = Decimal("0")
    memo: Optional[str] = None
    notes: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    is_internal: bool = False

    # Tagging outputs
    category: Optional[str] = None

    # Accept both 'risk_score' and legacy 'score' on input; serialize as 'risk_score'
    risk_score: Optional[float] = Field(
        default=None,
        validation_alias=AliasChoices("risk_score", "score")
    )
    # Accept both 'risk_flags' and legacy 'flags' on input; serialize as 'risk_flags'
    risk_flags: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("risk_flags", "flags")
    )

    # Convenience accessors so code can read .from_address/.to_address or .score/.flags too
    @property
    def from_address(self) -> Optional[str]:
        return self.from_addr

    @property
    def to_address(self) -> Optional[str]:
        return self.to_addr

    @property
    def score(self) -> Optional[float]:
        return self.risk_score

    @property
    def flags(self) -> List[str]:
        return self.risk_flags


class ReportRequest(BaseModel):
    """Input model for generating reports/exports."""
    model_config = ConfigDict(populate_by_name=True)

    address: Optional[str] = None
    chain: Optional[str] = "XRP"
    start: Optional[datetime] = None
    end: Optional[datetime] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    wallet_addresses: List[str] = Field(default_factory=list)   # <─ used in /report/csv


class ReportSummary(BaseModel):
    """
    Output model for summary endpoints/exports.
    Flexible defaults so reporter code can set more fields if needed.
    """
    model_config = ConfigDict(extra="allow")  # tolerate extra fields if reporter adds them

    address: Optional[str] = None
    chain: Optional[str] = "XRP"
    start: Optional[datetime] = None
    end: Optional[datetime] = None

    # Totals & counts
    count_in: int = 0
    count_out: int = 0
    total_in: Decimal = Decimal("0")
    total_out: Decimal = Decimal("0")
    total_fees: Decimal = Decimal("0")
    net: Decimal = Decimal("0")

    # Optional breakdowns
    categories: Dict[str, int] = Field(default_factory=dict)
