import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.main import app
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.execution import Execution
from app.models.message import Message
from app.models.user import User
from app.models.workflow import Workflow
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


def _conversation(db_session, *, customer, status="open", company_id=1):
    conv = Conversation(company_id=company_id, customer_id=customer.id, status=status)
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