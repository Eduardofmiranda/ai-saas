"""Testes da Fase 8.9 — membros x setores com nivel de acesso.

Cobertura:
- create/update user com setores (validacao de empresa e nivel)
- list users inclui departments
- visibilidade de conversas por setor
- can_view / can_attend (reply/alterar/assumir) e 403 para view-only
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
from app.models.department import Department
from app.models.user import User
from app.models.user_department import UserDepartment
from app.models.customer import Customer
from app.models.conversation import Conversation
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
    c = Company(name="Sectors Co")
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


@pytest.fixture
def client_for(db):
    def _make(user):
        def _get_db():
            yield db

        def _get_current_user():
            return user

        def _get_platform_admin():
            return user

        app.dependency_overrides[get_db] = _get_db
        app.dependency_overrides[get_current_user] = _get_current_user
        app.dependency_overrides[get_current_platform_admin] = _get_platform_admin
        return TestClient(app)
    yield _make
    app.dependency_overrides.clear()


def _user(db, company_id, email, role="agent"):
    u = User(company_id=company_id, name=email.split("@")[0], email=email, role=role)
    u.set_password("senha123")
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _department(db, company, name):
    d = Department(company_id=company.id, name=name)
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _assign(db, user, department, level="attend"):
    db.add(UserDepartment(user_id=user.id, department_id=department.id, level=level))
    db.commit()


def _customer(db, company, name, phone):
    c = Customer(company_id=company.id, name=name, phone=phone)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _conversation(db, company, customer, department=None):
    conv = Conversation(company_id=company.id, customer_id=customer.id)
    if department is not None:
        conv.department_id = department.id
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


class TestCreateUpdateUserDepartments:
    def test_create_user_with_departments(self, db, company, client_for):
        admin = _user(db, company.id, "admin@x.com", "admin")
        d1 = _department(db, company, "Vendas")
        d2 = _department(db, company, "Suporte")
        client = client_for(admin)
        res = client.post("/users/", json={
            "name": "Maria",
            "email": "maria@x.com",
            "password": "x123456",
            "role": "agent",
            "departments": [
                {"department_id": d1.id, "level": "attend"},
                {"department_id": d2.id, "level": "view"},
            ],
        })
        assert res.status_code == 200
        body = res.json()
        assert len(body["departments"]) == 2
        levels = {d["department_id"]: d["level"] for d in body["departments"]}
        assert levels[d1.id] == "attend"
        assert levels[d2.id] == "view"

    def test_create_user_rejects_foreign_department(self, db, company, client_for):
        admin = _user(db, company.id, "admin@x.com", "admin")
        other = Company(name="Other")
        db.add(other)
        db.commit()
        db.refresh(other)
        foreign = _department(db, other, "Externo")
        client = client_for(admin)
        res = client.post("/users/", json={
            "name": "Joao",
            "email": "joao@x.com",
            "password": "x123456",
            "departments": [{"department_id": foreign.id, "level": "attend"}],
        })
        assert res.status_code == 400

    def test_create_user_rejects_invalid_level(self, db, company, client_for):
        admin = _user(db, company.id, "admin@x.com", "admin")
        d1 = _department(db, company, "Vendas")
        client = client_for(admin)
        res = client.post("/users/", json={
            "name": "Joao",
            "email": "joao@x.com",
            "password": "x123456",
            "departments": [{"department_id": d1.id, "level": "boss"}],
        })
        assert res.status_code == 422

    def test_update_replaces_departments(self, db, company, client_for):
        admin = _user(db, company.id, "admin@x.com", "admin")
        d1 = _department(db, company, "Vendas")
        d2 = _department(db, company, "Suporte")
        agent = _user(db, company.id, "ag@x.com", "agent")
        _assign(db, agent, d1, "attend")
        client = client_for(admin)
        res = client.patch(f"/users/{agent.id}", json={
            "departments": [{"department_id": d2.id, "level": "manage"}],
        })
        assert res.status_code == 200
        body = res.json()
        assert [d["department_id"] for d in body["departments"]] == [d2.id]
        assert body["departments"][0]["level"] == "manage"

    def test_update_without_departments_keeps_them(self, db, company, client_for):
        admin = _user(db, company.id, "admin@x.com", "admin")
        d1 = _department(db, company, "Vendas")
        agent = _user(db, company.id, "ag@x.com", "agent")
        _assign(db, agent, d1, "attend")
        client = client_for(admin)
        res = client.patch(f"/users/{agent.id}", json={"role": "admin"})
        assert res.status_code == 200
        assert [d["department_id"] for d in res.json()["departments"]] == [d1.id]

    def test_update_clears_departments(self, db, company, client_for):
        admin = _user(db, company.id, "admin@x.com", "admin")
        d1 = _department(db, company, "Vendas")
        agent = _user(db, company.id, "ag@x.com", "agent")
        _assign(db, agent, d1, "attend")
        client = client_for(admin)
        res = client.patch(f"/users/{agent.id}", json={"departments": []})
        assert res.status_code == 200
        assert res.json()["departments"] == []

    def test_list_users_includes_departments(self, db, company, client_for):
        admin = _user(db, company.id, "admin@x.com", "admin")
        d1 = _department(db, company, "Vendas")
        agent = _user(db, company.id, "ag@x.com", "agent")
        _assign(db, agent, d1, "attend")
        client = client_for(admin)
        res = client.get("/users/")
        assert res.status_code == 200
        items = {i["email"]: i for i in res.json()["items"]}
        assert items["ag@x.com"]["departments"][0]["department_id"] == d1.id
        assert items["admin@x.com"]["departments"] == []


class TestConversationVisibility:
    def _setup(self, db, company):
        d1 = _department(db, company, "Vendas")
        d2 = _department(db, company, "Suporte")
        admin = _user(db, company.id, "admin@x.com", "admin")
        agent_sector = _user(db, company.id, "vendas@x.com", "agent")
        _assign(db, agent_sector, d1, "attend")
        agent_view = _user(db, company.id, "view@x.com", "agent")
        _assign(db, agent_view, d1, "view")
        agent_no_sector = _user(db, company.id, "geral@x.com", "agent")
        cust = _customer(db, company, "Cliente", "5511999999999")
        conv_a = _conversation(db, company, cust, d1)
        conv_b = _conversation(db, company, cust, d2)
        conv_none = _conversation(db, company, cust, None)
        return {
            "d1": d1, "d2": d2, "admin": admin, "agent_sector": agent_sector,
            "agent_view": agent_view, "agent_no_sector": agent_no_sector,
            "conv_a": conv_a, "conv_b": conv_b, "conv_none": conv_none,
        }

    def _ids(self, res):
        return {i["id"] for i in res.json()["items"]}

    def test_agent_with_sector_sees_only_sector_and_none(self, db, company, client_for):
        s = self._setup(db, company)
        client = client_for(s["agent_sector"])
        res = client.get("/conversations/")
        assert res.status_code == 200
        assert self._ids(res) == {s["conv_a"].id, s["conv_none"].id}

    def test_agent_without_sector_sees_all(self, db, company, client_for):
        s = self._setup(db, company)
        client = client_for(s["agent_no_sector"])
        res = client.get("/conversations/")
        assert self._ids(res) == {s["conv_a"].id, s["conv_b"].id, s["conv_none"].id}

    def test_manager_sees_all(self, db, company, client_for):
        s = self._setup(db, company)
        client = client_for(s["admin"])
        res = client.get("/conversations/")
        assert self._ids(res) == {s["conv_a"].id, s["conv_b"].id, s["conv_none"].id}

    def test_agent_cannot_view_other_sector_detail(self, db, company, client_for):
        s = self._setup(db, company)
        client = client_for(s["agent_sector"])
        assert client.get(f"/conversations/{s['conv_b'].id}").status_code == 403
        assert client.get(f"/messages/conversation/{s['conv_b'].id}").status_code == 403

    def test_view_level_can_read_but_not_act(self, db, company, client_for):
        s = self._setup(db, company)
        client = client_for(s["agent_view"])
        assert client.get(f"/conversations/{s['conv_a'].id}").status_code == 200
        assert client.get(f"/messages/conversation/{s['conv_a'].id}").status_code == 200
        assert client.patch(f"/conversations/{s['conv_a'].id}", json={"status": "closed"}).status_code == 403
        assert client.post(f"/messages/conversation/{s['conv_a'].id}/reply", json={"content": "oi"}).status_code == 403
        assert client.post(f"/conversations/{s['conv_a'].id}/assume").status_code == 403

    def test_attend_level_can_reply(self, db, company, client_for):
        s = self._setup(db, company)
        client = client_for(s["agent_sector"])
        res = client.post(f"/messages/conversation/{s['conv_a'].id}/reply", json={"content": "vou atender"})
        assert res.status_code == 200

    def test_agent_without_sector_can_reply_any(self, db, company, client_for):
        s = self._setup(db, company)
        client = client_for(s["agent_no_sector"])
        res = client.post(f"/messages/conversation/{s['conv_b'].id}/reply", json={"content": "oii"})
        assert res.status_code == 200

    def test_conversation_response_has_department(self, db, company, client_for):
        s = self._setup(db, company)
        client = client_for(s["admin"])
        res = client.get(f"/conversations/{s['conv_a'].id}")
        assert res.json()["department_name"] == s["d1"].name
        res2 = client.get(f"/conversations/{s['conv_none'].id}")
        assert res2.json()["department_name"] is None