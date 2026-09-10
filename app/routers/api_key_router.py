from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User
from app.services.api_key_auth import generate_api_key
from app.services.deps import get_current_user

router = APIRouter(
    prefix="/api-keys",
    tags=["API Keys"],
)


class ApiKeyCreate(BaseModel):
    name: str
    scopes: str = "read"


class ApiKeyCreatedResponse(BaseModel):
    id: int
    name: str
    key: str
    key_prefix: str
    message: str


@router.get("/")
def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    keys = (
        db.query(ApiKey)
        .filter(ApiKey.company_id == current_user.company_id)
        .order_by(ApiKey.id.desc())
        .all()
    )
    return [
        {
            "id": k.id,
            "company_id": k.company_id,
            "name": k.name,
            "key_prefix": k.key_prefix,
            "scopes": k.scopes,
            "active": k.active,
            "last_used_at": k.last_used_at.isoformat() if k.last_used_at else None,
            "expires_at": k.expires_at.isoformat() if k.expires_at else None,
            "created_at": k.created_at.isoformat() if k.created_at else None,
        }
        for k in keys
    ]


@router.post("/", response_model=ApiKeyCreatedResponse, status_code=201)
def create_api_key(
    body: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    raw_key, key_hash, key_prefix = generate_api_key()

    existing = db.query(ApiKey).filter(ApiKey.company_id == current_user.company_id).count()
    if existing >= 10:
        raise HTTPException(status_code=400, detail="Maximo de 10 API keys por empresa")

    ak = ApiKey(
        company_id=current_user.company_id,
        name=body.name,
        key_hash=key_hash,
        key_prefix=key_prefix,
        scopes=body.scopes,
    )
    db.add(ak)
    db.commit()
    db.refresh(ak)

    return {
        "id": ak.id,
        "name": ak.name,
        "key": raw_key,
        "key_prefix": key_prefix,
        "message": "Guarde esta chave. Ela nao sera mostrada novamente.",
    }


@router.patch("/{key_id}")
def update_api_key(
    key_id: int,
    active: bool | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ak = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.company_id == current_user.company_id)
        .first()
    )
    if not ak:
        raise HTTPException(status_code=404, detail="API key nao encontrada")
    if active is not None:
        ak.active = active
    db.commit()
    return {"ok": True}


@router.delete("/{key_id}")
def delete_api_key(
    key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ak = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.company_id == current_user.company_id)
        .first()
    )
    if not ak:
        raise HTTPException(status_code=404, detail="API key nao encontrada")
    db.delete(ak)
    db.commit()
    return {"ok": True}
