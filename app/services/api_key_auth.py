import hashlib
import secrets
from datetime import datetime, timezone

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.api_key import ApiKey
from app.models.user import User


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def generate_api_key() -> tuple[str, str, str]:
    raw = f"fai_{secrets.token_urlsafe(32)}"
    return raw, _hash_key(raw), raw[:12]


async def get_current_user_by_api_key(
    x_api_key: str = Header(default=""),
    db: Session = Depends(get_db),
) -> User:
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key obrigatoria (header X-API-Key)")

    key_hash = _hash_key(x_api_key)
    api_key = db.query(ApiKey).filter(ApiKey.key_hash == key_hash).first()

    if not api_key or not api_key.active:
        raise HTTPException(status_code=401, detail="API key invalida ou inativa")

    if api_key.expires_at and api_key.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="API key expirada")

    api_key.last_used_at = datetime.now(timezone.utc)
    db.commit()

    from app.models.user import User as UserModel
    user = db.query(UserModel).filter(UserModel.company_id == api_key.company_id, UserModel.role == "owner").first()
    if not user:
        user = db.query(UserModel).filter(UserModel.company_id == api_key.company_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Empresa sem usuarios")

    return user
