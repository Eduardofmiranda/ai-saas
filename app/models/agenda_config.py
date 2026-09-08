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
    confirmation_required: 1 = IA cria agendamento provisorio
        (awaiting_confirmation) e envia pedido de confirmacao ao cliente antes
        de confirmar (fluxo em 2 passos); 0 = cria direto como scheduled.
    confirmation_expiry_hours: horas apos as quais um agendamento provisorio
        sem confirmacao do cliente e automaticamente cancelado (0 = nunca).
    confirmation_request_message: texto do pedido de confirmacao enviado ao
        cliente. Suporta {nome}, {servico}, {data} e {horario}.
    reminders_enabled: 1 = envia lembretes automaticos; 0 = desativado.
    reminder_hours: JSON lista de horas de antecedencia para enviar lembretes
        (ex.: [24, 1]).
    reminder_message: texto do lembrete. Suporta {nome}, {servico}, {data} e
        {horario}.
    whatsapp_number: numero do WhatsApp vinculado a instancia da Secretaria IA
        (usado como referencia nos fluxos de confirmacao/lembrete).
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
    confirmation_required = Column(Integer, nullable=False, default=1)
    confirmation_expiry_hours = Column(Integer, nullable=False, default=24)
    confirmation_request_message = Column(
        Text,
        default=(
            "Olá {nome}! Para confirmar seu agendamento de {servico} no dia "
            "{data} às {horario}, responda CONFIRMAR. Para desistir, responda CANCELAR."
        ),
    )
    reminders_enabled = Column(Integer, nullable=False, default=0)
    reminder_hours = Column(Text, nullable=False, default="[24]")
    reminder_message = Column(
        Text,
        default="Lembrete: você tem {servico} marcado para {data} às {horario}.",
    )
    whatsapp_number = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    company = relationship("Company")