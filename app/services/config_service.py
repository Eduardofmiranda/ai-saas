import json

from sqlalchemy.orm import Session

from app.config import get_secret
from app.models.company_config import CompanyConfig
from app.models.user_ai_config import UserAIConfig
from app.services.field_crypto import decrypt_field
from app.services.platform_ai_provider_service import (
    decrypt_platform_api_key,
    get_platform_provider,
)


def get_user_ai_config(db: Session, user_id: int) -> UserAIConfig | None:
    """Retorna a politica de IA atribuida ao usuario pelo superadmin."""
    if not user_id:
        return None
    return db.query(UserAIConfig).filter(UserAIConfig.user_id == user_id).first()


def get_user_allowed_providers(db: Session, user_id: int) -> list[str]:
    """Retorna a lista de provedores liberados para o usuario."""
    uc = get_user_ai_config(db, user_id)
    if not uc:
        return []
    try:
        allowed = json.loads(uc.allowed_providers or "[]")
    except (TypeError, json.JSONDecodeError):
        return []
    return [str(provider).strip().lower() for provider in allowed if str(provider).strip()]


def resolve_ai_config(
    config: CompanyConfig | None,
    db: Session | None = None,
    user_id: int | None = None,
) -> dict[str, str]:
    """Resolve a IA com prioridade: usuario → empresa → plataforma → .env.

    1. Se usuario tem politica (UserAIConfig), usa provedor/modelo dela.
       Valida se o provedor esta na lista de permitidos.
    2. Senao, override da empresa (company_configs).
    3. Credencial global do mesmo provedor (platform_ai_providers).
    4. .env do provedor padrao.
    """
    default_provider = get_secret("DEFAULT_AI_PROVIDER") or "groq"

    # 1) Politica do usuario (prioridade maxima)
    user_ai = get_user_ai_config(db, user_id) if db and user_id else None
    user_allowed = get_user_allowed_providers(db, user_id) if user_ai else []

    if user_ai and user_ai.default_provider and user_ai.default_provider.lower().strip() in user_allowed:
        provider = user_ai.default_provider.lower().strip()
    else:
        provider = ((config.ai_provider if config else "") or default_provider).lower().strip()
        if user_allowed and provider not in user_allowed:
            provider = user_allowed[0]

    platform_provider = get_platform_provider(db, provider)

    configured_provider = ((config.ai_provider if config else "") or default_provider).lower().strip()
    # Credenciais/URL de empresa são legadas. Nunca podem acompanhar outro
    # provedor, pois isso vazaria uma chave para uma API diferente.
    company_credentials_match_provider = configured_provider == provider
    company_key = decrypt_field(config.ai_api_key) if config and company_credentials_match_provider else ""
    company_base_url = decrypt_field(config.ai_base_url) if config and company_credentials_match_provider else ""
    platform_key = decrypt_platform_api_key(platform_provider)
    is_environment_provider = provider == default_provider.lower().strip()
    environment_key = get_secret("DEFAULT_AI_API_KEY") if is_environment_provider else ""
    environment_base_url = get_secret("DEFAULT_AI_BASE_URL") if is_environment_provider else ""

    if company_key:
        credential_source = "company"
    elif platform_key:
        credential_source = "platform"
    elif environment_key:
        credential_source = "environment"
    else:
        credential_source = "missing"

    model = (
        (user_ai.default_model if user_ai and user_ai.default_model else "")
        or (config.ai_model if config else "")
        or (platform_provider.model if platform_provider else "")
        or (get_secret("DEFAULT_AI_MODEL") if is_environment_provider else "")
    )

    resolved = {
        "provider": provider,
        "model": model,
        "api_key": company_key or platform_key or environment_key,
        "base_url": (
            company_base_url if company_key else (
                (platform_provider.base_url or "") if platform_key
                else environment_base_url
            )
        ),
    }
    if db is not None:
        resolved["credential_source"] = credential_source
        if user_ai:
            resolved["user_allowed_providers"] = user_allowed
    return resolved


def resolve_embedding_config() -> dict[str, str]:
    """Resolve embeddings independente do provedor de chat."""
    return {
        "provider": get_secret("DEFAULT_EMBEDDING_PROVIDER") or "openai",
        "model": get_secret("DEFAULT_EMBEDDING_MODEL") or "text-embedding-3-small",
        "api_key": get_secret("DEFAULT_EMBEDDING_API_KEY"),
        "base_url": get_secret("DEFAULT_EMBEDDING_BASE_URL"),
    }


def get_or_create_config(db: Session, company_id: int) -> CompanyConfig:
    """Retorna a configuracao da empresa, criando com defaults se não existir."""
    config = (
        db.query(CompanyConfig)
        .filter(CompanyConfig.company_id == company_id)
        .first()
    )
    if not config:
        config = CompanyConfig(company_id=company_id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def get_config(db: Session, company_id: int) -> CompanyConfig | None:
    return (
        db.query(CompanyConfig)
        .filter(CompanyConfig.company_id == company_id)
        .first()
    )