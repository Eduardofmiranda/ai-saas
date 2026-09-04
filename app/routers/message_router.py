from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.user import User
from app.schemas.message_schema import (
    MessageCreate,
    MessageResponse,
    MessageUpdate,
)
from app.services.deps import get_current_user

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
