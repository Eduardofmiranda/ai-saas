"""add pending_flows table

Revision ID: 0002_pending_flows
Revises: None
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "0002_pending_flows"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)
    if "pending_flows" in inspector.get_table_names():
        return
    op.create_table(
        "pending_flows",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("workflow_id", sa.Integer(), sa.ForeignKey("workflows.id"), nullable=False, index=True),
        sa.Column("execution_id", sa.Integer(), sa.ForeignKey("executions.id"), nullable=False, index=True),
        sa.Column("phone", sa.String(), nullable=False, index=True),
        sa.Column("snapshot", sa.JSON(), nullable=True, default=dict),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("pending_flows")
