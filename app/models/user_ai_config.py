from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class UserAIConfig(Base):
    """Politica de IA atribuida pelo superadmin a cada usuario.

    allowed_providers: JSON array de provedores liberados (ex: ["groq","openai"]).
    default_provider: provedor padrao entre os liberados.
    default_model: modelo padrao para o provedor padrao.
    """

    __tablename__ = "user_ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    allowed_providers = Column(Text, nullable=False, default="[]")
    default_provider = Column(String, nullable=False, default="")
    default_model = Column(String, nullable=False, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    user = relationship("User", foreign_keys=[user_id])
    creator = relationship("User", foreign_keys=[created_by])
