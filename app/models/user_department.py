"""Associacao usuario <-> setor com nivel de acesso (Fase 8.9).

Niveis por setor (ordem crescente):
- view: apenas visualiza conversas do setor
- attend: visualiza, responde e assume conversas do setor (padrao)
- manage: tudo de attend + reservado para gestao/transferencia do setor
"""
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class UserDepartment(Base):
    """Usuario pertence a um setor com um nivel de acesso."""

    __tablename__ = "user_departments"
    __table_args__ = (
        UniqueConstraint("user_id", "department_id", name="uq_user_department"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    department_id = Column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    level = Column(String(20), nullable=False, default="attend")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    department = relationship("Department")