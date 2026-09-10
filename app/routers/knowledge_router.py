from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.models.knowledge import Knowledge
from app.models.department import Department
from app.models.user import User
from app.schemas.knowledge_schema import (
    KnowledgeCreate,
    KnowledgeDetail,
    KnowledgeResponse,
    KnowledgeSearch,
    KnowledgeUpdate,
    SearchResult,
)
from app.services.deps import get_current_user, require_company_manager
from app.services import access_rules
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


def _validate_department(db: Session, company_id: int, department_id: int | None) -> None:
    if department_id is None:
        return
    exists = db.query(Department.id).filter(
        Department.id == department_id,
        Department.company_id == company_id,
    ).first()
    if not exists:
        raise HTTPException(status_code=422, detail="Setor invalido para esta empresa")


def _get_visible_knowledge(db: Session, knowledge_id: int, user: User) -> Knowledge:
    item = db.query(Knowledge).filter(
        Knowledge.id == knowledge_id,
        Knowledge.company_id == user.company_id,
    ).first()
    if not item or not access_rules.can_view_department(db, user, item.department_id):
        raise HTTPException(status_code=404, detail="Knowledge not found")
    return item


@router.get("/")
def list_knowledge(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
) -> dict:
    query = db.query(Knowledge).filter(Knowledge.company_id == current_user.company_id)
    visible = access_rules.visible_department_condition(Knowledge, db, current_user)
    if visible is not None:
        query = query.filter(visible)
    if q and q.strip():
        ql = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Knowledge.name.ilike(ql),
                Knowledge.description.ilike(ql),
            )
        )
    total = query.count()
    items = query.order_by(Knowledge.created_at.desc()).offset(offset).limit(limit).all()
    result = []
    for item in items:
        chunks = get_chunks_by_knowledge(db, item.id)
        result.append(KnowledgeResponse(
            id=item.id,
            company_id=item.company_id,
            name=item.name,
            description=item.description or "",
            source_type=item.source_type or "text",
            department_id=item.department_id,
            chunk_count=len(chunks),
            created_at=item.created_at,
            updated_at=item.updated_at,
        ))
    return {"total": total, "items": result}


@router.get("/{knowledge_id}")
def get_knowledge(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> KnowledgeDetail:
    item = _get_visible_knowledge(db, knowledge_id, current_user)
    chunks = get_chunks_by_knowledge(db, item.id)
    return KnowledgeDetail(
        id=item.id,
        company_id=item.company_id,
        name=item.name,
        description=item.description or "",
        source_type=item.source_type or "text",
        department_id=item.department_id,
        chunks=chunks,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/")
async def create_knowledge(
    body: KnowledgeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_manager),
) -> KnowledgeResponse:
    _validate_department(db, current_user.company_id, body.department_id)
    item = Knowledge(
        company_id=current_user.company_id,
        name=body.name,
        description=body.description,
        source_type="text",
        department_id=body.department_id,
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
        department_id=item.department_id,
        chunk_count=chunks_saved,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.post("/upload")
async def upload_knowledge(
    file: UploadFile = File(...),
    name: str | None = None,
    description: str = "",
    department_id: int | None = Form(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_manager),
) -> KnowledgeResponse:
    """Upload de arquivo (PDF, DOCX, TXT, CSV, Markdown) para a base de conhecimento."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Arquivo invalido")

    data = await file.read()

    try:
        content = parse_file(file.filename, data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    _validate_department(db, current_user.company_id, department_id)
    item = Knowledge(
        company_id=current_user.company_id,
        name=name or file.filename,
        description=description,
        source_type="file",
        department_id=department_id,
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
        department_id=item.department_id,
        chunk_count=chunks_saved,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.patch("/{knowledge_id}")
async def update_knowledge(
    knowledge_id: int,
    body: KnowledgeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_manager),
) -> KnowledgeResponse:
    item = _get_visible_knowledge(db, knowledge_id, current_user)

    if body.name is not None:
        item.name = body.name
    if body.description is not None:
        item.description = body.description
    if body.department_id is not None or "department_id" in body.model_fields_set:
        _validate_department(db, current_user.company_id, body.department_id)
        item.department_id = body.department_id
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
        department_id=item.department_id,
        chunk_count=len(chunks),
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


@router.delete("/{knowledge_id}")
def delete_knowledge(
    knowledge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_company_manager),
):
    item = _get_visible_knowledge(db, knowledge_id, current_user)
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
    department_ids = access_rules.user_department_ids(db, current_user)

    results = await search_similar(
        db, current_user.company_id, body.query,
        provider=embedding_config["provider"], api_key=embedding_config["api_key"],
        embedding_model=embedding_config["model"], base_url=embedding_config["base_url"], top_k=body.top_k,
        department_ids=department_ids,
    )

    return [SearchResult(**r) for r in results]
