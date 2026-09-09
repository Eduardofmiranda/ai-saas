from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class OutboundWebhook(Base):
    __tablename__ = "outbound_webhooks"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    url = Column(String, nullable=False)
    secret = Column(String, nullable=False, default="")
    events = Column(String, nullable=False, default="workflow.completed,workflow.error")
    active = Column(Boolean, nullable=False, default=True)
    description = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)
    updated_at = Column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    company = relationship("Company")


class OutboundWebhookLog(Base):
    __tablename__ = "outbound_webhook_logs"

    id = Column(Integer, primary_key=True, index=True)
    webhook_id = Column(Integer, ForeignKey("outbound_webhooks.id", ondelete="CASCADE"), nullable=False, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    event = Column(String, nullable=False)
    url = Column(String, nullable=False)
    status_code = Column(Integer, default=0)
    success = Column(Boolean, default=False)
    request_body = Column(Text, default="")
    response_body = Column(Text, default="")
    error = Column(Text, default="")
    created_at = Column(DateTime(timezone=True), default=_utcnow)

    webhook = relationship("OutboundWebhook")
