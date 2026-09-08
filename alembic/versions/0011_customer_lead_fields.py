"""0011 customer lead fields

Revision ID: 0011_customer_lead_fields
Revises: 0010_departments
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0011_customer_lead_fields"
down_revision = "0010_departments"
branch_labels = None
depends_on = None


def _add_column_if_missing(table: str, column: sa.Column) -> None:
    existing = {c["name"] for c in inspect(op.get_bind()).get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column_if_missing("customers", sa.Column("email", sa.String(), nullable=True))
    _add_column_if_missing("customers", sa.Column("company", sa.String(), nullable=True))
    _add_column_if_missing("customers", sa.Column("city", sa.String(), nullable=True))
    _add_column_if_missing("customers", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("customers") as batch:
        for name in ("email", "company", "city", "notes"):
            batch.drop_column(name)