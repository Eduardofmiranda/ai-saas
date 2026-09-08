"""0012 business hours

Revision ID: 0012_business_hours
Revises: 0011_customer_lead_fields
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0012_business_hours"
down_revision = "0011_customer_lead_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "business_hours" not in inspector.get_table_names():
        op.create_table(
            "business_hours",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "company_id",
                sa.Integer(),
                sa.ForeignKey("companies.id"),
                nullable=False,
                unique=True,
                index=True,
            ),
            sa.Column(
                "timezone",
                sa.String(),
                nullable=False,
                server_default="America/Sao_Paulo",
            ),
            sa.Column("enabled", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("schedule", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("business_hours")