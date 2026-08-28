from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.models.company import Company
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.message import Message

from app.schemas.dashboard_schema import DashboardResponse


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get(
    "/",
    response_model=DashboardResponse
)
def get_dashboard(
    db: Session = Depends(get_db)
):

    companies = db.query(Company).count()

    customers = db.query(Customer).count()

    conversations = db.query(Conversation).count()

    open_conversations = (
        db.query(Conversation)
        .filter(
            Conversation.status == "open"
        )
        .count()
    )

    closed_conversations = (
        db.query(Conversation)
        .filter(
            Conversation.status == "closed"
        )
        .count()
    )

    messages = db.query(Message).count()

    return {
        "companies": companies,
        "customers": customers,
        "conversations": conversations,
        "open_conversations": open_conversations,
        "closed_conversations": closed_conversations,
        "messages": messages
    }