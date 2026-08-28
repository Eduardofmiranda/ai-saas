"""add knowledge and knowledge_chunks tables

Revision ID: 0003_knowledge
Revises: 0002_pending_flows
Create Date: 2026-08-28
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0003_knowledge"
down_revision = "0002_pending_flows"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = inspect(conn)

    if "knowledge" not in inspector.get_table_names():
        op.create_table(
            "knowledge",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), default=""),
            sa.Column("source_type", sa.String(), default="text"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )

    if "knowledge_chunks" not in inspector.get_table_names():
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("knowledge_id", sa.Integer(), sa.ForeignKey("knowledge.id", ondelete="CASCADE"), nullable=False, index=True),
            sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, index=True),
            sa.Column("chunk_index", sa.Integer(), default=0),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("embedding", sa.JSON(), nullable=True),
            sa.Column("tokens", sa.Integer(), default=0),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge")
