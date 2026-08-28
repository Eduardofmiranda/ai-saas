from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    JSON,
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
    from app.models.workflow import Workflow


def _utcnow():
    return datetime.now(timezone.utc)


class Execution(Base):
    __tablename__ = "executions"

    id = Column(Integer, primary_key=True, index=True)

    workflow_id = Column(
        Integer,
        ForeignKey("workflows.id"),
        nullable=False,
        index=True,
    )

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    # status: pending | running | success | error | canceled
    status = Column(String, nullable=False, default="pending")

    # Contexto compartilhado da execucao (mensagem de entrada, variaveis, etc)
    context = Column(JSON, default=dict)

    # Resultados acumulados por no: {node_id: {output: ..., error: ...}}
    node_results = Column(JSON, default=dict)

    error = Column(Text, default="")

    started_at = Column(DateTime(timezone=True), default=None, nullable=True)
    finished_at = Column(DateTime(timezone=True), default=None, nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    workflow = relationship("Workflow", back_populates="executions")
