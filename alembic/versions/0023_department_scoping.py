"""add department_id to workflows and knowledge

Revision ID: 0023_department_scoping
Revises: 0022_api_keys
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0023_department_scoping"
down_revision = "0022_api_keys"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflows", sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True, index=True))
    op.add_column("knowledge", sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True, index=True))


def downgrade() -> None:
    op.drop_column("knowledge", "department_id")
    op.drop_column("workflows", "department_id")
