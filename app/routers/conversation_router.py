from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, selectinload

from app.database.session import get_db
from app.models.conversation import Conversation
from app.models.conversation_transfer import ConversationTransfer
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


def _to_response(conversation: Conversation) -> dict:
    """Serializa uma conversa com dados do cliente e da ultima mensagem (inbox)."""
    messages = conversation.messages or []
    last = messages[-1] if messages else None
    return {
        "id": conversation.id,
        "company_id": conversation.company_id,
        "customer_id": conversation.customer_id,
        "status": conversation.status,
        "created_at": conversation.created_at,
        "updated_at": conversation.updated_at,
        "customer": conversation.customer,
        "last_message": last.content if last else None,
        "last_message_at": last.created_at if last else None,
        "message_count": len(messages),
        "transfers": conversation.transfers or [],
    }


def _transfer_action(old: str, new: str) -> str | None:
    """Mapeia uma transicao de status para o registro de transferencia."""
    transitions = {
        ("pending_agent", "open"): "assumed",
        ("pending_agent", "closed"): "closed",
        ("open", "closed"): "closed",
        ("closed", "open"): "reopened",
    }
    return transitions.get((old, new))


def _get_conversation(db: Session, conversation_id: int, company_id: int) -> Conversation:
    conversation = (
        db.query(Conversation)
        .options(
            selectinload(Conversation.customer),
            selectinload(Conversation.messages),
            selectinload(Conversation.transfers),
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
    new_conversation = Conversation(
        company_id=current_user.company_id,
        customer_id=conversation.customer_id,
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation


@router.get("/", response_model=list[ConversationResponse])
def get_conversations(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversations = (
        db.query(Conversation)
        .options(
            selectinload(Conversation.customer),
            selectinload(Conversation.messages),
            selectinload(Conversation.transfers),
        )
        .filter(Conversation.company_id == current_user.company_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [_to_response(conversation) for conversation in conversations]


@router.get("/filter/", response_model=list[ConversationResponse])
def filter_conversations(
    status: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Conversation).options(
        selectinload(Conversation.customer),
        selectinload(Conversation.messages),
        selectinload(Conversation.transfers),
    )
    query = query.filter(Conversation.company_id == current_user.company_id)
    if status:
        query = query.filter(Conversation.status == status)
    conversations = query.order_by(Conversation.updated_at.desc()).all()
    return [_to_response(conversation) for conversation in conversations]


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, current_user.company_id)
    return _to_response(conversation)


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
    return _to_response(conversation)


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
