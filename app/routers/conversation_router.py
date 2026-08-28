from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.conversation import Conversation
from app.schemas.conversation_schema import (
    ConversationCreate,
    ConversationResponse,
    ConversationUpdate,
)

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


@router.post("/", response_model=ConversationResponse)
def create_conversation(
    conversation: ConversationCreate,
    db: Session = Depends(get_db),
):
    new_conversation = Conversation(
        company_id=conversation.company_id,
        customer_id=conversation.customer_id,
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)
    return new_conversation


@router.get("/", response_model=list[ConversationResponse])
def get_conversations(db: Session = Depends(get_db)):
    return db.query(Conversation).all()


@router.get("/company/{company_id}", response_model=list[ConversationResponse])
def get_company_conversations(
    company_id: int,
    db: Session = Depends(get_db),
):
    return (
        db.query(Conversation)
        .filter(Conversation.company_id == company_id)
        .all()
    )


@router.get("/filter/", response_model=list[ConversationResponse])
def filter_conversations(
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Conversation)
    if status:
        query = query.filter(Conversation.status == status)
    return query.all()


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    conversation.status = data.status
    db.commit()
    db.refresh(conversation)
    return conversation


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db),
):
    conversation = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id)
        .first()
    )
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    db.delete(conversation)
    db.commit()
    return {"message": "Conversation deleted successfully"}
