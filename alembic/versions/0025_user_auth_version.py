"""add JWT revocation version to users

Revision ID: 0025_user_auth_version
Revises: 0024_campaigns
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0025_user_auth_version"
down_revision = "0024_campaigns"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("auth_version", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("users", "auth_version")
