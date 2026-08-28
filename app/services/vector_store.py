from sqlalchemy import text
from sqlalchemy.orm import Session

from app.services.embedding import (
    chunk_text,
    cosine_similarity,
    generate_embeddings,
)


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

    inserted = 0
    for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
        db.execute(
            text(
                "INSERT INTO knowledge_chunks (knowledge_id, company_id, chunk_index, content, embedding, tokens) "
                "VALUES (:kid, :cid, :idx, :content, :embedding, :tokens)"
            ),
            {
                "kid": knowledge_id,
                "cid": company_id,
                "idx": i,
                "content": chunk,
                "embedding": embedding,
                "tokens": len(chunk.split()),
            },
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

    rows = db.execute(
        text(
            "SELECT id, knowledge_id, content, embedding, tokens "
            "FROM knowledge_chunks WHERE company_id = :cid AND embedding IS NOT NULL"
        ),
        {"cid": company_id},
    ).fetchall()

    results = []
    for row in rows:
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
    except Exception:
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
