from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, desc

from app.database.session import get_db, SessionLocal
from app.models.conversation import Conversation
from app.models.conversation_transfer import ConversationTransfer
from app.models.customer import Customer
from app.models.message import Message
from app.models.user import User
from app.schemas.conversation_schema import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
)
from app.services.deps import get_current_user

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


def _to_response(conversation: Conversation, last_message: Message | None = None) -> dict:
    """Serializa uma conversa com dados do cliente e da ultima mensagem (inbox)."""
    customer = None
    if conversation.customer:
        customer = {
            "id": conversation.customer.id,
            "company_id": conversation.customer.company_id,
            "name": conversation.customer.name,
            "phone": conversation.customer.phone,
        }

    transfers = []
    for t in (conversation.transfers or []):
        transfers.append({
            "id": t.id,
            "conversation_id": t.conversation_id,
            "company_id": t.company_id,
            "actor_type": t.actor_type,
            "user_id": t.user_id,
            "user_name": t.user_name,
            "action": t.action,
            "created_at": t.created_at,
        })

    return {
        "id": conversation.id,
        "company_id": conversation.company_id,
        "customer_id": conversation.customer_id,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "customer": customer,
        "last_message": last_message.content if last_message else None,
        "last_message_at": last_message.created_at if last_message else None,
        "message_count": conversation._msg_count if hasattr(conversation, "_msg_count") else 0,
        "transfers": transfers,
    }


def _transfer_action(old: str, new: str) -> str | None:
    """Mapeia uma transicao de status para o registro de transferencia."""
    transitions = {
        ("pending_agent", "open"): "assumed",
        ("pending_agent", "agent"): "assumed",
        ("pending_agent", "closed"): "closed",
        ("open", "closed"): "closed",
        ("open", "agent"): "assumed",
        ("agent", "open"): "released",
        ("agent", "closed"): "closed",
        ("closed", "open"): "reopened",
    }
    return transitions.get((old, new))


def _get_conversation(db: Session, conversation_id: int, company_id: int) -> Conversation:
    conversation = (
        db.query(Conversation)
        .options(
            selectinload(Conversation.customer),
        )
        .filter(
            Conversation.id == conversation_id,
            Conversation.company_id == company_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.post("/", response_model=ConversationResponse)
def create_conversation(
    conversation: ConversationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == conversation.customer_id,
            Customer.company_id == current_user.company_id,
        )
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    new_conversation = Conversation(
        company_id=current_user.company_id,
        customer_id=customer.id,
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation


@router.get("/")
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    # Subquery: ultima mensagem de cada conversa
    last_msg_sq = (
        db.query(
            Message.conversation_id,
            func.max(Message.id).label("last_msg_id"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    # Subquery: contagem de mensagens
    msg_count_sq = (
        db.query(
            Message.conversation_id,
            func.count(Message.id).label("msg_count"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    q = (
        db.query(Conversation, Message)
        .outerjoin(last_msg_sq, Conversation.id == last_msg_sq.c.conversation_id)
        .outerjoin(Message, last_msg_sq.c.last_msg_id == Message.id)
        .outerjoin(msg_count_sq, Conversation.id == msg_count_sq.c.conversation_id)
        .options(
            selectinload(Conversation.customer),
            selectinload(Conversation.transfers),
        )
        .filter(Conversation.company_id == current_user.company_id)
    )

    total = db.query(Conversation).filter(Conversation.company_id == current_user.company_id).count()
    rows = q.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

    items = []
    for conv, last_msg in rows:
        # Pega contagem do subquery
        count_row = (
            db.query(msg_count_sq.c.msg_count)
            .filter(msg_count_sq.c.conversation_id == conv.id)
            .first()
        )
        conv._msg_count = count_row[0] if count_row else 0
        items.append(_to_response(conv, last_msg))

    return {"total": total, "items": items}


@router.get("/filter/")
def filter_conversations(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    last_msg_sq = (
        db.query(
            Message.conversation_id,
            func.max(Message.id).label("last_msg_id"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    msg_count_sq = (
        db.query(
            Message.conversation_id,
            func.count(Message.id).label("msg_count"),
        )
        .group_by(Message.conversation_id)
        .subquery()
    )

    q = (
        db.query(Conversation, Message)
        .outerjoin(last_msg_sq, Conversation.id == last_msg_sq.c.conversation_id)
        .outerjoin(Message, last_msg_sq.c.last_msg_id == Message.id)
        .outerjoin(msg_count_sq, Conversation.id == msg_count_sq.c.conversation_id)
        .options(
            selectinload(Conversation.customer),
            selectinload(Conversation.transfers),
        )
        .filter(Conversation.company_id == current_user.company_id)
    )
    if status:
        q = q.filter(Conversation.status == status)

    total = q.count()
    rows = q.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

    items = []
    for conv, last_msg in rows:
        count_row = (
            db.query(msg_count_sq.c.msg_count)
            .filter(msg_count_sq.c.conversation_id == conv.id)
            .first()
        )
        conv._msg_count = count_row[0] if count_row else 0
        items.append(_to_response(conv, last_msg))

    return {"total": total, "items": items}


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, current_user.company_id)

    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .first()
    )
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    conversation._msg_count = msg_count

    return _to_response(conversation, last_msg)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, current_user.company_id)

    old_status = conversation.status
    if data.status != old_status:
        action = _transfer_action(old_status, data.status)
        if action:
            db.add(
                ConversationTransfer(
                    conversation_id=conversation.id,
                    company_id=conversation.company_id,
                    actor_type="user",
                    user_id=current_user.id,
                    user_name=current_user.name or current_user.email or "Atendente",
                    action=action,
                )
            )
    conversation.status = data.status
    db.commit()
    db.refresh(conversation)

    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .first()
    )
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    conversation._msg_count = msg_count

    return _to_response(conversation, last_msg)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, current_user.company_id)

    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted successfully"}


@router.post("/{conversation_id}/assume", response_model=ConversationResponse)
def assume_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Assume atendimento manual: desliga IA e marca como 'agent'."""
    conversation = _get_conversation(db, conversation_id, current_user.company_id)

    if conversation.status == "agent":
        raise HTTPException(status_code=400, detail="Conversa ja esta em atendimento humano")

    old_status = conversation.status
    conversation.status = "agent"

    db.add(
        ConversationTransfer(
            conversation_id=conversation.id,
            company_id=conversation.company_id,
            actor_type="user",
            user_id=current_user.id,
            user_name=current_user.name or current_user.email or "Atendente",
            action="assumed",
        )
    )
    db.commit()
    db.refresh(conversation)

    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .first()
    )
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    conversation._msg_count = msg_count

    return _to_response(conversation, last_msg)
