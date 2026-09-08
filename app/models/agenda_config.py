from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class AgendaConfig(Base):
    """Config de agenda de compromissos por empresa (Secretaria IA).

    enabled: 1 = agenda ativa; 0 = indisponivel (tools da IA nao confirmam).
    schedule: JSON {"mon": ["09:00", "18:00"], ...} = janelas disponiveis para
        novos agendamentos; dia sem janela nao aceita horario.
    slot_duration: duracao padrao dos compromissos (minutos).
    min_advance: antecedencia minima (minutos) para novos agendamentos.
    blocked: JSON lista de bloqueios
        [{"date": "2026-09-10", "start": "09:00", "end": "11:00"}].
    confirmation_message: mensagem enviada ao cliente apos a confirmacao.
    """

    __tablename__ = "agenda_config"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        unique=True,
        index=True,
    )

    enabled = Column(Integer, nullable=False, default=0)
    timezone = Column(String, nullable=False, default="America/Sao_Paulo")
    schedule = Column(Text, nullable=False, default="{}")
    slot_duration = Column(Integer, nullable=False, default=30)
    min_advance = Column(Integer, nullable=False, default=60)
    blocked = Column(Text, nullable=False, default="[]")
    confirmation_message = Column(
        Text,
        default="Sua visita foi agendada. Em caso de imprevisto, avise-nos!",
    )

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    company = relationship("Company")