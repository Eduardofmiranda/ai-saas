from fastapi import HTTPException
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.database.session import get_db
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.user import User
from app.schemas.customer_schema import (
    CustomerCreate,
    CustomerResponse,
)
from app.services.deps import get_current_user

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
