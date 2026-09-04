import json
import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.embedding import (
    chunk_text,
    cosine_similarity,
    generate_embeddings,
    EmbeddingError,
)

logger = logging.getLogger(__name__)


def _has_pgvector(db: Session) -> bool:
    """Confirma pgvector somente no Postgres que recebeu a migration 0006."""
    if db.bind is None or db.bind.dialect.name != "postgresql":
        return False
    try:
        return bool(db.execute(text("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'knowledge_chunks' AND column_name = 'embedding_vector'
            )
        """)).scalar())
    except Exception:
        return False


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(format(float(value), ".10g") for value in values) + "]"


async def upsert_knowledge(
    db: Session,
    company_id: int,
    knowledge_id: int,
    content: str,
    provider: str = "openai",
    api_key: str = "",
    embedding_model: str = "text-embedding-3-small",
    base_url: str = "",
) -> int:
    chunks = chunk_text(content)
    if not chunks:
        return 0

    embeddings = await generate_embeddings(chunks, provider, api_key, embedding_model, base_url)

    db.execute(
        text("DELETE FROM knowledge_chunks WHERE knowledge_id = :kid"),
        {"kid": knowledge_id},
    )

    use_pgvector = _has_pgvector(db)
    inserted = 0
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        params = {
            "kid": knowledge_id,
            "cid": company_id,
            "idx": i,
            "content": chunk,
            "embedding": json.dumps(embedding),
            "embedding_model": embedding_model,
            "embedding_dimensions": len(embedding),
            "tokens": len(chunk.split()),
        }
        if use_pgvector:
            db.execute(
                text(
                    "INSERT INTO knowledge_chunks (knowledge_id, company_id, chunk_index, content, embedding, "
                    "embedding_model, embedding_dimensions, embedding_vector, tokens) "
                    "VALUES (:kid, :cid, :idx, :content, CAST(:embedding AS json), :embedding_model, "
                    ":embedding_dimensions, CAST(:embedding_vector AS vector), :tokens)"
                ),
                {**params, "embedding_vector": _vector_literal(embedding)},
            )
        else:
            db.execute(
                text(
                    "INSERT INTO knowledge_chunks (knowledge_id, company_id, chunk_index, content, embedding, "
                    "embedding_model, embedding_dimensions, tokens) "
                    "VALUES (:kid, :cid, :idx, :content, :embedding, :embedding_model, "
                    ":embedding_dimensions, :tokens)"
                ),
                params,
            )
        inserted += 1

    db.commit()
    return inserted


async def search_similar(
    db: Session,
    company_id: int,
    query: str,
    provider: str = "openai",
    api_key: str = "",
    embedding_model: str = "text-embedding-3-small",
    base_url: str = "",
    top_k: int = 5,
) -> list[dict]:
    query_embedding = await generate_single_embedding_safe(
        query, provider, api_key, embedding_model, base_url
    )
    if not query_embedding:
        return []

    if _has_pgvector(db):
        rows = db.execute(
            text(
                "SELECT id, knowledge_id, content, tokens, "
                "1 - (embedding_vector <=> CAST(:query_embedding AS vector)) AS similarity "
                "FROM knowledge_chunks "
                "WHERE company_id = :cid AND embedding_vector IS NOT NULL "
                "AND embedding_model = :embedding_model "
                "AND embedding_dimensions = :embedding_dimensions "
                "ORDER BY embedding_vector <=> CAST(:query_embedding AS vector) "
                "LIMIT :top_k"
            ),
            {
                "cid": company_id,
                "query_embedding": _vector_literal(query_embedding),
                "embedding_model": embedding_model,
                "embedding_dimensions": len(query_embedding),
                "top_k": top_k,
            },
        ).fetchall()
        return [
            {
                "chunk_id": row.id,
                "knowledge_id": row.knowledge_id,
                "content": row.content,
                "tokens": row.tokens,
                "similarity": round(float(row.similarity), 4),
            }
            for row in rows
        ]

    rows = db.execute(
        text(
            "SELECT id, knowledge_id, content, embedding, tokens, embedding_model "
            "FROM knowledge_chunks WHERE company_id = :cid AND embedding IS NOT NULL"
        ),
        {"cid": company_id},
    ).fetchall()

    results = []
    for row in rows:
        if row.embedding_model and row.embedding_model != embedding_model:
            continue
        emb = row.embedding
        if isinstance(emb, str):
            emb = _parse_pg_array(emb)
        sim = cosine_similarity(query_embedding, emb)
        results.append({
            "chunk_id": row.id,
            "knowledge_id": row.knowledge_id,
            "content": row.content,
            "tokens": row.tokens,
            "similarity": round(sim, 4),
        })

    results.sort(key=lambda x: x["similarity"], reverse=True)
    return results[:top_k]


async def generate_single_embedding_safe(
    text_content: str,
    provider: str,
    api_key: str,
    model: str,
    base_url: str,
) -> list[float] | None:
    try:
        from app.services.embedding import generate_single_embedding
        return await generate_single_embedding(text_content, provider, api_key, model, base_url)
    except EmbeddingError as exc:
        logger.warning("Embedding de consulta indisponivel: %s", exc)
        return None


def _parse_pg_array(arr_str: str) -> list[float]:
    arr_str = arr_str.strip()
    if arr_str.startswith("[") and arr_str.endswith("]"):
        arr_str = arr_str[1:-1]
    return [float(x.strip()) for x in arr_str.split(",") if x.strip()]


def get_chunks_by_knowledge(db: Session, knowledge_id: int) -> list[dict]:
    rows = db.execute(
        text(
            "SELECT id, chunk_index, content, tokens "
            "FROM knowledge_chunks WHERE knowledge_id = :kid ORDER BY chunk_index"
        ),
        {"kid": knowledge_id},
    ).fetchall()
    return [{"id": r.id, "chunk_index": r.chunk_index, "content": r.content, "tokens": r.tokens} for r in rows]


def delete_knowledge_chunks(db: Session, knowledge_id: int) -> None:
    db.execute(
        text("DELETE FROM knowledge_chunks WHERE knowledge_id = :kid"),
        {"kid": knowledge_id},
    )
    db.commit()


def count_chunks(db: Session, company_id: int) -> int:
    result = db.execute(
        text("SELECT COUNT(*) FROM knowledge_chunks WHERE company_id = :cid"),
        {"cid": company_id},
    ).scalar()
    return result or 0
