"""Administração exclusiva do operador da plataforma.

As rotas deste módulo nunca são protegidas por ``owner``/``admin`` de empresa.
"""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.company import Company
from app.models.execution import Execution
from app.models.platform_ai_provider import PlatformAIProvider
from app.models.user import User
from app.models.workflow import Workflow
from app.services import llm
from app.services.deps import get_current_platform_admin
from app.services.field_crypto import encrypt_field
from app.services.platform_access import is_platform_admin
from app.services.platform_ai_provider_service import (
    decrypt_platform_api_key,
    provider_public_dict,
)

router = APIRouter(prefix="/platform-admin", tags=["Platform administration"])
_ALLOWED_PROVIDERS = set(llm.PROVIDER_DEFAULTS)


class ProviderUpdate(BaseModel):
    model: str | None = Field(default=None, max_length=200)
    base_url: str | None = Field(default=None, max_length=500)
    api_key: str | None = Field(default=None, max_length=1000)
    enabled: bool | None = None


def _require_provider(provider: str) -> str:
    normalized = provider.strip().lower()
    if normalized not in _ALLOWED_PROVIDERS:
        raise HTTPException(status_code=400, detail="Provedor de IA não suportado")
    return normalized


def _provider_or_404(db: Session, provider: str) -> PlatformAIProvider:
    record = db.query(PlatformAIProvider).filter(PlatformAIProvider.provider == provider).first()
    if not record:
        raise HTTPException(status_code=404, detail="Provedor não cadastrado na plataforma")
    return record


@router.get("/overview")
def overview(
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    """Resumo global sem credenciais, conteúdo de conversa ou prompts."""
    providers = db.query(PlatformAIProvider).order_by(PlatformAIProvider.provider).all()
    return {
        "companies": db.query(Company).count(),
        "users": db.query(User).count(),
        "workflows": db.query(Workflow).count(),
        "executions": db.query(Execution).count(),
        "executions_error": db.query(Execution).filter(Execution.status == "error").count(),
        "providers": [provider_public_dict(item) for item in providers],
        "usage_tracking": "planned",
        "active_sessions": "not_tracked",
    }


@router.get("/errors")
def list_errors(
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
    company_id: int | None = None,
    workflow_id: int | None = None,
):
    """Lista execuções com erro (painel de erros do superadmin)."""
    q = (
        db.query(Execution, Workflow.name.label("workflow_name"), Company.name.label("company_name"))
        .join(Workflow, Workflow.id == Execution.workflow_id)
        .join(Company, Company.id == Execution.company_id)
        .filter(Execution.status == "error")
    )
    if company_id is not None:
        q = q.filter(Execution.company_id == company_id)
    if workflow_id is not None:
        q = q.filter(Execution.workflow_id == workflow_id)
    total = q.count()
    rows = q.order_by(Execution.created_at.desc()).offset(offset).limit(limit).all()
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": [
            {
                "id": ex.id,
                "workflow_id": ex.workflow_id,
                "workflow_name": wf_name,
                "company_id": ex.company_id,
                "company_name": co_name,
                "error": ex.error,
                "started_at": ex.started_at.isoformat() if ex.started_at else None,
                "finished_at": ex.finished_at.isoformat() if ex.finished_at else None,
                "created_at": ex.created_at.isoformat() if ex.created_at else None,
            }
            for ex, wf_name, co_name in rows
        ],
    }


@router.delete("/errors")
def clear_errors(
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    """Remove todas as execuções com erro."""
    count = db.query(Execution).filter(Execution.status == "error").delete(synchronize_session=False)
    db.commit()
    return {"deleted": count}


@router.get("/users")
def list_platform_users(
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    rows = (
        db.query(User, Company.name.label("company_name"))
        .join(Company, Company.id == User.company_id)
        .order_by(User.id.desc())
        .all()
    )
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "company_id": user.company_id,
            "company_name": company_name,
            "role": user.role,
            "is_platform_admin": is_platform_admin(user),
        }
        for user, company_name in rows
    ]


@router.get("/providers")
def list_providers(
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    records = {
        item.provider: item
        for item in db.query(PlatformAIProvider).order_by(PlatformAIProvider.provider).all()
    }
    result = []
    for provider, defaults in llm.PROVIDER_DEFAULTS.items():
        record = records.get(provider)
        if record:
            result.append(provider_public_dict(record))
        else:
            result.append(
                {
                    "provider": provider,
                    "model": defaults.get("model", ""),
                    "base_url": defaults.get("base_url", ""),
                    "enabled": False,
                    "has_api_key": False,
                    "credential_source": "not_configured",
                }
            )
    return result


@router.put("/providers/{provider}")
def save_provider(
    provider: str,
    data: ProviderUpdate,
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    provider = _require_provider(provider)
    record = db.query(PlatformAIProvider).filter(PlatformAIProvider.provider == provider).first()
    if not record:
        record = PlatformAIProvider(provider=provider)
        db.add(record)

    updates = data.model_dump(exclude_unset=True)
    if "model" in updates:
        record.model = (updates["model"] or "").strip()
    if "base_url" in updates:
        record.base_url = (updates["base_url"] or "").strip()
    if "enabled" in updates:
        record.enabled = updates["enabled"]
    if "api_key" in updates and updates["api_key"]:
        record.api_key = encrypt_field(updates["api_key"].strip())

    db.commit()
    db.refresh(record)
    return provider_public_dict(record)


@router.post("/providers/{provider}/balance")
async def provider_balance(
    provider: str,
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    """Consulta saldo apenas quando o provedor fornece um endpoint oficial.

    Não tenta converter dinheiro em 'tokens restantes': essa equivalência não é
    estável e seria enganosa.
    """
    provider = _require_provider(provider)
    record = _provider_or_404(db, provider)
    api_key = decrypt_platform_api_key(record)
    if not api_key:
        raise HTTPException(status_code=400, detail="O provedor não possui chave cadastrada")
    if provider != "deepseek":
        return {
            "available": None,
            "detail": "Este provedor não expõe saldo por uma API compatível. O painel mostrará uso observado quando o rastreamento estiver ativo.",
        }

    base_url = (record.base_url or llm.PROVIDER_DEFAULTS[provider]["base_url"]).rstrip("/")
    # O endpoint oficial do DeepSeek não fica sob /v1.
    if base_url.endswith("/v1"):
        base_url = base_url[:-3]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{base_url}/user/balance",
                headers={"Authorization": f"Bearer {api_key}"},
            )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(status_code=502, detail=f"DeepSeek recusou a consulta de saldo (HTTP {exc.response.status_code})") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Não foi possível consultar o saldo do DeepSeek") from exc

    return {
        "available": bool(payload.get("is_available")),
        "balances": [
            {
                "currency": item.get("currency"),
                "total_balance": item.get("total_balance"),
                "granted_balance": item.get("granted_balance"),
                "topped_up_balance": item.get("topped_up_balance"),
            }
            for item in (payload.get("balance_infos") or [])
            if isinstance(item, dict)
        ],
    }


# ---------------------------------------------------------------------------
# Politica de IA por usuario
# ---------------------------------------------------------------------------

import json

from app.models.user_ai_config import UserAIConfig


class UserAIConfigUpdate(BaseModel):
    allowed_providers: list[str] | None = None
    default_provider: str | None = None
    default_model: str | None = None


def _user_ai_config_dict(uc: UserAIConfig) -> dict:
    return {
        "user_id": uc.user_id,
        "allowed_providers": json.loads(uc.allowed_providers or "[]"),
        "default_provider": uc.default_provider,
        "default_model": uc.default_model,
        "created_by": uc.created_by,
        "updated_at": uc.updated_at.isoformat() if uc.updated_at else None,
    }


@router.get("/user-ai-config")
def list_user_ai_configs(
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    """Lista politicas de IA de todos os usuarios."""
    rows = (
        db.query(UserAIConfig, User.email, User.name)
        .join(User, User.id == UserAIConfig.user_id)
        .order_by(User.id)
        .all()
    )
    result = []
    for uc, email, name in rows:
        d = _user_ai_config_dict(uc)
        d["email"] = email
        d["name"] = name
        result.append(d)
    return result


@router.get("/user-ai-config/{user_id}")
def get_user_ai_config(
    user_id: int,
    _: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    """Retorna a politica de IA de um usuario especifico."""
    uc = db.query(UserAIConfig).filter(UserAIConfig.user_id == user_id).first()
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")
    if not uc:
        return {
            "user_id": user_id,
            "email": user.email,
            "name": user.name,
            "allowed_providers": [],
            "default_provider": "",
            "default_model": "",
        }
    d = _user_ai_config_dict(uc)
    d["email"] = user.email
    d["name"] = user.name
    return d


@router.put("/user-ai-config/{user_id}")
def save_user_ai_config(
    user_id: int,
    data: UserAIConfigUpdate,
    admin: User = Depends(get_current_platform_admin),
    db: Session = Depends(get_db),
):
    """Cria ou atualiza a politica de IA de um usuario (superadmin)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    uc = db.query(UserAIConfig).filter(UserAIConfig.user_id == user_id).first()
    if not uc:
        uc = UserAIConfig(user_id=user_id, created_by=admin.id)
        db.add(uc)

    if data.allowed_providers is not None:
        invalid = [p for p in data.allowed_providers if p not in _ALLOWED_PROVIDERS]
        if invalid:
            raise HTTPException(status_code=400, detail=f"Provedores nao suportados: {invalid}")
        uc.allowed_providers = json.dumps(data.allowed_providers)

    if data.default_provider is not None:
        uc.default_provider = data.default_provider

    if data.default_model is not None:
        uc.default_model = data.default_model

    db.commit()
    db.refresh(uc)
    d = _user_ai_config_dict(uc)
    d["email"] = user.email
    d["name"] = user.name
    return d