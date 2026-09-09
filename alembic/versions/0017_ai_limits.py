"""Adiciona limites de abuso de IA + tabela company_ai_usage.

Revision ID: 0017
Revises: 0016
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa

revision = "0017_ai_limits"
down_revision = "0016_pending_appointment_actions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Limites de abuso na tabela company_configs
    with op.batch_alter_table("company_configs") as batch:
        batch.add_column(sa.Column("ai_daily_message_limit", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("ai_daily_token_limit", sa.Integer(), nullable=False, server_default="0"))
        batch.add_column(sa.Column("ai_timeout_seconds", sa.Integer(), nullable=False, server_default="40"))
        batch.add_column(sa.Column("ai_max_retries", sa.Integer(), nullable=False, server_default="2"))
        batch.add_column(sa.Column("ai_fallback_message", sa.Text(), nullable=True, server_default=""))

    # Tabela de uso diario
    op.create_table(
        "company_ai_usage",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("usage_date", sa.Date(), nullable=False, index=True),
        sa.Column("message_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_company_ai_usage_date", "company_ai_usage", ["usage_date"])


def downgrade() -> None:
    op.drop_table("company_ai_usage")
    with op.batch_alter_table("company_configs") as batch:
        batch.drop_column("ai_daily_message_limit")
        batch.drop_column("ai_daily_token_limit")
        batch.drop_column("ai_timeout_seconds")
        batch.drop_column("ai_max_retries")
        batch.drop_column("ai_fallback_message")
