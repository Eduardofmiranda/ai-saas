from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.company import Company
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.execution import Execution
from app.models.workflow import Workflow
from app.models.user import User
from app.services.deps import get_current_user
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Metricas da empresa do usuario logado (isolamento multi-tenant)."""
    company_id = current_user.company_id

    companies = db.query(Company).count()

    customers = db.query(Customer).filter(Customer.company_id == company_id).count()

    conversations = (
        db.query(Conversation).filter(Conversation.company_id == company_id).count()
    )

    open_conversations = (
        db.query(Conversation)
        .filter(
            Conversation.company_id == company_id,
            Conversation.status == "open",
        )
        .count()
    )

    closed_conversations = (
        db.query(Conversation)
        .filter(
            Conversation.company_id == company_id,
            Conversation.status == "closed",
        )
        .count()
    )

    messages = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.company_id == company_id)
        .count()
    )

    workflows_total = db.query(Workflow).filter(Workflow.company_id == company_id).count()
    workflows_active = (
        db.query(Workflow)
        .filter(Workflow.company_id == company_id, Workflow.active.is_(True))
        .count()
    )

    executions_total = (
        db.query(Execution).filter(Execution.company_id == company_id).count()
    )
    executions_success = (
        db.query(Execution)
        .filter(Execution.company_id == company_id, Execution.status == "success")
        .count()
    )
    executions_error = (
        db.query(Execution)
        .filter(Execution.company_id == company_id, Execution.status == "error")
        .count()
    )

    return {
        "companies": companies,
        "customers": customers,
        "conversations": conversations,
        "open_conversations": open_conversations,
        "closed_conversations": closed_conversations,
        "messages": messages,
        "workflows_total": workflows_total,
        "workflows_active": workflows_active,
        "executions_total": executions_total,
        "executions_success": executions_success,
        "executions_error": executions_error,
    }
