from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PendingFlow(Base):
    """Estado de um fluxo aguardando a proxima mensagem no WhatsApp.

    Quando um fluxo encontra o no `wait_until_message`, o motor salva um
    snapshot (contexto + proximo no a executar) aqui, marcado pelo numero
    do cliente e empresa. Quando a proxima mensagem chega pelo webhook,
    o fluxo e retomado a partir desse ponto.
    """

    __tablename__ = "pending_flows"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False, index=True)
    execution_id = Column(Integer, ForeignKey("executions.id"), nullable=False, index=True)

    # numero do cliente no WhatsApp (sem "@s.whatsapp.net")
    phone = Column(String, nullable=False, index=True)

    # snapshot do contexto e do proximo nó a executar
    # {"data": {...}, "next_node_id": "..."}
    snapshot = Column(JSON, default=dict)

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)
