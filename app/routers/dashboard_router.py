from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends

from sqlalchemy import func
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

    pending_conversations = (
        db.query(Conversation)
        .filter(
            Conversation.company_id == company_id,
            Conversation.status == "pending_agent",
        )
        .count()
    )

    agent_conversations = (
        db.query(Conversation)
        .filter(
            Conversation.company_id == company_id,
            Conversation.status == "agent",
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

    # Series dos ultimos 7 dias (UTC) para os graficos do painel.
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=6), datetime.min.time(), tzinfo=timezone.utc)
    last_7_days = [(start + timedelta(days=i)).date().isoformat() for i in range(7)]

    def _day_key(value) -> str:
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    messages_by_day = {
        _day_key(day): count
        for day, count in (
            db.query(func.date(Message.created_at).label("day"), func.count(Message.id))
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(
                Conversation.company_id == company_id,
                Message.created_at >= start,
            )
            .group_by(func.date(Message.created_at))
            .all()
        )
    }
    messages_last_7_days = [
        {"date": d, "count": messages_by_day.get(d, 0)} for d in last_7_days
    ]

    executions_by_day: dict[str, dict[str, int]] = {}
    execution_rows = (
        db.query(func.date(Execution.created_at).label("day"), Execution.status, func.count(Execution.id).label("count"))
        .filter(
            Execution.company_id == company_id,
            Execution.created_at >= start,
        )
        .group_by(func.date(Execution.created_at), Execution.status)
        .all()
    )
    for row in execution_rows:
        day = _day_key(row.day)
        bucket = executions_by_day.setdefault(day, {"success": 0, "error": 0})
        if row.status in bucket:
            bucket[row.status] += row.count
    executions_last_7_days = [
        {
            "date": d,
            "success": executions_by_day.get(d, {}).get("success", 0),
            "error": executions_by_day.get(d, {}).get("error", 0),
        }
        for d in last_7_days
    ]

    return {
        "companies": companies,
        "customers": customers,
        "conversations": conversations,
        "open_conversations": open_conversations,
        "pending_conversations": pending_conversations,
        "agent_conversations": agent_conversations,
        "closed_conversations": closed_conversations,
        "messages": messages,
        "workflows_total": workflows_total,
        "workflows_active": workflows_active,
        "executions_total": executions_total,
        "executions_success": executions_success,
        "executions_error": executions_error,
        "messages_last_7_days": messages_last_7_days,
        "executions_last_7_days": executions_last_7_days,
    }
