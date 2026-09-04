"""enable pgvector search for knowledge chunks

Revision ID: 0006_pgvector_knowledge
Revises: 0005_password_reset_tokens
Create Date: 2026-09-04

SQLite keeps the JSON fallback used by local tests. PostgreSQL/Supabase gains a
pgvector column and a partial HNSW index for the configured embedding dimension.
"""
from __future__ import annotations

import os

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0006_pgvector_knowledge"
down_revision = "0005_password_reset_tokens"
branch_labels = None
depends_on = None


def _enabled() -> bool:
    return os.getenv("ENABLE_PGVECTOR", "false").lower() in {"1", "true", "yes"}


def _dimensions() -> int:
    value = os.getenv("DEFAULT_EMBEDDING_DIMENSIONS", "1536")
    try:
        dimensions = int(value)
    except ValueError as exc:
        raise RuntimeError("DEFAULT_EMBEDDING_DIMENSIONS deve ser um inteiro") from exc
    if dimensions < 1 or dimensions > 16000:
        raise RuntimeError("DEFAULT_EMBEDDING_DIMENSIONS fora do intervalo permitido")
    return dimensions


def upgrade() -> None:
    connection = op.get_bind()
    if "knowledge_chunks" not in inspect(connection).get_table_names():
        return

    columns = {column["name"] for column in inspect(connection).get_columns("knowledge_chunks")}
    # Metadados sao necessarios em todos os ambientes para impedir comparacao
    # de vetores de modelos diferentes. A representacao vetorial fica no Postgres.
    if "embedding_model" not in columns:
        op.add_column(
            "knowledge_chunks",
            sa.Column("embedding_model", sa.String(), nullable=False, server_default="text-embedding-3-small"),
        )
    if "embedding_dimensions" not in columns:
        op.add_column(
            "knowledge_chunks",
            sa.Column("embedding_dimensions", sa.Integer(), nullable=False, server_default="0"),
        )

    if connection.dialect.name != "postgresql" or not _enabled():
        return

    dimensions = _dimensions()
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        op.execute("ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding_vector vector")
        # O código anterior sempre usava text-embedding-3-small. Convertemos
        # apenas vetores existentes e preservamos o JSON como rollback/fallback.
        op.execute(
            "UPDATE knowledge_chunks "
            "SET embedding_vector = embedding::text::vector "
            "WHERE embedding IS NOT NULL AND embedding_vector IS NULL"
        )
        op.execute(
            "UPDATE knowledge_chunks "
            "SET embedding_dimensions = vector_dims(embedding_vector) "
            "WHERE embedding_vector IS NOT NULL AND embedding_dimensions = 0"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_company_embedding_model "
            "ON knowledge_chunks (company_id, embedding_model)"
        )
        op.execute(
            f"CREATE INDEX IF NOT EXISTS ix_knowledge_chunks_embedding_hnsw_{dimensions} "
            "ON knowledge_chunks USING hnsw "
            f"((embedding_vector::vector({dimensions})) vector_cosine_ops) "
            "WITH (m = 16, ef_construction = 64) "
            f"WHERE embedding_vector IS NOT NULL AND embedding_dimensions = {dimensions}"
        )
    except Exception as exc:
        raise RuntimeError(
            "Nao foi possivel habilitar pgvector. Confirme a extensao vector no Supabase "
            "ou defina ENABLE_PGVECTOR=false para manter o fallback JSON temporariamente."
        ) from exc


def downgrade() -> None:
    # Remover vetores pode inutilizar a base de conhecimento; rollback explicito
    # deve ser feito por uma migration operacional planejada, nunca automaticamente.
    raise NotImplementedError("A migracao pgvector e intencionalmente irreversivel")