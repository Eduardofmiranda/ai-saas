"""add conversation_transfers table

Revision ID: 0004_conversation_transfers
Revises: 0003_knowledge
Create Date: 2026-09-04
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0004_conversation_transfers"
down_revision = "0003_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if "conversation_transfers" not in inspector.get_table_names():
        op.create_table(
            "conversation_transfers",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column(
                "conversation_id",
                sa.Integer(),
                sa.ForeignKey("conversations.id"),
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
            sa.Column("actor_type", sa.String(), default="workflow", nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=True),
            sa.Column("user_name", sa.String(), default="", nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("conversation_transfers")