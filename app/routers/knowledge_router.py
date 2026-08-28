from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.knowledge import Knowledge
from app.models.user import User
from app.schemas.knowledge_schema import (
    KnowledgeCreate,
    KnowledgeDetail,
    KnowledgeResponse,
    KnowledgeSearch,
    KnowledgeUpdate,
    SearchResult,
)
from app.services.deps import get_current_user
from app.services.vector_store import (
    count_chunks,
    delete_knowledge_chunks,
    get_chunks_by_knowledge,
    search_similar,
    upsert_knowledge,
)
from app.config import get_secret

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("/")
def list_knowledge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[KnowledgeResponse]:
    items = (
        db.query(Knowledge)
        .filter(Knowledge.company_id == current_user.company_id)
        .order_by(Knowledge.created_at.desc())
        .all()
    )
    result = []
    for item in items:
        chunks = get_chunks_by_knowledge(db, item.id)
        result.append(KnowledgeResponse(
            id=item.id,
            company_id=item.company_id,
            name=item.name,
            description=item.description or "",
            source_type=item.source_type or "text",
            chunk_count=len(chunks),
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    return result


@router.get("/{knowledge_id}")
def get_knowledge(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeDetail:
    item = (
        db.query(Knowledge)
        .filter(Knowledge.id == knowledge_id, Knowledge.company_id == current_user.company_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    chunks = get_chunks_by_knowledge(db, item.id)
    return KnowledgeDetail(
        id=item.id,
        company_id=item.company_id,
        name=item.name,
        description=item.description or "",
        source_type=item.source_type or "text",
        chunks=chunks,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/")
async def create_knowledge(
    body: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeResponse:
    item = Knowledge(
        company_id=current_user.company_id,
        name=body.name,
        description=body.description,
        source_type="text",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    provider = get_secret("DEFAULT_AI_PROVIDER", "openai")
    api_key = get_secret("DEFAULT_AI_API_KEY", "")
    model = "text-embedding-3-small"

    chunks_saved = await upsert_knowledge(
        db, current_user.company_id, item.id, body.content,
        provider=provider, api_key=api_key, embedding_model=model,
    )

    return KnowledgeResponse(
        id=item.id,
        company_id=item.company_id,
        name=item.name,
        description=item.description or "",
        source_type=item.source_type or "text",
        chunk_count=chunks_saved,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.patch("/{knowledge_id}")
async def update_knowledge(
    knowledge_id: int,
    body: KnowledgeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeResponse:
    item = (
        db.query(Knowledge)
        .filter(Knowledge.id == knowledge_id, Knowledge.company_id == current_user.company_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")

    if body.name is not None:
        item.name = body.name
    if body.description is not None:
        item.description = body.description
    db.commit()

    if body.content is not None:
        provider = get_secret("DEFAULT_AI_PROVIDER", "openai")
        api_key = get_secret("DEFAULT_AI_API_KEY", "")
        model = "text-embedding-3-small"
        await upsert_knowledge(
            db, current_user.company_id, item.id, body.content,
            provider=provider, api_key=api_key, embedding_model=model,
        )

    chunks = get_chunks_by_knowledge(db, item.id)
    return KnowledgeResponse(
        id=item.id,
        company_id=item.company_id,
        name=item.name,
        description=item.description or "",
        source_type=item.source_type or "text",
        chunk_count=len(chunks),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/{knowledge_id}")
def delete_knowledge(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = (
        db.query(Knowledge)
        .filter(Knowledge.id == knowledge_id, Knowledge.company_id == current_user.company_id)
        .first()
    )
    if not item:
        raise HTTPException(status_code=404, detail="Knowledge not found")
    delete_knowledge_chunks(db, item.id)
    db.delete(item)
    db.commit()
    return {"detail": "deleted"}


@router.post("/search")
async def search_knowledge(
    body: KnowledgeSearch,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[SearchResult]:
    from app.models.company_config import CompanyConfig

    config = db.query(CompanyConfig).filter(
        CompanyConfig.company_id == current_user.company_id
    ).first()

    provider = "openai"
    api_key = ""
    model = "text-embedding-3-small"

    if config:
        if config.ai_provider:
            provider = config.ai_provider
        if config.ai_api_key:
            from app.services.field_crypto import decrypt_field
            api_key = decrypt_field(config.ai_api_key)

    results = await search_similar(
        db, current_user.company_id, body.query,
        provider=provider, api_key=api_key, embedding_model=model,
        top_k=body.top_k,
    )

    return [SearchResult(**r) for r in results]
