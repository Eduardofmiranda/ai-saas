from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class AppointmentEvent(Base):
    """Historico de criacao, alteracao e cancelamento de compromissos."""

    __tablename__ = "appointment_events"

    id = Column(Integer, primary_key=True, index=True)
    appointment_id = Column(
        Integer,
        ForeignKey("appointments.id"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    action = Column(String, nullable=False)
    actor_type = Column(String, nullable=False, default="user")
    user_id = Column(Integer, nullable=True)
    user_name = Column(String, nullable=True)
    # JSON resumido do estado relevante na acao (sem dados sensiveis).
    details = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow)