"""create outbound_webhooks and outbound_webhook_logs tables

Revision ID: 0020_outbound_webhooks
Revises: 0019_user_departments
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0020_outbound_webhooks"
down_revision = "0019_user_departments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbound_webhooks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("secret", sa.String(), nullable=False, server_default=""),
        sa.Column("events", sa.String(), nullable=False, server_default="workflow.completed,workflow.error"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "outbound_webhook_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("webhook_id", sa.Integer(), sa.ForeignKey("outbound_webhooks.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("event", sa.String(), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("status_code", sa.Integer(), server_default="0"),
        sa.Column("success", sa.Boolean(), server_default="false"),
        sa.Column("request_body", sa.Text(), server_default=""),
        sa.Column("response_body", sa.Text(), server_default=""),
        sa.Column("error", sa.Text(), server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("outbound_webhook_logs")
    op.drop_table("outbound_webhooks")
