"""create initial application schema

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-09-04

This baseline is idempotent so an existing production database created by the
legacy create_all bootstrap can be adopted safely by Alembic.
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def _create_if_missing(name: str, *columns, **kwargs) -> None:
    if name not in inspect(op.get_bind()).get_table_names():
        op.create_table(name, *columns, **kwargs)


def upgrade() -> None:
    _create_if_missing(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
    )
    _create_if_missing(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="agent"),
    )
    _create_if_missing(
        "company_configs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False, unique=True),
        sa.Column("ai_provider", sa.String(), nullable=False, server_default=""),
        sa.Column("ai_model", sa.String(), nullable=False, server_default=""),
        sa.Column("ai_api_key", sa.String(), nullable=True, server_default=""),
        sa.Column("ai_base_url", sa.String(), nullable=True, server_default=""),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("evolution_base_url", sa.String(), nullable=True, server_default=""),
        sa.Column("evolution_api_key", sa.String(), nullable=True, server_default=""),
        sa.Column("evolution_instance", sa.String(), nullable=True, server_default=""),
        sa.Column("ai_on", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    _create_if_missing(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("phone", sa.String(), nullable=False),
    )
    _create_if_missing(
        "conversations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=True, server_default="open"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    _create_if_missing(
        "messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("conversation_id", sa.Integer(), sa.ForeignKey("conversations.id"), nullable=False),
        sa.Column("sender_type", sa.String(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("wa_message_id", sa.String(), nullable=True, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )
    _create_if_missing(
        "workflows",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True, server_default=""),
        sa.Column("data", sa.JSON(), nullable=True),
        sa.Column("trigger_type", sa.String(), nullable=True, server_default="message"),
        sa.Column("trigger_config", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    _create_if_missing(
        "executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_id", sa.Integer(), sa.ForeignKey("workflows.id"), nullable=False),
        sa.Column("company_id", sa.Integer(), sa.ForeignKey("companies.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("context", sa.JSON(), nullable=True),
        sa.Column("node_results", sa.JSON(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True, server_default=""),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # Baseline adoption must never drop user data automatically.
    raise NotImplementedError("The initial schema migration is intentionally irreversible")