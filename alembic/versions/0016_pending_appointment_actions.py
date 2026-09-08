"""0016 pending appointment actions

Tabela de acoes pendentes de consentimento do cliente (remarcar/cancelar via
WhatsApp com `confirmation_required` ativo). O compromisso original permanece
inalterado ate o cliente confirmar.

Revision ID: 0016_pending_appointment_actions
Revises: 0015_agenda_slot_index
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0016_pending_appointment_actions"
down_revision = "0015_agenda_slot_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())

    if "pending_appointment_actions" not in inspector.get_table_names():
        op.create_table(
            "pending_appointment_actions",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "company_id",
                sa.Integer(),
                sa.ForeignKey("companies.id"),
                nullable=False,
                index=True,
            ),
            sa.Column(
                "appointment_id",
                sa.Integer(),
                sa.ForeignKey("appointments.id"),
                nullable=False,
                index=True,
            ),
            sa.Column("phone", sa.String(), nullable=False, index=True),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("payload", sa.Text(), nullable=True),
            sa.Column("notified", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "pending_appointment_actions" in inspector.get_table_names():
        op.drop_table("pending_appointment_actions")
