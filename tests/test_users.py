import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.main import app
from app.models.user import User
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
def owner(db_session):
    u = User(company_id=1, name="Dono", email="owner@test.com", role="owner")
    u.set_password("senha123")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


@pytest.fixture
def agent(db_session):
    u = User(company_id=1, name="Agente", email="agent@test.com", role="agent")
    u.set_password("senha123")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


class TestUsers:
    def test_list_users_sees_only_own_company(self, db_session, owner):
        other = User(company_id=99, name="Outro", email="outro@test.com", role="agent")
        other.set_password("x")
        db_session.add(other)
        db_session.commit()

        for c in _make(db_session, owner):
            res = c.get("/users/")
            assert res.status_code == 200
            emails = {u["email"] for u in res.json()}
            assert "owner@test.com" in emails
            assert "outro@test.com" not in emails

    def test_create_user(self, db_session, owner):
        for c in _make(db_session, owner):
            res = c.post("/users/", json={
                "name": "Novo", "email": "novo@test.com", "password": "senha123", "role": "admin",
            })
            assert res.status_code == 200
            assert res.json()["email"] == "novo@test.com"
            assert res.json()["role"] == "admin"

    def test_agent_cannot_create_user(self, db_session, owner, agent):
        for c in _make(db_session, agent):
            res = c.post("/users/", json={
                "name": "X", "email": "x@test.com", "password": "senha123", "role": "agent",
            })
            assert res.status_code == 403

    def test_agent_can_list_but_not_delete(self, db_session, owner, agent):
        for c in _make(db_session, agent):
            assert c.get("/users/").status_code == 200
            assert c.delete(f"/users/{owner.id}").status_code == 403

    def test_owner_can_delete_agent(self, db_session, owner, agent):
        for c in _make(db_session, owner):
            assert c.delete(f"/users/{agent.id}").status_code == 200
            assert db_session.query(User).filter(User.id == agent.id).first() is None

    def test_cannot_delete_self(self, db_session, owner):
        for c in _make(db_session, owner):
            assert c.delete(f"/users/{owner.id}").status_code == 400

    def test_auth_me_returns_role(self, db_session, owner):
        for c in _make(db_session, owner):
            res = c.get("/auth/me")
            assert res.status_code == 200
            data = res.json()
            assert data["email"] == "owner@test.com"
            assert data["role"] == "owner"
            assert data["company_id"] == 1
