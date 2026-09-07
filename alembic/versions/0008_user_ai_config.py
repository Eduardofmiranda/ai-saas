"""add user AI config for per-user provider/model policy

Revision ID: 0008_user_ai_config
Revises: 0007_platform_admin
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0008_user_ai_config"
down_revision = "0007_platform_admin"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)

    if "user_ai_configs" not in inspector.get_table_names():
        op.create_table(
            "user_ai_configs",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, unique=True),
            sa.Column("allowed_providers", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("default_provider", sa.String(), nullable=False, server_default=""),
            sa.Column("default_model", sa.String(), nullable=False, server_default=""),
            sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_user_ai_configs_user_id",
            "user_ai_configs",
            ["user_id"],
            unique=True,
        )


def downgrade() -> None:
    raise NotImplementedError("Migracao de politica de IA por usuario e intencionalmente irreversivel")
