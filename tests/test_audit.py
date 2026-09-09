"""Testes do servico de audit log.

Cobertura:
- log_action registra corretamente
- get_audit_logs com filtros
- isolamento por company_id
- request IP/user-agent
"""
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.main import app
from app.database.session import get_db
from app.models.company import Company
from app.models.user import User
from app.models.audit_log import AuditLog
from app.services.audit import log_action, get_audit_logs
from app.services.deps import get_current_user, get_current_platform_admin


@pytest.fixture
def db():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = create_engine(f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    session._engine = engine
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def company(db):
    c = Company(name="Test Audit")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _user(db, company_id, email, role="agent"):
    u = User(company_id=company_id, name=email.split("@")[0], email=email, role=role)
    u.set_password("senha123")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


class TestLogAction:
    def test_creates_audit_record(self, db, company):
        user = _user(db, company.id, "admin@test.com", "admin")
        log_action(db, company.id, user.id, "user.create", entity="user", entity_id=10)
        logs = db.query(AuditLog).all()
        assert len(logs) == 1
        assert logs[0].action == "user.create"
        assert logs[0].entity == "user"
        assert logs[0].entity_id == 10
        assert logs[0].user_id == user.id
        assert logs[0].company_id == company.id

    def test_details_as_json(self, db, company):
        log_action(db, company.id, None, "config.update", details={"fields": ["ai_on", "ai_model"]})
        log = db.query(AuditLog).first()
        assert '"ai_on"' in log.details
        assert '"ai_model"' in log.details

    def test_ip_and_user_agent(self, db, company):
        class FakeRequest:
            headers = {"user-agent": "TestBot/1.0", "x-forwarded-for": "1.2.3.4"}
            client = type("C", (), {"host": "127.0.0.1"})()
        log_action(db, company.id, None, "auth.login", request=FakeRequest())
        log = db.query(AuditLog).first()
        assert log.ip_address == "1.2.3.4"
        assert log.user_agent == "TestBot/1.0"


class TestGetAuditLogs:
    def test_empty(self, db, company):
        result = get_audit_logs(db, company.id)
        assert result["total"] == 0
        assert result["items"] == []

    def test_lists_records(self, db, company):
        user = _user(db, company.id, "admin@test.com", "admin")
        log_action(db, company.id, user.id, "user.create", entity="user")
        log_action(db, company.id, user.id, "config.update", entity="config")
        result = get_audit_logs(db, company.id)
        assert result["total"] == 2

    def test_filter_by_action(self, db, company):
        log_action(db, company.id, None, "auth.login")
        log_action(db, company.id, None, "user.create")
        result = get_audit_logs(db, company.id, action="auth.login")
        assert result["total"] == 1
        assert result["items"][0]["action"] == "auth.login"

    def test_filter_by_entity(self, db, company):
        log_action(db, company.id, None, "user.create", entity="user")
        log_action(db, company.id, None, "workflow.create", entity="workflow")
        result = get_audit_logs(db, company.id, entity="user")
        assert result["total"] == 1

    def test_filter_by_user(self, db, company):
        u1 = _user(db, company.id, "a@test.com", "admin")
        u2 = _user(db, company.id, "b@test.com", "agent")
        log_action(db, company.id, u1.id, "user.create")
        log_action(db, company.id, u2.id, "config.update")
        result = get_audit_logs(db, company.id, user_id=u1.id)
        assert result["total"] == 1

    def test_pagination(self, db, company):
        for i in range(5):
            log_action(db, company.id, None, f"action.{i}")
        result = get_audit_logs(db, company.id, limit=2, offset=0)
        assert result["total"] == 5
        assert len(result["items"]) == 2
        result2 = get_audit_logs(db, company.id, limit=2, offset=4)
        assert len(result2["items"]) == 1

    def test_company_isolation(self, db, company):
        c2 = Company(name="Other")
        db.add(c2)
        db.commit()
        db.refresh(c2)
        log_action(db, company.id, None, "user.create")
        log_action(db, c2.id, None, "workflow.create")
        assert get_audit_logs(db, company.id)["total"] == 1
        assert get_audit_logs(db, c2.id)["total"] == 1


class TestAuditEndpoint:
    def _make(self, db, user):
        def _get_db():
            yield db
        def _get_current_user():
            return user
        def _get_platform_admin():
            return user
        app.dependency_overrides[get_db] = _get_db
        app.dependency_overrides[get_current_user] = _get_current_user
        app.dependency_overrides[get_current_platform_admin] = _get_platform_admin
        client = TestClient(app)
        yield client
        app.dependency_overrides.clear()

    def test_endpoint_requires_manager(self, db, company):
        agent = _user(db, company.id, "agent@test.com", "agent")
        for c in self._make(db, agent):
            res = c.get("/audit-logs/")
            assert res.status_code == 403

    def test_endpoint_returns_logs(self, db, company):
        admin = _user(db, company.id, "admin@test.com", "admin")
        log_action(db, company.id, admin.id, "user.create", entity="user")
        for c in self._make(db, admin):
            res = c.get("/audit-logs/")
            assert res.status_code == 200
            body = res.json()
            assert body["total"] == 1
            assert body["items"][0]["action"] == "user.create"

    def test_endpoint_with_filters(self, db, company):
        admin = _user(db, company.id, "admin@test.com", "admin")
        log_action(db, company.id, admin.id, "user.create", entity="user")
        log_action(db, company.id, admin.id, "config.update", entity="config")
        for c in self._make(db, admin):
            res = c.get("/audit-logs/", params={"entity": "user"})
            assert res.status_code == 200
            assert res.json()["total"] == 1
