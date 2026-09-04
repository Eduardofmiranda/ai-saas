from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.message_schema import (
    MessageCreate,
    MessageReply,
    MessageResponse,
    MessageUpdate,
)
from app.services import evolution
from app.services.config_service import get_or_create_config
from app.services.deps import get_current_user
from app.routers.config_router import _evo_config

router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


@router.post("/", response_model=MessageResponse)
def create_message(
    message: MessageCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == message.conversation_id,
            Conversation.company_id == current_user.company_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_message = Message(
        conversation_id=message.conversation_id,
        sender_type=message.sender_type,
        content=message.content,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


@router.get("/conversation/{conversation_id}", response_model=list[MessageResponse])
def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.company_id == current_user.company_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .all()
    )


@router.get("/{message_id}", response_model=MessageResponse)
def get_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = (
        db.query(Message)
        .join(Conversation)
        .filter(
            Message.id == message_id,
            Conversation.company_id == current_user.company_id,
        )
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    return message


@router.patch("/{message_id}", response_model=MessageResponse)
def update_message(
    message_id: int,
    data: MessageUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = (
        db.query(Message)
        .join(Conversation)
        .filter(
            Message.id == message_id,
            Conversation.company_id == current_user.company_id,
        )
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    message.content = data.content
    db.commit()
    db.refresh(message)
    return message


@router.delete("/{message_id}")
def delete_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    message = (
        db.query(Message)
        .join(Conversation)
        .filter(
            Message.id == message_id,
            Conversation.company_id == current_user.company_id,
        )
        .first()
    )
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")

    db.delete(message)
    db.commit()
    return {"message": "Message deleted successfully"}


@router.post("/conversation/{conversation_id}/reply", response_model=MessageResponse)
async def reply_in_conversation(
    conversation_id: int,
    data: MessageReply,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Resposta MANUAL do atendente humano dentro de uma conversa.

    Envia a mensagem pelo WhatsApp (Evolution) e registra na thread como
    sender_type="agent" (para o LLM tratar como mensagem do assistente e nao
    confundir com uma nova mensagem de cliente).
    """
    conversation = (
        db.query(Conversation)
        .filter(
            Conversation.id == conversation_id,
            Conversation.company_id == current_user.company_id,
        )
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    customer = conversation.customer
    if not customer:
        raise HTTPException(status_code=400, detail="Cliente da conversa não encontrado")

    config = get_or_create_config(db, current_user.company_id)
    base_url, api_key, instance = _evo_config(config)
    if not base_url or not api_key or not instance:
        raise HTTPException(
            status_code=400,
            detail="WhatsApp não configurado para esta empresa (falta URL/chave/instância).",
        )

    try:
        await evolution.send_text(
            to_phone=customer.phone,
            text=content,
            base_url=base_url,
            api_key=api_key,
            instance=instance,
        )
    except evolution.EvolutionError as exc:
        raise HTTPException(status_code=502, detail=f"Falha ao enviar no WhatsApp: {exc}")

    message = Message(
        conversation_id=conversation.id,
        sender_type="agent",
        content=content,
    )
    db.add(message)
    if conversation.status != "open":
        conversation.status = "open"
    conversation.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(message)
    return message
