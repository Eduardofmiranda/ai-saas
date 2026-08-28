from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.database.database import Base

if TYPE_CHECKING:
    from app.models.execution import Execution


def _utcnow():
    return datetime.now(timezone.utc)


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    name = Column(String, nullable=False)
    description = Column(Text, default="")

    # Grafo do fluxo (formato do editor): {"nodes": [...], "edges": [...]}
    data = Column(JSON, default=dict)

    # Tipo de disparo principal: message | webhook | cron | manual
    trigger_type = Column(String, default="message")
    # Configuracao do trigger (ex: numero do WhatsApp, cron, endpoint)
    trigger_config = Column(JSON, default=dict)

    active = Column(Boolean, nullable=False, default=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    company = relationship("Company")
    executions = relationship("Execution", back_populates="workflow")
