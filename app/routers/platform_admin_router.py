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