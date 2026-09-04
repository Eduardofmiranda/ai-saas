import hashlib
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.main import app
from app.models.password_reset_token import PasswordResetToken
from app.models.user import User
from app.services import email_service
from app.services.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    verify_password,
)


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
    u = User(company_id=1, name="Dono", email="dono@test.com", role="owner")
    u.set_password("senha123")
    db_session.add(u)
    db_session.commit()
    db_session.refresh(u)
    return u


def _make(db_session, current_user):
    def _get_db():
        yield db_session

    from app.database.session import get_db
    from app.services.deps import get_current_user

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


def _hash(token):
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


class TestChangePassword:
    def test_change_password_success(self, db_session, owner, monkeypatch):
        for c in _make(db_session, owner):
            res = c.post(
                "/auth/change-password",
                json={"current_password": "senha123", "new_password": "novaSenha!9"},
            )
            assert res.status_code == 200

        db_session.refresh(owner)
        assert verify_password("novaSenha!9", owner.password_hash)

    def test_change_password_wrong_current_returns_400(self, db_session, owner):
        for c in _make(db_session, owner):
            res = c.post(
                "/auth/change-password",
                json={"current_password": "errada", "new_password": "novaSenha!9"},
            )
            assert res.status_code == 400
            assert "Senha atual" in res.json()["detail"]

    def test_change_password_short_returns_400(self, db_session, owner):
        for c in _make(db_session, owner):
            res = c.post(
                "/auth/change-password",
                json={"current_password": "senha123", "new_password": "abc"},
            )
            assert res.status_code == 400

    def test_change_password_requires_auth(self, db_session, owner):
        # Nao sobrescreve get_current_user: sem header Authorization -> 401.
        def _get_db():
            yield db_session

        from app.database.session import get_db

        app.dependency_overrides[get_db] = _get_db
        try:
            client = TestClient(app)
            res = client.post(
                "/auth/change-password",
                json={"current_password": "x", "new_password": "novaSenha!9"},
            )
            assert res.status_code == 401
        finally:
            app.dependency_overrides.clear()


class TestRefresh:
    def test_refresh_rotates_tokens(self, db_session, owner):
        refresh = create_refresh_token(str(owner.id), {"company_id": owner.company_id})

        for c in _make(db_session, owner):
            res = c.post("/auth/refresh", json={"refresh_token": refresh})
            assert res.status_code == 200
            data = res.json()
            assert data["access_token"]
            assert data["refresh_token"]
            assert data["email"] == "dono@test.com"

            payload = decode_access_token(data["access_token"])
            assert payload["type"] == "access"
            assert payload["sub"] == str(owner.id)

    def test_access_token_cannot_be_used_as_refresh(self, db_session, owner):
        access = create_access_token(str(owner.id), {"company_id": owner.company_id})

        for c in _make(db_session, owner):
            res = c.post("/auth/refresh", json={"refresh_token": access})
            assert res.status_code == 401

    def test_invalid_refresh_returns_401(self, db_session, owner):
        for c in _make(db_session, owner):
            res = c.post("/auth/refresh", json={"refresh_token": "nao.eh.um.jwt"})
            assert res.status_code == 401


class TestForgotPassword:
    def test_forgot_returns_503_without_smtp(self, db_session, owner, monkeypatch):
        monkeypatch.setattr(email_service, "email_is_configured", lambda: False)

        for c in _make(db_session, owner):
            res = c.post("/auth/forgot-password", json={"email": "dono@test.com"})
            assert res.status_code == 503

        assert db_session.query(PasswordResetToken).count() == 0

    def test_forgot_sends_link_and_creates_token(self, db_session, owner, monkeypatch):
        monkeypatch.setattr(email_service, "email_is_configured", lambda: True)
        captured = {}

        def fake_send(to_email, reset_url):
            captured.update(to_email=to_email, reset_url=reset_url)

        monkeypatch.setattr(email_service, "send_reset_email", fake_send)

        for c in _make(db_session, owner):
            res = c.post("/auth/forgot-password", json={"email": "dono@test.com"})
            assert res.status_code == 200
            assert "recebera um link" in res.json()["message"]

        assert captured["to_email"] == "dono@test.com"
        assert captured["reset_url"].startswith("http://localhost:5173/reset-password?token=")
        token = captured["reset_url"].split("token=")[1]
        assert db_session.query(PasswordResetToken).filter_by(token_hash=_hash(token)).count() == 1

    def test_forgot_unknown_email_returns_generic(self, db_session, owner, monkeypatch):
        monkeypatch.setattr(email_service, "email_is_configured", lambda: True)
        captured = {}

        def fake_send(to_email, reset_url):
            captured.update(to_email=to_email, reset_url=reset_url)

        monkeypatch.setattr(email_service, "send_reset_email", fake_send)

        for c in _make(db_session, owner):
            res = c.post("/auth/forgot-password", json={"email": "naoexiste@test.com"})
            assert res.status_code == 200
            assert "recebera um link" in res.json()["message"]

        assert captured == {}
        assert db_session.query(PasswordResetToken).count() == 0


class TestResetPassword:
    def _seed_token(self, db_session, owner, *, used=False, expired=False):
        record = PasswordResetToken(
            user_id=owner.id,
            company_id=owner.company_id,
            token_hash=_hash("tok_reset"),
            expires_at=(
                datetime.now(timezone.utc) - timedelta(hours=1)
                if expired
                else datetime.now(timezone.utc) + timedelta(hours=1)
            ),
            used_at=datetime.now(timezone.utc) if used else None,
        )
        db_session.add(record)
        db_session.commit()
        return record

    def test_reset_password_success(self, db_session, owner):
        self._seed_token(db_session, owner)

        for c in _make(db_session, owner):
            res = c.post(
                "/auth/reset-password",
                json={"token": "tok_reset", "new_password": "novaSenha!9"},
            )
            assert res.status_code == 200

        db_session.refresh(owner)
        assert verify_password("novaSenha!9", owner.password_hash)
        record = db_session.query(PasswordResetToken).one()
        assert record.used_at is not None

    def test_reset_invalid_token_returns_400(self, db_session, owner):
        for c in _make(db_session, owner):
            res = c.post(
                "/auth/reset-password",
                json={"token": "tok_inexistente", "new_password": "novaSenha!9"},
            )
            assert res.status_code == 400

    def test_reset_used_token_returns_400(self, db_session, owner):
        self._seed_token(db_session, owner, used=True)

        for c in _make(db_session, owner):
            res = c.post(
                "/auth/reset-password",
                json={"token": "tok_reset", "new_password": "novaSenha!9"},
            )
            assert res.status_code == 400
            assert "ja foi utilizado" in res.json()["detail"]

    def test_reset_expired_token_returns_400(self, db_session, owner):
        self._seed_token(db_session, owner, expired=True)

        for c in _make(db_session, owner):
            res = c.post(
                "/auth/reset-password",
                json={"token": "tok_reset", "new_password": "novaSenha!9"},
            )
            assert res.status_code == 400
            assert "expirou" in res.json()["detail"]

    def test_reset_short_password_returns_400(self, db_session, owner):
        self._seed_token(db_session, owner)

        for c in _make(db_session, owner):
            res = c.post(
                "/auth/reset-password",
                json={"token": "tok_reset", "new_password": "abc"},
            )
            assert res.status_code == 400