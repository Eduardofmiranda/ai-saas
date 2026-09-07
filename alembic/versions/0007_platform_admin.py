"""add platform administration and provider credentials

Revision ID: 0007_platform_admin
Revises: 0006_pgvector_knowledge
Create Date: 2026-09-07
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0007_platform_admin"
down_revision = "0006_pgvector_knowledge"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    inspector = inspect(connection)
    users_columns = {column["name"] for column in inspector.get_columns("users")}
    if "is_platform_admin" not in users_columns:
        op.add_column(
            "users",
            sa.Column(
                "is_platform_admin",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    if "platform_ai_providers" not in inspector.get_table_names():
        op.create_table(
            "platform_ai_providers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("provider", sa.String(), nullable=False, unique=True),
            sa.Column("model", sa.String(), nullable=False, server_default=""),
            sa.Column("api_key", sa.Text(), nullable=False, server_default=""),
            sa.Column("base_url", sa.String(), nullable=False, server_default=""),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index(
            "ix_platform_ai_providers_provider",
            "platform_ai_providers",
            ["provider"],
            unique=True,
        )


def downgrade() -> None:
    # Remover credenciais e privilégios pode bloquear acesso operacional;
    # rollback só deve ocorrer com plano explícito de recuperação.
    raise NotImplementedError("Migracao de administracao global e intencionalmente irreversivel")