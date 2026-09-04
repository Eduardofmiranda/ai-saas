from sqlalchemy import (
    Column,
    Integer,
    String,
    ForeignKey,
    DateTime,
)

from sqlalchemy.orm import relationship

from typing import TYPE_CHECKING
from datetime import datetime, timezone

from app.database.database import Base

if TYPE_CHECKING:
    from app.models.message import Message


def _utcnow():
    return datetime.now(timezone.utc)


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)

    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
    )

    customer_id = Column(
        Integer,
        ForeignKey("customers.id"),
        nullable=False,
    )

    status = Column(
        String,
        default="open",
    )

    created_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=_utcnow,
        onupdate=_utcnow,
    )

    company = relationship("Company")

    customer = relationship("Customer")

    messages = relationship("Message", back_populates="conversation", order_by="Message.id")

    transfers = relationship(
        "ConversationTransfer",
        back_populates="conversation",
        order_by="ConversationTransfer.id",
    )
