"""Initial core tables (users, transactions) baseline.

Revision ID: 0001_initial_core_tables
Revises:
Create Date: 2025-09-25
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "0001_initial_core_tables"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():  # noqa: D401
    op.create_table(
        "users",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("email", sa.String(length=255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=False, server_default="user"),
        sa.Column(
            "subscription_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=True)

    op.create_table(
        "transactions",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tx_id", sa.String(length=64), nullable=True),
        sa.Column("amount", sa.Numeric(18, 8), nullable=True),
        sa.Column("currency", sa.String(length=16), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index("idx_transactions_created_at", "transactions", ["created_at"])  # noqa: E501


def downgrade():  # noqa: D401
    with op.batch_alter_table("transactions"):
        op.drop_index("idx_transactions_created_at")
    op.drop_table("transactions")

    with op.batch_alter_table("users"):
        op.drop_index("idx_users_email")
    op.drop_table("users")
