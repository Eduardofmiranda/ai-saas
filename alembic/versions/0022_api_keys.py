"""create api_keys table

Revision ID: 0022_api_keys
Revises: 0021_workflow_versions
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0022_api_keys"
down_revision = "0021_workflow_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("key_hash", sa.String(), nullable=False, unique=True, index=True),
        sa.Column("key_prefix", sa.String(), nullable=False),
        sa.Column("scopes", sa.String(), nullable=False, server_default="read"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("api_keys")
