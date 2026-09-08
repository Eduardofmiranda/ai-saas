import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.main import app
from app.models.company import Company
from app.models.user import User
from app.services.security import verify_password


@pytest.fixture
def db_session():
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    engine = create_engine(f"sqlite:///{tmp.name}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


def _client(db_session, current_user):
    from app.database.session import get_db
    from app.services.deps import get_current_user

    def _get_db():
        yield db_session

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture
def ctx(db_session):
    company = Company(name="Empresa Plat")
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)

    operator = User(
        company_id=company.id,
        name="Operador",
        email="operador@test.com",
        password_hash="unused",
        role="admin",
        is_platform_admin=True,
    )
    target = User(
        company_id=company.id,
        name="Atendente",
        email="atendente@test.com",
        password_hash="unused",
        role="agent",
    )
    target.set_password("senhaAntiga9")
    db_session.add_all([operator, target])
    db_session.commit()
    db_session.refresh(operator)
    db_session.refresh(target)
    return {"operator": operator, "target": target}


class TestPlatformResetPassword:
    def test_reset_generates_temp_password(self, db_session, ctx):
        target = ctx["target"]
        for client in _client(db_session, ctx["operator"]):
            res = client.post(f"/platform-admin/users/{target.id}/reset-password")
            assert res.status_code == 200
            body = res.json()
            assert body["user_id"] == target.id
            assert body["name"] == target.name
            assert len(body["temporary_password"]) >= 8
            assert "redefinida" in body["message"]

        db_session.refresh(target)
        assert verify_password(body["temporary_password"], target.password_hash)
        assert not verify_password("senhaAntiga9", target.password_hash)

    def test_reset_unknown_user_returns_404(self, db_session, ctx):
        for client in _client(db_session, ctx["operator"]):
            res = client.post("/platform-admin/users/999999/reset-password")
            assert res.status_code == 404

    def test_reset_requires_platform_admin(self, db_session, ctx):
        regular = User(
            company_id=ctx["target"].company_id,
            name="Regular",
            email="regular@test.com",
            password_hash="unused",
            role="owner",
        )
        db_session.add(regular)
        db_session.commit()
        db_session.refresh(regular)

        for client in _client(db_session, regular):
            res = client.post(f"/platform-admin/users/{ctx['target'].id}/reset-password")
            assert res.status_code == 403

    def test_reset_requires_auth(self, db_session, ctx):
        from app.database.session import get_db

        def _get_db():
            yield db_session

        app.dependency_overrides[get_db] = _get_db
        try:
            client = TestClient(app)
            res = client.post(f"/platform-admin/users/{ctx['target'].id}/reset-password")
            assert res.status_code == 401
        finally:
            app.dependency_overrides.clear()