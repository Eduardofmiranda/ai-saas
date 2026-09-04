from sqlalchemy.orm import Session

from app.config import get_secret
from app.models.company_config import CompanyConfig
from app.services.field_crypto import decrypt_field


def resolve_ai_config(config: CompanyConfig | None) -> dict[str, str]:
    """Resolve IA em um unico ponto, com a empresa sobrepondo o .env.

    Campos vazios em ``company_configs`` significam que os ``DEFAULT_AI_*`` do
    deploy continuam sendo a fonte de verdade. Isso impede que caminhos
    individuais inventem provedores ou modelos próprios.
    """
    return {
        "provider": (
            (config.ai_provider if config else "")
            or get_secret("DEFAULT_AI_PROVIDER")
            or "groq"
        ),
        "model": (
            (config.ai_model if config else "")
            or get_secret("DEFAULT_AI_MODEL")
        ),
        "api_key": (
            decrypt_field(config.ai_api_key) if config else ""
        ) or get_secret("DEFAULT_AI_API_KEY"),
        "base_url": (
            decrypt_field(config.ai_base_url) if config else ""
        ) or get_secret("DEFAULT_AI_BASE_URL"),
    }


def resolve_embedding_config() -> dict[str, str]:
    """Resolve embeddings independentemente do provedor de chat.

    Modelos de conversa e modelos de embeddings possuem contratos diferentes.
    Por isso a Knowledge nunca herda implicitamente uma chave/modelo de chat.
    """
    return {
        "provider": get_secret("DEFAULT_EMBEDDING_PROVIDER") or "openai",
        "model": get_secret("DEFAULT_EMBEDDING_MODEL") or "text-embedding-3-small",
        "api_key": get_secret("DEFAULT_EMBEDDING_API_KEY"),
        "base_url": get_secret("DEFAULT_EMBEDDING_BASE_URL"),
    }


def get_or_create_config(db: Session, company_id: int) -> CompanyConfig:
    """Retorna a configuracao da empresa, criando com defaults se nao existir."""
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
