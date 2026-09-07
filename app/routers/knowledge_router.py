from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
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
from app.services.config_service import resolve_embedding_config
from app.services.embedding import EmbeddingError
from app.services.file_parser import parse_file

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

    embedding_config = resolve_embedding_config()

    try:
        chunks_saved = await upsert_knowledge(
            db, current_user.company_id, item.id, body.content,
            provider=embedding_config["provider"], api_key=embedding_config["api_key"],
            embedding_model=embedding_config["model"], base_url=embedding_config["base_url"],
        )
    except EmbeddingError as exc:
        db.delete(item)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

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


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    name: str | None = None,
    description: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeResponse:
    """Upload de arquivo (PDF, DOCX, TXT, CSV, Markdown) para a base de conhecimento."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo invalido")

    data = await file.read()

    try:
        content = parse_file(file.filename, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    item = Knowledge(
        company_id=current_user.company_id,
        name=name or file.filename,
        description=description,
        source_type="file",
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    embedding_config = resolve_embedding_config()

    try:
        chunks_saved = await upsert_knowledge(
            db, current_user.company_id, item.id, content,
            provider=embedding_config["provider"], api_key=embedding_config["api_key"],
            embedding_model=embedding_config["model"], base_url=embedding_config["base_url"],
        )
    except EmbeddingError as exc:
        db.delete(item)
        db.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return KnowledgeResponse(
        id=item.id,
        company_id=item.company_id,
        name=item.name,
        description=item.description or "",
        source_type=item.source_type or "file",
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
        embedding_config = resolve_embedding_config()
        try:
            await upsert_knowledge(
                db, current_user.company_id, item.id, body.content,
                provider=embedding_config["provider"], api_key=embedding_config["api_key"],
                embedding_model=embedding_config["model"], base_url=embedding_config["base_url"],
            )
        except EmbeddingError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

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
    embedding_config = resolve_embedding_config()

    results = await search_similar(
        db, current_user.company_id, body.query,
        provider=embedding_config["provider"], api_key=embedding_config["api_key"],
        embedding_model=embedding_config["model"], base_url=embedding_config["base_url"], top_k=body.top_k,
    )

    return [SearchResult(**r) for r in results]
