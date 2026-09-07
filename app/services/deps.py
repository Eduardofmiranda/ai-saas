from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.services.security import decode_access_token
from app.services.platform_access import is_platform_admin

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Credenciais invalidas",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    # O endpoint /auth/refresh aceita tokens de longa duracao, mas estes nunca
    # devem autenticar chamadas comuns da API.
    if not payload or payload.get("type") != "access" or not payload.get("sub"):
        raise credentials_exc
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError):
        raise credentials_exc
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise credentials_exc
    return user


def get_current_company(
    current_user: User = Depends(get_current_user),
) -> int:
    return current_user.company_id


def get_current_platform_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    """Exige privilegio global sem reaproveitar o papel da empresa."""
    if not is_platform_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso restrito a administracao da plataforma",
        )
    return current_user
