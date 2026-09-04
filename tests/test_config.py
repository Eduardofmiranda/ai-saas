import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.main import app
from app.models.company import Company
from app.models.company_config import CompanyConfig
from app.models.user import User
from app.database.session import get_db
from app.routers.config_router import _evo_config
from app.services import llm
from app.services.config_service import get_config, get_or_create_config
from app.services.deps import get_current_user
from app.services.field_crypto import decrypt_field


class TestConfigService:
    def test_get_or_create_creates_defaults(self, db_session, company):
        cfg = get_or_create_config(db_session, company.id)
        assert cfg.company_id == company.id
        assert cfg.ai_provider == ""
        assert cfg.ai_on is True

    def test_get_config_returns_none_if_missing(self, db_session, company):
        # nao cria, so busca
        assert get_config(db_session, company.id) is None

    def test_update_encrypts_sensitive_fields(self, db_session, company, config):
        from app.services.field_crypto import encrypt_field
        # Simula o que o router faz
        config.ai_api_key = encrypt_field("gsk_NOVA_CHAVE")
        config.evolution_api_key = encrypt_field("evo_NOVA")
        db_session.commit()
        db_session.refresh(config)

        # Lidos do banco, estao criptografados
        assert config.ai_api_key.startswith("enc:")
        assert config.evolution_api_key.startswith("enc:")

        # Descriptografa corretamente
        assert decrypt_field(config.ai_api_key) == "gsk_NOVA_CHAVE"
        assert decrypt_field(config.evolution_api_key) == "evo_NOVA"

    def test_legacy_plaintext_keys_still_readable(self, db_session, company, config):
        # Simula chave legada em texto puro
        config.ai_api_key = "sk_legada_sem_enc"
        config.evolution_api_key = "evo_legada"
        db_session.commit()
        db_session.refresh(config)

        assert decrypt_field(config.ai_api_key) == "sk_legada_sem_enc"
        assert decrypt_field(config.evolution_api_key) == "evo_legada"

    def test_empty_keys_not_encrypted(self, db_session, config):
        from app.services.field_crypto import encrypt_field
        config.ai_api_key = encrypt_field("")
        config.evolution_api_key = encrypt_field(None)
        db_session.commit()
        db_session.refresh(config)

        assert config.ai_api_key == ""
        assert config.evolution_api_key is None


@pytest.fixture
def router_context(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'config_router.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()

    company = Company(name="Empresa Router")
    session.add(company)
    session.commit()
    session.refresh(company)

    user = User(
        company_id=company.id,
        name="Dono",
        email="config@test.com",
        password_hash="unused",
        role="owner",
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    def override_db():
        yield session

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = override_db
    try:
        yield TestClient(app), session, company
    finally:
        app.dependency_overrides.clear()
        session.close()
        engine.dispose()


class TestConfigRouter:
    def test_get_creates_and_returns_public_config(self, router_context):
        client, _, company = router_context
        response = client.get("/config/")
        body = response.json()

        assert response.status_code == 200
        assert body["company_id"] == company.id
        assert body["ai_provider"] == ""
        assert body["ai_model"] == ""
        assert body["has_evolution_key"] is False
        assert body["ai_on"] is True
        assert "ai_api_key" not in body
        assert "evolution_api_key" not in body

    def test_patch_encrypts_keys_and_returns_no_secret(self, router_context):
        client, db_session, company = router_context
        response = client.patch(
            "/config/",
            json={
                "ai_provider": "mock",
                "ai_api_key": "gsk_new",
                "evolution_api_key": "evo_new",
                "ai_on": False,
            },
        )

        assert response.status_code == 200
        body = response.json()
        assert body["ai_provider"] == "mock"
        assert body["ai_on"] is False
        assert "ai_api_key" not in body
        assert "evolution_api_key" not in body

        stored = get_config(db_session, company.id)
        assert stored is not None
        assert stored.ai_api_key.startswith("enc:")
        assert stored.evolution_api_key.startswith("enc:")
        assert decrypt_field(stored.ai_api_key) == "gsk_new"
        assert decrypt_field(stored.evolution_api_key) == "evo_new"

    def test_patch_masked_keys_preserves_existing_values(self, router_context):
        client, db_session, company = router_context
        existing = get_or_create_config(db_session, company.id)
        existing.ai_api_key = "mock-key"
        existing.evolution_api_key = "evo-key"
        db_session.commit()

        response = client.patch(
            "/config/",
            json={"ai_api_key": "__MASKED__", "evolution_api_key": ""},
        )

        assert response.status_code == 200
        stored = get_config(db_session, company.id)
        assert stored is not None
        assert stored.ai_api_key == "mock-key"
        assert stored.evolution_api_key == "evo-key"


class TestEvolutionConfig:
    def test_evo_config_uses_environment_fallback_and_company_instance(self, config, monkeypatch):
        config.evolution_base_url = ""
        config.evolution_api_key = ""
        config.evolution_instance = ""

        values = {
            "EVOLUTION_BASE_URL": "http://evolution:8080",
            "EVOLUTION_API_KEY": "env-key",
        }
        monkeypatch.setattr(
            "app.routers.config_router.get_secret",
            lambda name: values.get(name),
        )

        base_url, api_key, instance = _evo_config(config)

        assert base_url == "http://evolution:8080"
        assert api_key == "env-key"
        assert instance == f"inst-{config.company_id}"


@pytest.fixture
def http_db():
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
def owner(http_db):
    u = User(company_id=1, name="Dono", email="dono@test.com", role="owner")
    u.set_password("senha123")
    http_db.add(u)
    http_db.commit()
    http_db.refresh(u)
    return u


def _make(http_db, current_user):
    def _get_db():
        yield http_db

    from app.database.session import get_db

    app.dependency_overrides[get_current_user] = lambda: current_user
    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestAITestEndpoint:
    def test_ai_test_with_mock_provider(self, http_db, owner):
        http_db.add(CompanyConfig(company_id=owner.company_id, ai_provider="mock", ai_model="x"))
        http_db.commit()

        for c in _make(http_db, owner):
            res = c.post("/config/ai/test")
            assert res.status_code == 200
            data = res.json()
            assert data["ok"] is True
            assert data["provider"] == "mock"
            assert "PONG" in data.get("reply", "") or "sua mensagem" in data.get("reply", "")

    def test_ai_test_reports_provider_error(self, http_db, owner, monkeypatch):
        http_db.add(CompanyConfig(company_id=owner.company_id, ai_provider="groq", ai_model="openai/gpt-oss-120b"))
        http_db.commit()

        async def _boom(*args, **kwargs):
            raise llm.LLMError("Provedor de IA retornou erro 400: ...")

        monkeypatch.setattr(llm, "generate_reply", _boom)

        for c in _make(http_db, owner):
            res = c.post("/config/ai/test")
            assert res.status_code == 200
            data = res.json()
            assert data["ok"] is False
            assert "Provedor de IA" in data["detail"]

    def test_ai_test_uses_company_model(self, http_db, owner, monkeypatch):
        # O modelo salvo na empresa tem prioridade (mesmo que antigo/descontinuado).
        http_db.add(CompanyConfig(company_id=owner.company_id, ai_provider="groq", ai_model="mixtral-8x7b-32768"))
        http_db.commit()

        seen = {}

        async def _fake(**kwargs):
            seen["model"] = kwargs.get("model")
            return "PONG"

        monkeypatch.setattr(llm, "generate_reply", _fake)

        for c in _make(http_db, owner):
            res = c.post("/config/ai/test")
            assert res.status_code == 200
            assert res.json()["ok"] is True
        assert seen["model"] == "mixtral-8x7b-32768"