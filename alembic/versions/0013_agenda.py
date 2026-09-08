"""0013 agenda (Secretaria IA)

Revision ID: 0013_agenda
Revises: 0012_business_hours
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0013_agenda"
down_revision = "0012_business_hours"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    if "agenda_config" not in inspector.get_table_names():
        op.create_table(
            "agenda_config",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "company_id",
                sa.Integer(),
                sa.ForeignKey("companies.id"),
                nullable=False,
                unique=True,
                index=True,
            ),
            sa.Column("enabled", sa.Integer(), nullable=False, server_default="0"),
            sa.Column(
                "timezone",
                sa.String(),
                nullable=False,
                server_default="America/Sao_Paulo",
            ),
            sa.Column("schedule", sa.Text(), nullable=False, server_default="{}"),
            sa.Column("slot_duration", sa.Integer(), nullable=False, server_default="30"),
            sa.Column("min_advance", sa.Integer(), nullable=False, server_default="60"),
            sa.Column("blocked", sa.Text(), nullable=False, server_default="[]"),
            sa.Column("confirmation_message", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "appointments" not in inspector.get_table_names():
        op.create_table(
            "appointments",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "company_id",
                sa.Integer(),
                sa.ForeignKey("companies.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "customer_id",
                sa.Integer(),
                sa.ForeignKey("customers.id"),
                nullable=True,
                index=True,
            ),
            sa.Column("customer_name", sa.String(), nullable=True),
            sa.Column("phone", sa.String(), nullable=False),
            sa.Column("status", sa.String(), nullable=False, server_default="scheduled", index=True),
            sa.Column("date", sa.String(), nullable=False, index=True),
            sa.Column("start_time", sa.String(), nullable=False),
            sa.Column("end_time", sa.String(), nullable=False),
            sa.Column("service", sa.String(), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("origin", sa.String(), nullable=False, server_default="manual"),
            sa.Column(
                "created_by_user_id",
                sa.Integer(),
                sa.ForeignKey("users.id"),
                nullable=True,
            ),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "appointment_events" not in inspector.get_table_names():
        op.create_table(
            "appointment_events",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "appointment_id",
                sa.Integer(),
                sa.ForeignKey("appointments.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "company_id",
                sa.Integer(),
                sa.ForeignKey("companies.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("actor_type", sa.String(), nullable=False, server_default="user"),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("user_name", sa.String(), nullable=True),
            sa.Column("details", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("appointment_events")
    op.drop_table("appointments")
    op.drop_table("agenda_config")