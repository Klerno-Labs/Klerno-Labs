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


def main(url: str | None = None) -> int:
    """Create minimal core tables on `url` or DATABASE_URL.

    The optional `url` argument allows callers (tests) to explicitly target
    a temporary database file without relying on environment initialization
    order. Returns 0 on success, non-zero on error (for use from scripts).
    """
    url = url or os.getenv("DATABASE_URL") or "sqlite:///./data/klerno.db"
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
            "subscription_active",
            Boolean,
            nullable=False,
            server_default=text("false"),
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
        Column("notes", String(2048), nullable=True),
        Column("amount", Numeric(18, 8), nullable=True),
        Column("currency", String(16), nullable=True),
        Column("status", String(32), nullable=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )

    # Some parts of the application (legacy code / tests) expect a table named
    # 'txs' instead of 'transactions'. Create a lightweight 'txs' table with a
    # superset of commonly-used columns so tests and runtime code using either
    # name will work in CI (sqlite fallback).
    txs = Table(
        "txs",
        meta,
        Column("id", Integer, primary_key=True),
        Column("tx_id", String(64), nullable=True),
        Column("notes", String(2048), nullable=True),
        Column("timestamp", String(64), nullable=True),
        Column("chain", String(64), nullable=True),
        Column("from_addr", String(255), nullable=True),
        Column("to_addr", String(255), nullable=True),
        Column("amount", Numeric(18, 8), nullable=True),
        Column("symbol", String(32), nullable=True),
        Column("direction", String(32), nullable=True),
        Column("memo", String(1024), nullable=True),
        Column("fee", Numeric(18, 8), nullable=True),
        Column("category", String(64), nullable=True),
        Column("risk_score", Numeric(5, 2), nullable=True),
        Column("risk_flags", String(1024), nullable=True),
        Column(
            "created_at",
            DateTime(timezone=True),
            server_default=text("CURRENT_TIMESTAMP"),
        ),
    )

    try:
        # ensure variables are referenced so linters don't flag them
        _ = (users, transactions, txs)
        meta.create_all(engine)
        print(f"Initialized tables (if missing) on {url}")
        return 0
    except Exception as exc:  # pragma: no cover - CI helper
        print("Failed to create tables:", exc, file=sys.stderr)
        return 2

    if __name__ == "__main__":
        # When invoked as a script, call main() without args so it reads
        # DATABASE_URL from the environment as before.
        raise SystemExit(main())
