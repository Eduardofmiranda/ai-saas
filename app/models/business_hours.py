from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class BusinessHours(Base):
    """Horario de atendimento de uma empresa (dias e janelas + mensagem).

    enabled: 1 = respeita o horario configurado; 0 ou ausente = atendimento 24/7.
    schedule: JSON {"mon": ["09:00", "18:00"], ...}; dia sem janela = fechado.
    message: resposta enviada automaticamente fora do horario.
    """

    __tablename__ = "business_hours"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    timezone = Column(String, nullable=False, default="America/Sao_Paulo")
    enabled = Column(Integer, nullable=False, default=0)
    schedule = Column(Text, nullable=False, default="{}")
    message = Column(Text, default="Estamos fora do horário de atendimento. Retornaremos em breve!")

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    company = relationship("Company")