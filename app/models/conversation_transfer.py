from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database.database import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ConversationTransfer(Base):
    """Registro de transferencia/handoff de uma conversa (quem assumiu, quando).

    Actions:
        transfer_requested - o node `transfer_to_agent` marcou a conversa como pendente
        assumed           - um atendente assumiu a conversa (pending_agent -> open)
        closed            - a conversa foi fechada
        reopened          - a conversa foi reaberta
    """

    __tablename__ = "conversation_transfers"

    id = Column(Integer, primary_key=True, index=True)

    conversation_id = Column(
        Integer,
        ForeignKey("conversations.id"),
        nullable=False,
        index=True,
    )
    company_id = Column(
        Integer,
        ForeignKey("companies.id"),
        nullable=False,
        index=True,
    )

    # quem agiu: workflow (node) ou user (atendente)
    actor_type = Column(String, default="workflow")
    user_id = Column(Integer, nullable=True)
    user_name = Column(String, default="")

    action = Column(String, nullable=False)

    created_at = Column(DateTime(timezone=True), default=_utcnow)

    conversation = relationship("Conversation", back_populates="transfers")