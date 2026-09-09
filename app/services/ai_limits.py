"""Limites de abuso de IA por empresa.

Verifica e aplica limites de uso diario de IA (mensagens, tokens) por empresa.
Acompanha: CompanyConfig (limites) + CompanyAIUsage (contadores diarios).
"""
from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Session

from app.database.database import Base
from app.models.company_config import CompanyConfig


# ---------------------------------------------------------------------------
# Model: uso diario de IA por empresa
# ---------------------------------------------------------------------------

class CompanyAIUsage(Base):
    """Contadores de uso diario de IA por empresa."""

    __tablename__ = "company_ai_usage"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )
    usage_date = Column(Date, nullable=False, index=True)
    message_count = Column(Integer, nullable=False, default=0)
    token_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        {"sqlite_autoincrement": True},
    )


# ---------------------------------------------------------------------------
# Limites padrao (quando nao configurado)
# ---------------------------------------------------------------------------

_DEFAULTS = {
    "ai_daily_message_limit": 0,    # 0 = ilimitado
    "ai_daily_token_limit": 0,      # 0 = ilimitado
    "ai_timeout_seconds": 40,
    "ai_max_retries": 2,
    "ai_fallback_message": (
        "Desculpe, estou temporariamente indisponivel. "
        "Por favor, tente novamente em alguns minutos."
    ),
}


def _get_limit(config: CompanyConfig | None, field: str) -> int | str:
    """Retorna o valor do limite do config, ou o default."""
    if config is None:
        return _DEFAULTS.get(field, 0)
    val = getattr(config, field, None)
    if val is None or val == "":
        return _DEFAULTS.get(field, 0)
    return val


# ---------------------------------------------------------------------------
# Checagem de limites
# ---------------------------------------------------------------------------

class LimitExceeded(Exception):
    """Levantado quando o uso diario excede o limite configurado."""

    def __init__(self, limit_type: str, message: str | None = None):
        self.limit_type = limit_type
        self.message = message or "Limite de uso de IA atingido."


def check_ai_limits(db: Session, company_id: int, config: CompanyConfig | None = None) -> None:
    """Verifica se a empresa excedeu os limites de uso diario de IA.

    Levanta LimitExceeded se o limite for atingido. Nao faz nada se
    os limites forem 0 (ilimitado).
    """
    daily_msg_limit = int(_get_limit(config, "ai_daily_message_limit"))
    daily_token_limit = int(_get_limit(config, "ai_daily_token_limit"))

    if daily_msg_limit <= 0 and daily_token_limit <= 0:
        return  # ilimitado

    today = date.today()
    usage = (
        db.query(CompanyAIUsage)
        .filter(
            CompanyAIUsage.company_id == company_id,
            CompanyAIUsage.usage_date == today,
        )
        .first()
    )

    if usage is None:
        return  # primeiro uso do dia, tudo liberado

    if daily_msg_limit > 0 and usage.message_count >= daily_msg_limit:
        raise LimitExceeded(
            "messages",
            _get_limit(config, "ai_fallback_message"),
        )

    if daily_token_limit > 0 and usage.token_count >= daily_token_limit:
        raise LimitExceeded(
            "tokens",
            _get_limit(config, "ai_fallback_message"),
        )


# ---------------------------------------------------------------------------
# Registro de uso
# ---------------------------------------------------------------------------

def record_ai_usage(
    db: Session,
    company_id: int,
    *,
    messages: int = 1,
    tokens: int = 0,
) -> None:
    """Registra uso de IA para o dia atual (upsert)."""
    today = date.today()
    usage = (
        db.query(CompanyAIUsage)
        .filter(
            CompanyAIUsage.company_id == company_id,
            CompanyAIUsage.usage_date == today,
        )
        .first()
    )

    if usage is None:
        usage = CompanyAIUsage(
            company_id=company_id,
            usage_date=today,
            message_count=messages,
            token_count=tokens,
        )
        db.add(usage)
    else:
        usage.message_count += messages
        usage.token_count += tokens

    db.commit()


# ---------------------------------------------------------------------------
# Leitura de uso (para endpoints)
# ---------------------------------------------------------------------------

def get_usage_summary(db: Session, company_id: int) -> dict:
    """Retorna o resumo de uso do dia atual."""
    today = date.today()
    usage = (
        db.query(CompanyAIUsage)
        .filter(
            CompanyAIUsage.company_id == company_id,
            CompanyAIUsage.usage_date == today,
        )
        .first()
    )

    return {
        "date": today.isoformat(),
        "message_count": usage.message_count if usage else 0,
        "token_count": usage.token_count if usage else 0,
    }
