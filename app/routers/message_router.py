import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks

from sqlalchemy.orm import Session

from app.database.session import get_db, SessionLocal
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
from app.services import access_rules
from app.routers.config_router import _evo_config

router = APIRouter(
    prefix="/messages",
    tags=["Messages"],
)


def _send_whatsapp_background(company_id: int, phone: str, content: str) -> None:
    """Envia mensagem pelo WhatsApp em background (fire-and-forget)."""
    db: Session = SessionLocal()
    try:
        config = get_or_create_config(db, company_id)
        base_url, api_key, instance = _evo_config(config)
        if base_url and api_key and instance:
            asyncio.run(evolution.send_text(
                to_phone=phone,
                text=content,
                base_url=base_url,
                api_key=api_key,
                instance=instance,
            ))
    except Exception:
        pass
    finally:
        db.close()


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

    if not access_rules.can_attend(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao pode enviar mensagens neste setor")

    new_message = Message(
        conversation_id=message.conversation_id,
        sender_type=message.sender_type,
        content=message.content,
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


@router.get("/conversation/{conversation_id}")
def get_messages(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    offset: int = 0,
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

    if not access_rules.can_view(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao tem acesso a esta conversa")

    q = db.query(Message).filter(Message.conversation_id == conversation_id)
    total = q.count()
    messages = q.order_by(Message.created_at.asc()).offset(offset).limit(limit).all()
    return {"total": total, "items": messages}


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

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == message.conversation_id)
        .first()
    )
    if not access_rules.can_attend(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao pode editar mensagens deste setor")

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

    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == message.conversation_id)
        .first()
    )
    if not access_rules.can_attend(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao pode excluir mensagens deste setor")

    db.delete(message)
    db.commit()
    return {"message": "Message deleted successfully"}


@router.post("/conversation/{conversation_id}/reply", response_model=MessageResponse)
def reply_in_conversation(
    conversation_id: int,
    data: MessageReply,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """Resposta MANUAL do atendente humano — retorna IMEDIATAMENTE.

    Salva a mensagem no banco e envia pelo WhatsApp em background.
    O frontend recebe a resposta instantaneamente (optimistic UI).
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

    if not access_rules.can_attend(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao pode responder conversas deste setor")

    content = data.content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="Mensagem vazia")

    customer = conversation.customer
    if not customer:
        raise HTTPException(status_code=400, detail="Cliente da conversa nao encontrado")

    # Salva no banco IMEDIATAMENTE
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

    # Envia WhatsApp em background (nao bloqueia o usuario)
    if background_tasks:
        background_tasks.add_task(
            _send_whatsapp_background,
            current_user.company_id,
            customer.phone,
            content,
        )

    return message
