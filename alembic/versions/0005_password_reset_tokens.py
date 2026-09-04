"""add password_reset_tokens table

Revision ID: 0005_password_reset_tokens
Revises: 0004_conversation_transfers
Create Date: 2026-09-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0005_password_reset_tokens"
down_revision = "0004_conversation_transfers"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if "password_reset_tokens" not in inspector.get_table_names():
        op.create_table(
            "password_reset_tokens",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "company_id",
                sa.Integer(),
                sa.ForeignKey("companies.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("token_hash", sa.String(), nullable=False, index=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("password_reset_tokens")