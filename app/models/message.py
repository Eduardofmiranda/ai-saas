from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
    Text,
)

from sqlalchemy.orm import relationship

from datetime import datetime, timezone

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False,
    )

    sender_type = Column(
        String,
        nullable=False,
    )

    content = Column(
        Text,
        nullable=False,
    )

    # id da mensagem no WhatsApp (para deduplicacao no webhook)
    wa_message_id = Column(String, default="", index=True)

    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
    )

    conversation = relationship("Conversation", back_populates="messages")
