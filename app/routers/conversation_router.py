from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import func, desc, or_
from app.models.pending_flow import PendingFlow

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
from app.services import access_rules

router = APIRouter(
    prefix="/conversations",
    tags=["Conversations"],
)


def _to_response(conversation: Conversation, last_message: Message | None = None, has_pending_flow: bool = False) -> dict:
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
        "department_id": conversation.department_id,
        "department_name": conversation.department.name if conversation.department else None,
        "customer": customer,
        "last_message": last_message.content if last_message else None,
        "last_message_at": last_message.created_at if last_message else None,
        "message_count": conversation._msg_count if hasattr(conversation, "_msg_count") else 0,
        "transfers": transfers,
        "has_pending_flow": has_pending_flow,
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
            selectinload(Conversation.department),
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
    status: Optional[str] = None,
    q: Optional[str] = None,
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

    qry = (
        db.query(Conversation, Message)
        .outerjoin(last_msg_sq, Conversation.id == last_msg_sq.c.conversation_id)
        .outerjoin(Message, last_msg_sq.c.last_msg_id == Message.id)
        .outerjoin(msg_count_sq, Conversation.id == msg_count_sq.c.conversation_id)
        .options(
            selectinload(Conversation.customer),
            selectinload(Conversation.transfers),
            selectinload(Conversation.department),
        )
        .filter(Conversation.company_id == current_user.company_id)
    )
    vis = access_rules.visible_condition(Conversation, db, current_user)
    if vis is not None:
        qry = qry.filter(vis)
    if status:
        qry = qry.filter(Conversation.status == status)
    if q and q.strip():
        ql = f"%{q.strip()}%"
        qry = qry.outerjoin(Customer, Conversation.customer_id == Customer.id).filter(
            or_(Customer.name.ilike(ql), Customer.phone.ilike(ql))
        )

    total = qry.count()
    rows = qry.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

    # Pega phones com pending_flow ativo
    pending_phones = set(
        row[0] for row in (
            db.query(PendingFlow.phone)
            .filter(PendingFlow.company_id == current_user.company_id)
            .all()
        )
    )

    items = []
    for conv, last_msg in rows:
        count_row = (
            db.query(msg_count_sq.c.msg_count)
            .filter(msg_count_sq.c.conversation_id == conv.id)
            .first()
        )
        conv._msg_count = count_row[0] if count_row else 0
        has_pending = conv.customer.phone in pending_phones if conv.customer else False
        items.append(_to_response(conv, last_msg, has_pending_flow=has_pending))

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
            selectinload(Conversation.department),
        )
        .filter(Conversation.company_id == current_user.company_id)
    )
    vis = access_rules.visible_condition(Conversation, db, current_user)
    if vis is not None:
        q = q.filter(vis)
    if status:
        q = q.filter(Conversation.status == status)

    total = q.count()
    rows = q.order_by(desc(Conversation.updated_at)).offset(offset).limit(limit).all()

    pending_phones = set(
        row[0] for row in (
            db.query(PendingFlow.phone)
            .filter(PendingFlow.company_id == current_user.company_id)
            .all()
        )
    )

    items = []
    for conv, last_msg in rows:
        count_row = (
            db.query(msg_count_sq.c.msg_count)
            .filter(msg_count_sq.c.conversation_id == conv.id)
            .first()
        )
        conv._msg_count = count_row[0] if count_row else 0
        has_pending = conv.customer.phone in pending_phones if conv.customer else False
        items.append(_to_response(conv, last_msg, has_pending_flow=has_pending))

    return {"total": total, "items": items}


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, current_user.company_id)

    if not access_rules.can_view(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao tem acesso a esta conversa")

    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .first()
    )
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    conversation._msg_count = msg_count

    has_pending = False
    if conversation.customer:
        has_pending = db.query(PendingFlow).filter(
            PendingFlow.company_id == current_user.company_id,
            PendingFlow.phone == conversation.customer.phone,
        ).first() is not None

    return _to_response(conversation, last_msg, has_pending_flow=has_pending)


@router.patch("/{conversation_id}", response_model=ConversationResponse)
def update_conversation(
    conversation_id: int,
    data: ConversationUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    conversation = _get_conversation(db, conversation_id, current_user.company_id)

    if not access_rules.can_attend(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao pode alterar conversas deste setor")

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

    if not access_rules.can_attend(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao pode assumir conversas deste setor")

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


@router.post("/{conversation_id}/pause-workflow", response_model=ConversationResponse)
def pause_conversation_workflow(
    conversation_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Pausa qualquer fluxo ativo para esta conversa (cancela PendingFlow)."""
    conversation = _get_conversation(db, conversation_id, current_user.company_id)

    if not access_rules.can_attend(db, current_user, conversation):
        raise HTTPException(status_code=403, detail="Voce nao pode pausar fluxos desta conversa")

    if not conversation.customer:
        raise HTTPException(status_code=400, detail="Conversa sem cliente associado")

    deleted = (
        db.query(PendingFlow)
        .filter(
            PendingFlow.company_id == current_user.company_id,
            PendingFlow.phone == conversation.customer.phone,
        )
        .delete(synchronize_session=False)
    )
    db.commit()

    if deleted == 0:
        raise HTTPException(status_code=400, detail="Nenhum fluxo ativo para esta conversa")

    db.refresh(conversation)

    last_msg = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.id.desc())
        .first()
    )
    msg_count = db.query(Message).filter(Message.conversation_id == conversation_id).count()
    conversation._msg_count = msg_count

    return _to_response(conversation, last_msg, has_pending_flow=False)
