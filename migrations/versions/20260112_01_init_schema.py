"""init schema

Revision ID: 20260112_01
Revises:
Create Date: 2026-01-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260112_01"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("username", sa.String(length=80), nullable=False),
        sa.Column("password_hash", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
        sa.Column("last_login", sa.BigInteger(), nullable=True),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("temp_email_address", sa.String(length=255), nullable=True),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password", sa.String(length=255), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("create_time", sa.BigInteger(), nullable=False),
        sa.Column("expire_time", sa.BigInteger(), nullable=False),
        sa.Column("is_used", sa.Integer(), nullable=True),
        sa.Column("is_deleted", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.UniqueConstraint("email"),
    )

    op.create_table(
        "revoked_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("exp", sa.BigInteger(), nullable=False),
        sa.Column("revoked_at", sa.BigInteger(), nullable=False),
        sa.UniqueConstraint("jti"),
    )
    op.create_index("ix_revoked_tokens_user_id", "revoked_tokens", ["user_id"])
    op.create_index("ix_revoked_tokens_exp", "revoked_tokens", ["exp"])
    op.create_index("ix_revoked_tokens_revoked_at", "revoked_tokens", ["revoked_at"])

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=True),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("ip", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("detail", sa.Text(), nullable=True),
        sa.Column("created_at", sa.BigInteger(), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_action", "audit_logs", ["action"])
    op.create_index("ix_audit_logs_request_id", "audit_logs", ["request_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_request_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_action", table_name="audit_logs")
    op.drop_index("ix_audit_logs_user_id", table_name="audit_logs")
    op.drop_table("audit_logs")

    op.drop_index("ix_revoked_tokens_revoked_at", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_exp", table_name="revoked_tokens")
    op.drop_index("ix_revoked_tokens_user_id", table_name="revoked_tokens")
    op.drop_table("revoked_tokens")

    op.drop_table("accounts")
    op.drop_table("users")
