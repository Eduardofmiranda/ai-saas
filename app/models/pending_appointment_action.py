from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class PendingAppointmentAction(Base):
    """Acao pendente de consentimento do cliente (Secretaria IA).

    Quando `agenda_config.confirmation_required` esta ativo, remarcar ou
    cancelar via tools da IA nao e aplicado de imediato: fica registrado aqui
    e so e efetivado depois que o cliente responde CONFIRMAR (ou descartado ao
    responder CANCELAR/expirar). O compromisso original permanece inalterado
    ate a confirmacao.

    action: reschedule | cancel
    payload: JSON — campos da remarcacao (`fields`) ou `{"reason": ...}`.
    notified: 1 depois que o pedido foi enviado via WhatsApp (deduplicacao).
    """

    __tablename__ = "pending_appointment_actions"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )
    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False,
        index=True,
    )
    phone = Column(String, nullable=False, index=True)

    action = Column(String, nullable=False)
    payload = Column(Text, nullable=True)
    notified = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=_utcnow)
