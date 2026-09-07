"""0010 departments

Revision ID: 0010
Revises: 0009
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa


revision = "0010_departments"
down_revision = "0009_workflow_user_id"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "departments",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), server_default=""),
        sa.Column("is_active", sa.Integer(), server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    with op.batch_alter_table("conversations") as batch:
        batch.add_column(
            sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("conversations") as batch:
        batch.drop_constraint(None, type_="foreignkey")
        batch.drop_column("department_id")
    op.drop_table("departments")
