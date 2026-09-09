from collections import Counter
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.company import Company
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.conversation_transfer import ConversationTransfer
from app.models.message import Message
from app.models.execution import Execution
from app.models.workflow import Workflow
from app.models.user import User
from app.services.ai_limits import CompanyAIUsage
from app.services.deps import get_current_user
from app.schemas.dashboard_schema import DashboardResponse, WorkflowMetricsResponse


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)

# Custo estimado por 1k tokens (USD). Estimativa conservadora de mistura
# entre modelos/provedores; ajustar aqui conforme o provedor em uso.
AI_ESTIMATED_COST_PER_1K_TOKENS = 0.00075


def _day_key(value) -> str:
    return value.isoformat() if hasattr(value, "isoformat") else str(value)


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

    companies = db.query(Company).filter(Company.id == company_id).count()

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

    # Series dos ultimos 7 e 30 dias (UTC) para os graficos do painel.
    today = datetime.now(timezone.utc).date()
    start = datetime.combine(today - timedelta(days=6), datetime.min.time(), tzinfo=timezone.utc)
    last_7_days = [(start + timedelta(days=i)).date().isoformat() for i in range(7)]
    start_30 = datetime.combine(today - timedelta(days=29), datetime.min.time(), tzinfo=timezone.utc)
    last_30_days = [(start_30 + timedelta(days=i)).date().isoformat() for i in range(30)]

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

    conversations_by_day = {
        _day_key(day): count
        for day, count in (
            db.query(func.date(Conversation.created_at).label("day"), func.count(Conversation.id))
            .filter(Conversation.company_id == company_id, Conversation.created_at >= start_30)
            .group_by(func.date(Conversation.created_at))
            .all()
        )
    }
    conversations_last_30_days = [
        {"date": d, "count": conversations_by_day.get(d, 0)} for d in last_30_days
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

    # Tempo medio de resposta: intervalo entre a mensagem do cliente e a
    # proxima resposta (bot ou humano) na mesma conversa.
    message_rows = (
        db.query(Message.conversation_id, Message.sender_type, Message.created_at)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(Conversation.company_id == company_id)
        .order_by(Message.conversation_id, Message.created_at)
        .all()
    )
    deltas_seconds: list[float] = []
    waiting = None  # (conversation_id, created_at)
    for conv_id, sender_type, created_at in message_rows:
        if sender_type == "customer":
            waiting = (conv_id, created_at)
        elif sender_type in ("bot", "agent") and waiting is not None:
            conv_id_part, sent_at = waiting
            if conv_id_part == conv_id:
                delta = (created_at - sent_at).total_seconds()
                if delta >= 0:
                    deltas_seconds.append(delta)
            waiting = None
    avg_response_time_minutes = round(
        (sum(deltas_seconds) / len(deltas_seconds)) / 60, 1
    ) if deltas_seconds else 0.0

    # Resolucao automatica vs humana: entre fechadas, quem teve mensagem de
    # agente ou transferencia por usuário foi resolvida com humano.
    closed_ids = [
        row.id
        for row in db.query(Conversation.id)
        .filter(Conversation.company_id == company_id, Conversation.status == "closed")
        .all()
    ]
    agent_conversation_ids = {
        cid
        for (cid,) in (
            db.query(Message.conversation_id)
            .join(Conversation, Message.conversation_id == Conversation.id)
            .filter(Conversation.company_id == company_id, Message.sender_type == "agent")
            .distinct()
            .all()
        )
    }
    user_transfer_conversation_ids = {
        cid
        for (cid,) in (
            db.query(ConversationTransfer.conversation_id)
            .filter(
                ConversationTransfer.company_id == company_id,
                ConversationTransfer.actor_type == "user",
            )
            .distinct()
            .all()
        )
    }
    human_resolved = sum(
        1
        for cid in closed_ids
        if cid in agent_conversation_ids or cid in user_transfer_conversation_ids
    )
    auto_resolved = len(closed_ids) - human_resolved

    # Uso de IA (mensagens e tokens) acumulado e serie dos ultimos 30 dias.
    ai_messages_total = 0
    ai_tokens_total = 0
    ai_usage_by_day: dict[str, dict[str, int]] = {}
    for usage_date, message_count, token_count in (
        db.query(CompanyAIUsage.usage_date, CompanyAIUsage.message_count, CompanyAIUsage.token_count)
        .filter(CompanyAIUsage.company_id == company_id)
        .all()
    ):
        ai_messages_total += message_count
        ai_tokens_total += token_count
        key = _day_key(usage_date)
        bucket = ai_usage_by_day.setdefault(key, {"messages": 0, "tokens": 0})
        bucket["messages"] += message_count
        bucket["tokens"] += token_count
    ai_usage_last_30_days = [
        {
            "date": d,
            "messages": ai_usage_by_day.get(d, {}).get("messages", 0),
            "tokens": ai_usage_by_day.get(d, {}).get("tokens", 0),
        }
        for d in last_30_days
    ]
    ai_estimated_cost = round(
        ai_tokens_total * AI_ESTIMATED_COST_PER_1K_TOKENS / 1000, 2
    )

    # Top workflows por numero de execucoes (com contagem de erros e taxa de sucesso).
    execution_counts = dict(
        db.query(Execution.workflow_id, func.count(Execution.id))
        .filter(Execution.company_id == company_id)
        .group_by(Execution.workflow_id)
        .all()
    )
    error_counts = dict(
        db.query(Execution.workflow_id, func.count(Execution.id))
        .filter(Execution.company_id == company_id, Execution.status == "error")
        .group_by(Execution.workflow_id)
        .all()
    )
    success_counts = dict(
        db.query(Execution.workflow_id, func.count(Execution.id))
        .filter(Execution.company_id == company_id, Execution.status == "success")
        .group_by(Execution.workflow_id)
        .all()
    )
    workflow_rows = db.query(Workflow.id, Workflow.name).filter(Workflow.company_id == company_id).all()
    top_rows = sorted(
        (
            (wf_id, name, execution_counts.get(wf_id, 0), error_counts.get(wf_id, 0), success_counts.get(wf_id, 0))
            for wf_id, name in workflow_rows
        ),
        key=lambda row: row[2],
        reverse=True,
    )[:5]
    top_workflows = [
        {
            "workflow_id": wf_id,
            "name": name,
            "executions": executions,
            "errors": errors,
            "success_rate": round(success / executions * 100, 1) if executions else 0.0,
        }
        for wf_id, name, executions, errors, success in top_rows
        if executions > 0
    ]

    # Erros e falhas por node (node_id fica prefixado em execution.error).
    node_error_counter: Counter = Counter()
    for (error_text,) in (
        db.query(Execution.error)
        .filter(Execution.company_id == company_id, Execution.status == "error")
        .all()
    ):
        if not error_text:
            continue
        node_id = str(error_text).split(":", 1)[0].strip() or "unknown"
        node_error_counter[node_id] += 1
    errors_by_node = [
        {"node_id": node_id, "count": count}
        for node_id, count in node_error_counter.most_common(10)
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
        "conversations_last_30_days": conversations_last_30_days,
        "avg_response_time_minutes": avg_response_time_minutes,
        "auto_resolved": auto_resolved,
        "human_resolved": human_resolved,
        "ai_messages_total": ai_messages_total,
        "ai_tokens_total": ai_tokens_total,
        "ai_estimated_cost": ai_estimated_cost,
        "ai_usage_last_30_days": ai_usage_last_30_days,
        "top_workflows": top_workflows,
        "errors_by_node": errors_by_node,
    }


@router.get(
    "/workflows/{workflow_id}/metrics",
    response_model=WorkflowMetricsResponse,
)
def get_workflow_metrics(
    workflow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Metricas detalhadas de um workflow especifico da empresa do usuario."""
    company_id = current_user.company_id

    workflow = (
        db.query(Workflow)
        .filter(Workflow.id == workflow_id, Workflow.company_id == company_id)
        .first()
    )
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow nao encontrado")

    execs = (
        db.query(Execution)
        .filter(Execution.workflow_id == workflow_id, Execution.company_id == company_id)
        .all()
    )

    total = len(execs)
    success = sum(1 for e in execs if e.status == "success")
    error = sum(1 for e in execs if e.status == "error")
    waiting = sum(1 for e in execs if e.status == "waiting")
    success_rate = round(success / total * 100, 1) if total else 0.0

    durations: list[float] = []
    for e in execs:
        if e.started_at and e.finished_at and e.status in ("success", "error"):
            d = (e.finished_at - e.started_at).total_seconds()
            if d >= 0:
                durations.append(d)
    avg_duration = round(sum(durations) / len(durations), 1) if durations else 0.0

    today = datetime.now(timezone.utc).date()
    start_30 = datetime.combine(today - timedelta(days=29), datetime.min.time(), tzinfo=timezone.utc)
    last_30_days = [(start_30 + timedelta(days=i)).date().isoformat() for i in range(30)]

    exec_by_day: dict[str, dict[str, int]] = {}
    for e in execs:
        if e.created_at and e.created_at >= start_30:
            day = e.created_at.date().isoformat()
            bucket = exec_by_day.setdefault(day, {"success": 0, "error": 0})
            if e.status in bucket:
                bucket[e.status] += 1

    node_counter: Counter = Counter()
    node_error_counter: Counter = Counter()
    for e in execs:
        nodes_in_exec = set()
        if e.context and isinstance(e.context, dict):
            for log_entry in e.context.get("logs", []):
                if isinstance(log_entry, str) and ":" in log_entry:
                    nid = log_entry.split(":", 1)[0].strip()
                    if nid:
                        nodes_in_exec.add(nid)
        for nid in nodes_in_exec:
            node_counter[nid] += 1
        if e.status == "error" and e.error:
            nid = str(e.error).split(":", 1)[0].strip()
            if nid:
                node_error_counter[nid] += 1

    all_node_ids = set(node_counter.keys()) | set(node_error_counter.keys())
    node_usage = [
        {
            "node_id": nid,
            "executions": node_counter.get(nid, 0),
            "errors": node_error_counter.get(nid, 0),
        }
        for nid in sorted(all_node_ids, key=lambda x: node_counter.get(x, 0), reverse=True)
    ]

    return {
        "workflow_id": workflow.id,
        "workflow_name": workflow.name,
        "trigger_type": workflow.trigger_type,
        "executions_total": total,
        "executions_success": success,
        "executions_error": error,
        "executions_waiting": waiting,
        "success_rate": success_rate,
        "avg_duration_seconds": avg_duration,
        "executions_last_30_days": [
            {
                "date": d,
                "success": exec_by_day.get(d, {}).get("success", 0),
                "error": exec_by_day.get(d, {}).get("error", 0),
            }
            for d in last_30_days
        ],
        "node_usage": node_usage,
    }