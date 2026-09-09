"""create workflow_versions table

Revision ID: 0021_workflow_versions
Revises: 0020_outbound_webhooks
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0021_workflow_versions"
down_revision = "0020_outbound_webhooks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_id", sa.Integer(), sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("trigger_type", sa.String(), nullable=False, server_default="message"),
        sa.Column("trigger_config", sa.JSON(), server_default="{}"),
        sa.Column("note", sa.Text(), server_default=""),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_workflow_versions_workflow_version", "workflow_versions", ["workflow_id", "version_number"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_workflow_versions_workflow_version")
    op.drop_table("workflow_versions")
