from datetime import datetime
from decimal import Decimal
from typing import Any

class User:
    def __init__(
        self,
        id: int | None = ...,
        email: str = ...,
        password_hash: str | None = ...,
        hashed_password: str | None = ...,
        role: Any = ...,
        is_active: bool | None = ...,
        is_admin: bool | None = ...,
        **kwargs: Any,
    ) -> None: ...

    id: int | None
    email: str
    password_hash: str | None
    role: Any
    is_active: bool
    is_admin: bool
    created_at: datetime | None
    last_login: datetime | None
    is_premium: bool

class Transaction:
    def __init__(
        self,
        id: int | None = ...,
        tx_id: str | None = ...,
        user_id: int | None = ...,
        amount: Decimal | float | str = ...,
        currency: str | None = ...,
        status: str | None = ...,
        **kwargs: Any,
    ) -> None: ...

    id: int | None
    tx_id: str
    user_id: int | None
    amount: Decimal
    currency: str
    symbol: str
    status: str | None
    timestamp: datetime
    chain: str
    from_addr: str | None
    to_addr: str | None
    direction: str
    fee: Decimal
    memo: str | None
    notes: str | None
    tags: list[str]
    is_internal: bool

# mark package as typed via presence of .pyi

class TaggedTransaction:
    tx_id: str
    timestamp: datetime
    chain: str
    from_addr: str | None
    to_addr: str | None
    amount: Decimal
    symbol: str
    direction: str
    fee: Decimal
    memo: str | None
    notes: str | None
    tags: list[str]
    is_internal: bool
    category: str | None
    risk_score: float | None
    risk_flags: list[str]
    def model_dump(self) -> dict[str, Any]: ...

class ReportSummary:
    def __init__(
        self,
        *,
        count_in: int | None = ...,
        count_out: int | None = ...,
        total_in: Decimal | None = ...,
        total_out: Decimal | None = ...,
        total_fees: Decimal | None = ...,
        net: Decimal | None = ...,
        **kwargs: Any,
    ) -> None: ...

    address: str | None
    chain: str | None
    start: datetime | None
    end: datetime | None
    count_in: int
    count_out: int
    total_in: Decimal
    total_out: Decimal
    total_fees: Decimal
    net: Decimal
    categories: dict[str, int]
    legacy_total_transactions: int | None
    legacy_total_volume: Decimal | None
    legacy_high_risk_count: int | None

# mark package as typed via presence of .pyi

class ReportRequest:
    def __init__(
        self,
        *,
        address: str | None = ...,
        chain: str | None = ...,
        start: datetime | None = ...,
        end: datetime | None = ...,
        min_amount: Decimal | None = ...,
        max_amount: Decimal | None = ...,
        wallet_addresses: list[str] = ...,
        **kwargs: Any,
    ) -> None: ...
