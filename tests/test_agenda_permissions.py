"""Permissoes granulares dos operadores da agenda (papel + propriedade).

Modelo aprovado:
- Ler (config/availability/lista/detalhe) e criar: qualquer papel autenticado.
- Alterar/cancelar: gestor (owner/admin) OU o proprio criador do compromisso.
- Compromissos de WhatsApp (sem criador): apenas gestao.
- Config da agenda: gestor (ja era).
"""
import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.main import app
from app.models.company import Company
from app.models.user import User
from app.services import agenda as ag
from app.services.deps import get_current_user


@pytest.fixture
def db_session():
    """Banco SQLite em arquivo temporario (visto por todas as conexoes do TestClient)."""
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


def _make(db_session, current_user):
    def _get_db():
        yield db_session

    def _get_current_user():
        return current_user

    app.dependency_overrides[get_current_user] = _get_current_user
    from app.database.session import get_db

    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def company(db_session):
    c = Company(name="Empresa Agenda")
    db_session.add(c)
    db_session.commit()
    db_session.refresh(c)
    return c


def _user(db_session, company_id, email, role):
    u = User(company_id=company_id, name=email.split("@")[0], email=email, role=role)
    u.set_password("senha123")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def owner(db_session, company):
    return _user(db_session, company.id, "owner@test.com", "owner")


@pytest.fixture
def admin(db_session, company):
    return _user(db_session, company.id, "admin@test.com", "admin")


@pytest.fixture
def agent(db_session, company):
    return _user(db_session, company.id, "agent@test.com", "agent")


@pytest.fixture
def agent2(db_session, company):
    return _user(db_session, company.id, "agent2@test.com", "agent")


def _appt(db, company_id, *, created_by=None, origin="manual", phone="5511999999999", date="2099-09-21", start="10:00"):
    return ag.add_appointment(
        db,
        company_id,
        date=date,
        start_time=start,
        end_time="10:30",
        phone=phone,
        origin=origin,
        user_id=created_by.id if created_by else None,
        status="scheduled",
        skip_min_advance=True,
    )


class TestAgentMutatesOwnAppointment:
    def test_agent_updates_own(self, db_session, company, agent):
        appt = _appt(db_session, company.id, created_by=agent)
        for c in _make(db_session, agent):
            res = c.patch(f"/agenda/appointments/{appt.id}", json={"notes": "Cliente pediu nota"})
            assert res.status_code == 200
            assert res.json()["notes"] == "Cliente pediu nota"

    def test_agent_cancels_own(self, db_session, company, agent):
        appt = _appt(db_session, company.id, created_by=agent)
        for c in _make(db_session, agent):
            res = c.delete(f"/agenda/appointments/{appt.id}")
            assert res.status_code == 200
            assert res.json()["status"] == "canceled"


class TestAgentCannotMutateOthers:
    def test_agent_cannot_update_other_agent_appointment(self, db_session, company, agent, agent2):
        appt = _appt(db_session, company.id, created_by=agent2)
        for c in _make(db_session, agent):
            res = c.patch(f"/agenda/appointments/{appt.id}", json={"notes": "indevido"})
            assert res.status_code == 403

    def test_agent_cannot_cancel_other_agent_appointment(self, db_session, company, agent, agent2):
        appt = _appt(db_session, company.id, created_by=agent2)
        for c in _make(db_session, agent):
            res = c.delete(f"/agenda/appointments/{appt.id}")
            assert res.status_code == 403
        db_session.refresh(appt)
        assert appt.status == "scheduled"

    def test_agent_cannot_mutate_whatsapp_origin(self, db_session, company, agent):
        appt = _appt(db_session, company.id, origin="whatsapp")
        for c in _make(db_session, agent):
            assert c.patch(f"/agenda/appointments/{appt.id}", json={"notes": "x"}).status_code == 403
            assert c.delete(f"/agenda/appointments/{appt.id}").status_code == 403
        db_session.refresh(appt)
        assert appt.status == "scheduled"


class TestManagersMutateAnything:
    def test_admin_updates_agent_appointment(self, db_session, company, admin, agent):
        appt = _appt(db_session, company.id, created_by=agent)
        for c in _make(db_session, admin):
            res = c.patch(f"/agenda/appointments/{appt.id}", json={"notes": "ajuste da gestao"})
            assert res.status_code == 200
            assert res.json()["notes"] == "ajuste da gestao"

    def test_owner_cancels_whatsapp_origin(self, db_session, company, owner):
        appt = _appt(db_session, company.id, origin="whatsapp")
        for c in _make(db_session, owner):
            res = c.delete(f"/agenda/appointments/{appt.id}")
            assert res.status_code == 200
            assert res.json()["status"] == "canceled"

    def test_admin_cancels_agent_appointment(self, db_session, company, admin, agent):
        appt = _appt(db_session, company.id, created_by=agent)
        for c in _make(db_session, admin):
            res = c.delete(f"/agenda/appointments/{appt.id}")
            assert res.status_code == 200
            assert res.json()["status"] == "canceled"


class TestReadAndCreateOpenToAll:
    def test_agent_reads_list_and_detail(self, db_session, company, agent, agent2):
        appt = _appt(db_session, company.id, created_by=agent2)
        for c in _make(db_session, agent):
            assert c.get("/agenda/appointments").status_code == 200
            assert c.get(f"/agenda/appointments/{appt.id}").status_code == 200

    def test_agent_creates_appointment(self, db_session, company, agent):
        for c in _make(db_session, agent):
            res = c.post("/agenda/appointments", json={
                "date": "2099-09-21", "start_time": "11:00", "end_time": "11:30",
                "phone": "5511977777777",
            })
            assert res.status_code == 200
            body = res.json()
            assert body["created_by_user_id"] == agent.id

    def test_agent_reads_config_and_availability(self, db_session, company, agent):
        for c in _make(db_session, agent):
            assert c.get("/agenda/config").status_code == 200
            assert c.get("/agenda/availability", params={"date": "2099-09-21"}).status_code == 200


class TestConfigStaysManagerOnly:
    def test_agent_cannot_update_config(self, db_session, company, agent):
        for c in _make(db_session, agent):
            res = c.put("/agenda/config", json={"enabled": True})
            assert res.status_code == 403

    def test_admin_updates_config(self, db_session, company, admin):
        for c in _make(db_session, admin):
            res = c.put("/agenda/config", json={"enabled": True})
            assert res.status_code == 200


class TestTenantBoundary:
    def test_agent_cannot_mutate_other_company_appointment(self, db_session, company, agent):
        other = Company(name="Outra Empresa")
        db_session.add(other)
        db_session.commit()
        db_session.refresh(other)
        foreign = _appt(db_session, other.id)

        for c in _make(db_session, agent):
            assert c.patch(f"/agenda/appointments/{foreign.id}", json={"notes": "x"}).status_code == 404
            assert c.delete(f"/agenda/appointments/{foreign.id}").status_code == 404
