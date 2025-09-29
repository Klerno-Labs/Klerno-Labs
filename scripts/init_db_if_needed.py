#!/usr/bin/env python3
"""Create minimal core tables if they don't exist (fallback when alembic fails)."""
from __future__ import annotations

import os
import sys

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    Numeric,
    String,
    Table,
    text,
)


def main() -> int:
    url = os.getenv("DATABASE_URL") or "sqlite:///./data/klerno.db"
    engine = sa.create_engine(url)
    meta = MetaData()

    users = Table(
        "users",
        meta,
        Column("id", Integer, primary_key=True),
        Column("email", String(255), nullable=False, unique=True),
        Column("password_hash", String(255), nullable=True),
        Column("role", String(50), nullable=False, server_default="user"),
        Column(
            "subscription_active", Boolean, nullable=False, server_default=text("false")
        ),
        Column(
            "created_at",
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )

    transactions = Table(
        "transactions",
        meta,
        Column("id", Integer, primary_key=True),
        Column("tx_id", String(64), nullable=True),
        Column("amount", Numeric(18, 8), nullable=True),
        Column("currency", String(16), nullable=True),
        Column("status", String(32), nullable=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )

    try:
        # ensure variables are referenced so linters don't flag them
        _ = (users, transactions)
        meta.create_all(engine)
        print(f"Initialized tables (if missing) on {url}")
        return 0
    except Exception as exc:  # pragma: no cover - CI helper
        print("Failed to create tables:", exc, file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
