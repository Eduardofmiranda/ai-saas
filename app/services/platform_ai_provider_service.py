"""Leitura segura das credenciais de IA mantidas pela plataforma."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.platform_ai_provider import PlatformAIProvider
from app.services.field_crypto import decrypt_field


def get_platform_provider(db: Session | None, provider: str | None) -> PlatformAIProvider | None:
    if db is None or not provider:
        return None
    return (
        db.query(PlatformAIProvider)
        .filter(
            PlatformAIProvider.provider == provider.lower().strip(),
            PlatformAIProvider.enabled.is_(True),
        )
        .first()
    )


def provider_public_dict(record: PlatformAIProvider) -> dict:
    """Representação administrativa sem jamais devolver a chave."""
    return {
        "provider": record.provider,
        "model": record.model,
        "base_url": record.base_url,
        "enabled": record.enabled,
        "has_api_key": bool(record.api_key),
        "credential_source": "platform",
    }


def decrypt_platform_api_key(record: PlatformAIProvider | None) -> str:
    return decrypt_field(record.api_key) if record else ""