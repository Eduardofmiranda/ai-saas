import io
import json
import asyncio
from datetime import datetime, timezone

from fastapi import HTTPException, BackgroundTasks
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db, SessionLocal
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.user import User
from app.models.company_config import CompanyConfig
from app.schemas.customer_schema import (
    CustomerCreate,
    CustomerResponse,
)
from app.services.config_service import get_or_create_config
from app.services.deps import get_current_user
from app.routers.config_router import _evo_config
from app.services import evolution

router = APIRouter(
    prefix="/customers",
    tags=["Customers"],
)


@router.post("/", response_model=CustomerResponse)
def create_customer(
    customer: CustomerCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_customer = Customer(
        company_id=current_user.company_id,
        name=customer.name,
        phone=customer.phone,
    )
    db.add(new_customer)
    db.commit()
    db.refresh(new_customer)
    return new_customer


@router.get("/")
def get_customers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 50,
    offset: int = 0,
):
    q = db.query(Customer).filter(Customer.company_id == current_user.company_id)
    total = q.count()
    customers = q.order_by(Customer.id.desc()).offset(offset).limit(limit).all()

    customer_ids = [c.id for c in customers]
    conv_counts = (
        db.query(Conversation.customer_id, func.count(Conversation.id))
        .filter(Conversation.customer_id.in_(customer_ids))
        .group_by(Conversation.customer_id)
        .all()
    )
    count_map = dict(conv_counts)

    items = []
    for c in customers:
        items.append({
            "id": c.id,
            "company_id": c.company_id,
            "name": c.name,
            "phone": c.phone,
            "conversation_count": count_map.get(c.id, 0),
        })

    return {"total": total, "items": items}


@router.get("/export")
def export_customers(
    format: str = "json",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Exporta todos os leads da empresa como JSON ou Excel."""
    customers = (
        db.query(Customer)
        .filter(Customer.company_id == current_user.company_id)
        .order_by(Customer.id)
        .all()
    )

    customer_ids = [c.id for c in customers]
    conv_counts = (
        db.query(Conversation.customer_id, func.count(Conversation.id))
        .filter(Conversation.customer_id.in_(customer_ids))
        .group_by(Conversation.customer_id)
        .all()
    )
    count_map = dict(conv_counts)

    data = []
    for c in customers:
        data.append({
            "id": c.id,
            "name": c.name,
            "phone": c.phone,
            "conversation_count": count_map.get(c.id, 0),
            "created_at": c.created_at.isoformat() if c.created_at else None,
        })

    if format == "xlsx":
        try:
            from openpyxl import Workbook
        except ImportError:
            raise HTTPException(status_code=500, detail="Export Excel nao disponivel (openpyxl nao instalado)")

        wb = Workbook()
        ws = wb.active
        ws.title = "Leads"
        ws.append(["ID", "Nome", "Telefone", "Conversas", "Criado em"])
        for row in data:
            ws.append([row["id"], row["name"], row["phone"], row["conversation_count"], row["created_at"]])

        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        filename = f"leads_{current_user.company_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.xlsx"
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    # JSON por padrao
    filename = f"leads_{current_user.company_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    return StreamingResponse(
        io.BytesIO(json.dumps(data, ensure_ascii=False, indent=2).encode()),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _send_bulk_background(company_id: int, phones: list[str], text: str) -> None:
    """Envia mensagem em massa pelo WhatsApp em background."""
    db: Session = SessionLocal()
    try:
        config = get_or_create_config(db, company_id)
        base_url, api_key, instance = _evo_config(config)
        if not base_url or not api_key or not instance:
            return

        for phone in phones:
            try:
                asyncio.run(evolution.send_text(
                    to_phone=phone,
                    text=text,
                    base_url=base_url,
                    api_key=api_key,
                    instance=instance,
                ))
            except Exception:
                pass
    finally:
        db.close()


@router.post("/bulk-message")
def bulk_message(
    data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    background_tasks: BackgroundTasks = None,
):
    """Envia mensagem em massa para leads.

    body: {"text": "...", "customer_ids": [1,2,3]} ou {"text": "...", "all": true}
    """
    text = (data.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Mensagem obrigatoria")

    customer_ids = data.get("customer_ids")
    send_all = data.get("all", False)

    if send_all:
        customers = (
            db.query(Customer)
            .filter(Customer.company_id == current_user.company_id)
            .all()
        )
    elif customer_ids:
        customers = (
            db.query(Customer)
            .filter(
                Customer.id.in_(customer_ids),
                Customer.company_id == current_user.company_id,
            )
            .all()
        )
    else:
        raise HTTPException(status_code=400, detail="Selecione os leads ou marque 'enviar para todos'")

    if not customers:
        raise HTTPException(status_code=400, detail="Nenhum lead encontrado")

    phones = [c.phone for c in customers]

    if background_tasks:
        background_tasks.add_task(_send_bulk_background, current_user.company_id, phones, text)

    return {"message": f"Mensagem enviada para {len(phones)} leads", "count": len(phones)}


@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.company_id == current_user.company_id,
        )
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@router.delete("/{customer_id}")
def delete_customer(
    customer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    customer = (
        db.query(Customer)
        .filter(
            Customer.id == customer_id,
            Customer.company_id == current_user.company_id,
        )
        .first()
    )
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    conv_ids = [c.id for c in db.query(Conversation.id).filter(Conversation.customer_id == customer.id).all()]
    if conv_ids:
        db.query(Message).filter(Message.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
        db.query(Conversation).filter(Conversation.id.in_(conv_ids)).delete(synchronize_session=False)

    db.delete(customer)
    db.commit()
    return {"message": "Lead removido com sucesso"}
