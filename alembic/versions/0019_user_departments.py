"""Cria tabela user_departments (associacao membro <-> setor, nivel de acesso).

Revision ID: 0019
Revises: 0018_audit_log
Create Date: 2026-09-09
"""
from alembic import op
import sqlalchemy as sa

revision = "0019_user_departments"
down_revision = "0018_audit_log"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_departments",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "department_id",
            sa.Integer(),
            sa.ForeignKey("departments.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("level", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "department_id", name="uq_user_department"),
    )


def downgrade() -> None:
    op.drop_table("user_departments")