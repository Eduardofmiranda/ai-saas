from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Appointment(Base):
    """Compromisso agendado na Agenda da Secretaria IA.

    status: scheduled | confirmed | completed | canceled
    origin: manual | whatsapp | workflow
    date/start_time/end_time ficam em strings no fuso configurado da empresa
    (nao expor timezone UTC ao usuario final).
    """

    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )
    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=True,
        index=True,
    )
    customer_name = Column(String, nullable=True)
    phone = Column(String, nullable=False)

    status = Column(String, nullable=False, default="scheduled", index=True)
    date = Column(String, nullable=False, index=True)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    service = Column(String, nullable=True)
    notes = Column(Text, nullable=True)

    origin = Column(String, nullable=False, default="manual")
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    company = relationship("Company")
    customer = relationship("Customer")