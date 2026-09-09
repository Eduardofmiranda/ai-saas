"""Registro de auditoria (audit log).

Registra acoes criticas no sistema: login, CRUD de usuarios/workflows,
alteracoes de config, etc. Cada registro armazena: quem, o que, onde,
quando e detalhes (JSON).
"""
from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class AuditLog(Base):
    """Registro de auditoria por empresa."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )

    action = Column(String(100), nullable=False, index=True)
    # ex.: "user.create", "config.update", "workflow.delete", "auth.login"

    entity = Column(String(100), nullable=True)
    # ex.: "user", "workflow", "config", "conversation"

    entity_id = Column(Integer, nullable=True)

    details = Column(Text, default="")
    # JSON string com campos alterados, valores antigos/novos, etc.

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow, index=True)
