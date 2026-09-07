"""add user_id to workflows for AI config resolution

Revision ID: 0009_workflow_user_id
Revises: 0008_user_ai_config
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0009_workflow_user_id"
down_revision = "0008_user_ai_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    columns = [c["name"] for c in inspector.get_columns("workflows")]

    if "user_id" not in columns:
        op.add_column(
            "workflows",
            sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        )
        op.create_index(
            "ix_workflows_user_id",
            "workflows",
            ["user_id"],
        )


def downgrade() -> None:
    op.drop_index("ix_workflows_user_id", "workflows")
    op.drop_column("workflows", "user_id")
