from sqlalchemy.orm import Session

from app.config import get_secret
from app.models.company_config import CompanyConfig
from app.services.field_crypto import decrypt_field
from app.services.platform_ai_provider_service import (
    decrypt_platform_api_key,
    get_platform_provider,
)


def resolve_ai_config(
    config: CompanyConfig | None,
    db: Session | None = None,
) -> dict[str, str]:
    """Resolve a IA sem reutilizar uma chave de outro provedor.

    Ordem: override da empresa -> credencial global do mesmo provedor -> .env
    do provedor padrão. O .env não é usado para autenticar outro provedor.
    """
    default_provider = get_secret("DEFAULT_AI_PROVIDER") or "groq"
    provider = ((config.ai_provider if config else "") or default_provider).lower().strip()
    platform_provider = get_platform_provider(db, provider)

    company_key = decrypt_field(config.ai_api_key) if config else ""
    company_base_url = decrypt_field(config.ai_base_url) if config else ""
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

    resolved = {
        "provider": provider,
        "model": (
            (config.ai_model if config else "")
            or (platform_provider.model if platform_provider else "")
            or (get_secret("DEFAULT_AI_MODEL") if is_environment_provider else "")
        ),
        "api_key": company_key or platform_key or environment_key,
        "base_url": (
            company_base_url
            or (platform_provider.base_url if platform_provider else "")
            or environment_base_url
        ),
    }
    # Compatibilidade: chamadas antigas sem sessão continuam recebendo o
    # contrato original. As rotas e execuções reais sempre passam ``db``.
    if db is not None:
        resolved["credential_source"] = credential_source
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