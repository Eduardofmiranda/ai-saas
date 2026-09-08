"""0014 agenda confirmacao em 2 passos + lembretes

Revision ID: 0014_agenda_confirmation
Revises: 0013_agenda
Create Date: 2026-09-08
"""
from alembic import op
import sqlalchemy as sa


revision = "0014_agenda_confirmation"
down_revision = "0013_agenda"
branch_labels = None
depends_on = None


def _add_column(table, column, server_default=None):
    """Adiciona coluna apenas se ainda nao existir (padrao 0013)."""
    from sqlalchemy import inspect

    inspector = inspect(op.get_bind())
    existing = {c["name"] for c in inspector.get_columns(table)}
    if column.name not in existing:
        op.add_column(table, column)


def upgrade() -> None:
    _add_column(
        "agenda_config",
        sa.Column("confirmation_required", sa.Integer(), nullable=False, server_default="1"),
    )
    _add_column(
        "agenda_config",
        sa.Column("confirmation_expiry_hours", sa.Integer(), nullable=False, server_default="24"),
    )
    _add_column(
        "agenda_config",
        sa.Column(
            "confirmation_request_message",
            sa.Text(),
            nullable=True,
        ),
    )
    _add_column(
        "agenda_config",
        sa.Column("reminders_enabled", sa.Integer(), nullable=False, server_default="0"),
    )
    _add_column(
        "agenda_config",
        sa.Column("reminder_hours", sa.Text(), nullable=False, server_default="[24]"),
    )
    _add_column("agenda_config", sa.Column("reminder_message", sa.Text(), nullable=True))
    _add_column("agenda_config", sa.Column("whatsapp_number", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("agenda_config", "whatsapp_number")
    op.drop_column("agenda_config", "reminder_message")
    op.drop_column("agenda_config", "reminder_hours")
    op.drop_column("agenda_config", "reminders_enabled")
    op.drop_column("agenda_config", "confirmation_request_message")
    op.drop_column("agenda_config", "confirmation_expiry_hours")
    op.drop_column("agenda_config", "confirmation_required")