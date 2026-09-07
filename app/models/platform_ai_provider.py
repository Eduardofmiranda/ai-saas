from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PlatformAIProvider(Base):
    """Credencial de IA administrada pela plataforma, nunca exposta pela API."""

    __tablename__ = "platform_ai_providers"

    id = Column(Integer, primary_key=True, index=True)
    provider = Column(String, nullable=False, unique=True, index=True)
    model = Column(String, nullable=False, default="")
    api_key = Column(Text, nullable=False, default="")
    base_url = Column(String, nullable=False, default="")
    enabled = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)