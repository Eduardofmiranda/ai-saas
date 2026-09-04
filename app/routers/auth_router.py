import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.config import get_secret
from app.database.session import get_db
from app.models.company import Company
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.schemas.auth_schema import (
    ChangePasswordRequest,
    ForgotPasswordRequest,
    LoginResponse,
    RefreshRequest,
    RegisterRequest,
    ResetPasswordRequest,
)
from app.schemas.user_schema import UserResponse
from app.services import email_service
from app.services.deps import get_current_user
from app.services.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


def _rate_limit_login():
    """Aplica rate limit no login se slowapi estiver disponivel."""
    try:
        from app.main import limiter
        return limiter.limit("5/minute")
    except (ImportError, AttributeError):
        return lambda func: func


def _rate_limit_recovery():
    """Rate limit do fluxo de recuperacao de senha (anti-spam de email)."""
    try:
        from app.main import limiter
        return limiter.limit("10/minute")
    except (ImportError, AttributeError):
        return lambda func: func


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _as_utc(dt):
    """Normaliza datetime (naive ou aware) para UTC aware (SQLite x Postgres)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _build_login_response(user: User) -> LoginResponse:
    access = create_access_token(str(user.id), {"company_id": user.company_id})
    refresh = create_refresh_token(str(user.id), {"company_id": user.company_id})
    return LoginResponse(
        access_token=access,
        refresh_token=refresh,
        user_id=user.id,
        company_id=user.company_id,
        name=user.name,
        email=user.email,
        role=user.role,
    )


@_rate_limit_login()
@router.post("/register", response_model=LoginResponse)
def register(
    request: Request,
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    existing = db.query(User).filter(User.email == data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email ja cadastrado")

    company = Company(name=data.company_name)
    db.add(company)
    db.flush()

    user = User(
        company_id=company.id,
        name=data.name,
        email=data.email,
        role="owner",
    )
    user.set_password(data.password)
    db.add(user)
    db.commit()
    db.refresh(user)

    return _build_login_response(user)


@_rate_limit_login()
@router.post("/login", response_model=LoginResponse)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    return _build_login_response(user)


@router.get("/me", response_model=UserResponse)
def me(
    current_user: User = Depends(get_current_user),
):
    """Retorna os dados do usuario logado (usado no reload para restaurar role)."""
    return current_user


@router.post("/change-password")
def change_password(
    data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Altera a senha do usuario logado (exige a senha atual)."""
    if not verify_password(data.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres")
    current_user.set_password(data.new_password)
    db.commit()
    return {"message": "Senha alterada com sucesso"}


@router.post("/refresh", response_model=LoginResponse)
def refresh(
    data: RefreshRequest,
    db: Session = Depends(get_db),
):
    """Troca um refresh token por um novo par (access + refresh rotacionado)."""
    payload = decode_access_token(data.refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Refresh token invalido")
    user = db.query(User).filter(User.id == int(payload["sub"])).first()
    if not user:
        raise HTTPException(status_code=401, detail="Refresh token invalido")
    return _build_login_response(user)


@_rate_limit_recovery()
@router.post("/forgot-password")
def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """Cria um token de recuperacao e envia o link por email."""
    if not email_service.email_is_configured():
        raise HTTPException(status_code=503, detail="Servico de email nao configurado")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # Resposta generica para nao expor quais emails estao cadastrados.
        return {"message": "Se o email estiver cadastrado, voce recebera um link de recuperacao"}

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(
        minutes=int(get_secret("PASSWORD_RESET_TOKEN_EXPIRE_MINUTES", "60"))
    )
    db.add(
        PasswordResetToken(
            user_id=user.id,
            company_id=user.company_id,
            token_hash=_hash_token(token),
            expires_at=expires_at,
        )
    )
    db.commit()

    frontend_url = get_secret("FRONTEND_URL", "http://localhost:5173").rstrip("/")
    reset_url = f"{frontend_url}/reset-password?token={token}"
    email_service.send_reset_email(user.email, reset_url)
    return {"message": "Se o email estiver cadastrado, voce recebera um link de recuperacao"}


@router.post("/reset-password")
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """Redefine a senha usando o token recebido por email (uso unico)."""
    record = (
        db.query(PasswordResetToken)
        .filter(PasswordResetToken.token_hash == _hash_token(data.token))
        .first()
    )
    if not record:
        raise HTTPException(status_code=400, detail="Link de recuperacao invalido")
    if record.used_at:
        raise HTTPException(status_code=400, detail="Este link ja foi utilizado")
    now = datetime.now(timezone.utc)
    if _as_utc(record.expires_at) < now:
        raise HTTPException(status_code=400, detail="Este link expirou")
    if len(data.new_password) < 6:
        raise HTTPException(status_code=400, detail="A nova senha deve ter pelo menos 6 caracteres")

    user = db.query(User).filter(User.id == record.user_id).first()
    if not user:
        raise HTTPException(status_code=400, detail="Usuario nao encontrado")

    user.set_password(data.new_password)
    record.used_at = now
    db.commit()
    return {"message": "Senha redefinida com sucesso"}
