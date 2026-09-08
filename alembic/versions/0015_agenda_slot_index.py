"""0015 agenda slot index

Indice composto (company_id, date) em appointments para acelerar a checagem
de conflito (has_conflict) em volunes maiores. A garantia contra dupla reserva
vem do advisory lock transacional em app/services/agenda.py (_serialize_booking);
este indice e apenas performance.

Revision ID: 0015_agenda_slot_index
Revises: 0014_agenda_confirmation
Create Date: 2026-09-08
"""
from alembic import op
from sqlalchemy import inspect

revision = "0015_agenda_slot_index"
down_revision = "0014_agenda_confirmation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "appointments" not in inspector.get_table_names():
        return
    indexes = {ix["name"] for ix in inspector.get_indexes("appointments")}
    if "ix_appointments_company_date" not in indexes:
        op.create_index("ix_appointments_company_date", "appointments", ["company_id", "date"])


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "appointments" not in inspector.get_table_names():
        return
    indexes = {ix["name"] for ix in inspector.get_indexes("appointments")}
    if "ix_appointments_company_date" in indexes:
        op.drop_index("ix_appointments_company_date", table_name="appointments")