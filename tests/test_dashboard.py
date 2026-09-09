import tempfile
from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.main import app
from app.models.conversation import Conversation
from app.models.conversation_transfer import ConversationTransfer
from app.models.customer import Customer
from app.models.execution import Execution
from app.models.message import Message
from app.models.user import User
from app.models.workflow import Workflow
from app.services.ai_limits import CompanyAIUsage
from app.services.deps import get_current_user


@pytest.fixture
def db_session():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = create_engine(f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db._engine = engine
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


@pytest.fixture
def owner(db_session):
    u = User(company_id=1, name="Dono", email="owner@test.com", role="owner")
    u.set_password("senha123")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _make(db_session, current_user):
    def _get_db():
        yield db_session

    app.dependency_overrides[get_current_user] = lambda: current_user
    from app.database.session import get_db

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _customer(db_session, *, name="Cliente", phone="5511999999999", company_id=1):
    cust = Customer(company_id=company_id, phone=phone, name=name)
    db_session.add(cust)
    db_session.flush()
    return cust


def _conversation(db_session, *, customer, status="open", company_id=1, days_ago=0):
    conv = Conversation(
        company_id=company_id,
        customer_id=customer.id,
        status=status,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db_session.add(conv)
    db_session.flush()
    return conv


def _message(db_session, *, conversation, sender_type="bot", content="oi", days_ago=0):
    msg = Message(
        conversation_id=conversation.id,
        sender_type=sender_type,
        content=content,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db_session.add(msg)
    db_session.flush()
    return msg


def _workflow(db_session, *, company_id=1, name="Fluxo"):
    wf = Workflow(company_id=company_id, user_id=1, name=name)
    db_session.add(wf)
    db_session.flush()
    return wf


def _execution(db_session, *, workflow, status="success", days_ago=0, company_id=1):
    ex = Execution(
        workflow_id=workflow.id,
        company_id=company_id,
        status=status,
        created_at=datetime.now(timezone.utc) - timedelta(days=days_ago),
    )
    db_session.add(ex)
    db_session.flush()
    return ex


class TestDashboardData:
    def test_counts_and_status(self, db_session, owner):
        c = _customer(db_session)
        _conversation(db_session, customer=c, status="open")
        _conversation(db_session, customer=c, status="pending_agent")
        _conversation(db_session, customer=c, status="agent")
        _conversation(db_session, customer=c, status="closed")
        db_session.commit()

        for client in _make(db_session, owner):
            res = client.get("/dashboard/")
            assert res.status_code == 200
            body = res.json()
            assert body["customers"] == 1
            assert body["conversations"] == 4
            assert body["open_conversations"] == 1
            assert body["pending_conversations"] == 1
            assert body["agent_conversations"] == 1
            assert body["closed_conversations"] == 1

    def test_messages_series_last_7_days(self, db_session, owner):
        c = _customer(db_session)
        conv = _conversation(db_session, customer=c)
        _message(db_session, conversation=conv, days_ago=0)
        _message(db_session, conversation=conv, days_ago=1)
        _message(db_session, conversation=conv, days_ago=2)
        _message(db_session, conversation=conv, days_ago=2)
        db_session.commit()

        for client in _make(db_session, owner):
            res = client.get("/dashboard/")
            body = res.json()
            series = body["messages_last_7_days"]
            assert len(series) == 7
            assert sum(item["count"] for item in series) == 4
            assert series[-1]["count"] == 1  # hoje
            assert series[-2]["count"] == 1  # ontem
            assert series[-3]["count"] == 2  # ha dois dias

    def test_executions_series_and_status_split(self, db_session, owner):
        wf = _workflow(db_session)
        _execution(db_session, workflow=wf, status="success", days_ago=0)
        _execution(db_session, workflow=wf, status="error", days_ago=0)
        _execution(db_session, workflow=wf, status="error", days_ago=1)
        db_session.commit()

        for client in _make(db_session, owner):
            res = client.get("/dashboard/")
            body = res.json()
            assert body["executions_total"] == 3
            assert body["executions_success"] == 1
            assert body["executions_error"] == 2
            series = body["executions_last_7_days"]
            assert len(series) == 7
            assert series[-1]["success"] == 1
            assert series[-1]["error"] == 1
            assert series[-2]["error"] == 1

    def test_multi_tenant_isolation_in_series(self, db_session, owner):
        my_c = _customer(db_session, phone="5511988888888")
        my_conv = _conversation(db_session, customer=my_c)
        _message(db_session, conversation=my_conv, days_ago=0)

        other = _customer(db_session, phone="5511777777777", company_id=99)
        other_conv = _conversation(db_session, customer=other, company_id=99)
        _message(db_session, conversation=other_conv, days_ago=0)
        other_wf = _workflow(db_session, company_id=99)
        _execution(db_session, workflow=other_wf, status="success", days_ago=0, company_id=99)
        db_session.commit()

        for client in _make(db_session, owner):
            res = client.get("/dashboard/")
            body = res.json()
            assert body["customers"] == 1
            assert sum(item["count"] for item in body["messages_last_7_days"]) == 1
            assert sum(item["success"] + item["error"] for item in body["executions_last_7_days"]) == 0

    def test_conversations_last_30_days(self, db_session, owner):
        c = _customer(db_session)
        _conversation(db_session, customer=c, days_ago=0)
        _conversation(db_session, customer=c, days_ago=0)
        _conversation(db_session, customer=c, days_ago=1)
        _conversation(db_session, customer=c, days_ago=40)

        other = _customer(db_session, phone="5511777777777", company_id=99)
        _conversation(db_session, customer=other, company_id=99, days_ago=0)
        db_session.commit()

        for client in _make(db_session, owner):
            body = client.get("/dashboard/").json()
            series = body["conversations_last_30_days"]
            assert len(series) == 30
            assert sum(item["count"] for item in series) == 3
            assert series[-1]["count"] == 2  # hoje
            assert series[-2]["count"] == 1  # ontem
            assert series[0]["count"] == 0   # ha 29 dias

    def test_response_time_and_auto_vs_human(self, db_session, owner):
        c = _customer(db_session)
        t0 = datetime.now(timezone.utc)

        conv_agent = _conversation(db_session, customer=c, status="closed")
        db_session.add(Message(
            conversation_id=conv_agent.id, sender_type="customer",
            content="oi", created_at=t0 - timedelta(minutes=3),
        ))
        db_session.add(Message(
            conversation_id=conv_agent.id, sender_type="agent",
            content="ola, como posso ajudar?", created_at=t0,
        ))

        conv_bot = _conversation(db_session, customer=c, status="closed")
        db_session.add(Message(
            conversation_id=conv_bot.id, sender_type="customer",
            content="oi", created_at=t0 - timedelta(minutes=3),
        ))
        db_session.add(Message(
            conversation_id=conv_bot.id, sender_type="bot",
            content="ola!", created_at=t0,
        ))

        conv_transfer = _conversation(db_session, customer=c, status="closed")
        db_session.add(ConversationTransfer(
            conversation_id=conv_transfer.id, company_id=1,
            actor_type="user", user_name="Atendente", action="assumed",
        ))

        _conversation(db_session, customer=c, status="open")
        db_session.commit()

        for client in _make(db_session, owner):
            body = client.get("/dashboard/").json()
            assert body["avg_response_time_minutes"] == 3.0
            assert body["auto_resolved"] == 1
            assert body["human_resolved"] == 2

    def test_ai_usage_totals_series_and_cost(self, db_session, owner):
        today = date.today()
        db_session.add(CompanyAIUsage(company_id=1, usage_date=today, message_count=5, token_count=4_000_000))
        db_session.add(CompanyAIUsage(company_id=1, usage_date=today - timedelta(days=1), message_count=2, token_count=1_000_000))
        db_session.add(CompanyAIUsage(company_id=99, usage_date=today, message_count=50, token_count=999_999_999))
        db_session.commit()

        for client in _make(db_session, owner):
            body = client.get("/dashboard/").json()
            assert body["ai_messages_total"] == 7
            assert body["ai_tokens_total"] == 5_000_000
            assert body["ai_estimated_cost"] == round(5_000_000 * 0.00075 / 1000, 2) == 3.75
            series = body["ai_usage_last_30_days"]
            assert len(series) == 30
            assert series[-1]["messages"] == 5
            assert series[-1]["tokens"] == 4_000_000
            assert series[-2]["messages"] == 2
            assert series[-2]["tokens"] == 1_000_000

    def test_top_workflows_and_errors_by_node(self, db_session, owner):
        wf_a = _workflow(db_session, name="Fluxo A")
        wf_b = _workflow(db_session, name="Fluxo B")
        other_wf = _workflow(db_session, name="Outra empresa", company_id=99)
        _execution(db_session, workflow=wf_a, status="success")
        _execution(db_session, workflow=wf_a, status="success")
        err_a = _execution(db_session, workflow=wf_a, status="error")
        _execution(db_session, workflow=wf_b, status="success")
        err_b = _execution(db_session, workflow=wf_b, status="error")
        _execution(db_session, workflow=other_wf, status="error")
        err_a.error = "rag_node: falha ao consultar knowledge"
        err_b.error = "http_node: timeout"
        db_session.commit()

        for client in _make(db_session, owner):
            body = client.get("/dashboard/").json()
            top = body["top_workflows"]
            assert [w["name"] for w in top] == ["Fluxo A", "Fluxo B"]
            assert top[0]["executions"] == 3 and top[0]["errors"] == 1
            assert top[1]["executions"] == 2 and top[1]["errors"] == 1
            errors = {item["node_id"]: item["count"] for item in body["errors_by_node"]}
            assert errors == {"rag_node": 1, "http_node": 1}