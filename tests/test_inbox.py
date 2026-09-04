import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.services.evolution as evolution_module
from app.database.database import Base
from app.main import app
from app.models.conversation import Conversation
from app.models.customer import Customer
from app.models.message import Message
from app.models.user import User
from app.routers import message_router
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


def _seed_conversation(db_session, *, company_id=1, phone="5511999999999", name="Cliente", status="open"):
    cust = db_session.query(Customer).filter_by(phone=phone).first()
    if not cust:
        cust = Customer(company_id=company_id, phone=phone, name=name)
        db_session.add(cust)
        db_session.flush()
    conv = Conversation(company_id=company_id, customer_id=cust.id, status=status)
    db_session.add(conv)
    db_session.flush()
    db_session.commit()
    return conv


class TestInboxList:
    def test_list_has_customer_last_message_and_count(self, db_session, owner):
        conv = _seed_conversation(db_session)
        customer = conv.customer
        db_session.add(Message(conversation_id=conv.id, sender_type="customer", content="ola"))
        db_session.add(Message(conversation_id=conv.id, sender_type="bot", content="oi, como posso ajudar?"))
        db_session.commit()

        for c in _make(db_session, owner):
            res = c.get("/conversations/")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1
            row = data[0]
            assert row["customer"]["name"] == "Cliente"
            assert row["customer"]["phone"] == "5511999999999"
            assert row["last_message"] == "oi, como posso ajudar?"
            assert row["message_count"] == 2
            assert row["status"] == "open"
            assert row["last_message_at"] is not None

    def test_list_scoped_by_company(self, db_session, owner):
        _seed_conversation(db_session, company_id=1, phone="5511888888888")
        _seed_conversation(db_session, company_id=99, phone="5511777777777", name="Outro")

        for c in _make(db_session, owner):
            res = c.get("/conversations/")
            assert res.status_code == 200
            data = res.json()
            assert len(data) == 1
            assert data[0]["customer"]["phone"] == "5511888888888"

    def test_conversation_outside_company_returns_404(self, db_session, owner):
        other = _seed_conversation(db_session, company_id=99, phone="5511777777777")

        for c in _make(db_session, owner):
            assert c.get(f"/conversations/{other.id}").status_code == 404


class TestReply:
    def _seed_evo_config(self, db_session, company_id):
        from app.services.config_service import get_or_create_config

        cfg = get_or_create_config(db_session, company_id)
        cfg.evolution_base_url = "http://evo"
        cfg.evolution_api_key = "evo-key"
        cfg.evolution_instance = "inst-1"
        db_session.commit()
        return cfg

    @pytest.mark.asyncio
    async def test_reply_sends_and_persists_agent_message(self, db_session, owner, monkeypatch):
        conv = _seed_conversation(db_session)
        customer = conv.customer
        self._seed_evo_config(db_session, owner.company_id)

        captured = {}

        async def fake_send_text(*, to_phone, text, base_url, api_key, instance, timeout=30.0):
            captured.update(to_phone=to_phone, text=text, base_url=base_url, api_key=api_key, instance=instance)
            return {"key": {"id": "wamid_manual"}}

        monkeypatch.setattr(message_router.evolution, "send_text", fake_send_text)

        for c in _make(db_session, owner):
            res = c.post(f"/messages/conversation/{conv.id}/reply", json={"content": "  Tudo certo!  "})
            assert res.status_code == 200
            data = res.json()
            assert data["sender_type"] == "agent"
            assert data["content"] == "Tudo certo!"

        assert captured == {
            "to_phone": customer.phone,
            "text": "Tudo certo!",
            "base_url": "http://evo",
            "api_key": "evo-key",
            "instance": "inst-1",
        }

        persisted = db_session.query(Message).filter_by(conversation_id=conv.id).all()
        assert len(persisted) == 1
        assert persisted[0].sender_type == "agent"

    def test_reply_empty_content_returns_400(self, db_session, owner):
        conv = _seed_conversation(db_session)

        for c in _make(db_session, owner):
            res = c.post(f"/messages/conversation/{conv.id}/reply", json={"content": "   "})
            assert res.status_code == 400

    def test_reply_foreign_conversation_returns_404(self, db_session, owner):
        other = _seed_conversation(db_session, company_id=99, phone="5511777777777")

        for c in _make(db_session, owner):
            res = c.post(f"/messages/conversation/{other.id}/reply", json={"content": "oi"})
            assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_reply_send_failure_returns_502(self, db_session, owner, monkeypatch):
        conv = _seed_conversation(db_session)

        async def fail_send_text(**kwargs):
            raise evolution_module.EvolutionError("Evolution offline")

        monkeypatch.setattr(message_router.evolution, "send_text", fail_send_text)

        for c in _make(db_session, owner):
            res = c.post(f"/messages/conversation/{conv.id}/reply", json={"content": "oi"})
            assert res.status_code == 502
            assert "Evolution offline" in res.json()["detail"]

        assert db_session.query(Message).filter_by(conversation_id=conv.id).count() == 0


class TestBuildHistory:
    def test_agent_messages_are_assistant(self):
        from app.services.evolution import build_history

        msgs = [
            Message(sender_type="customer", content="ola"),
            Message(sender_type="agent", content="fui eu que respondi"),
            Message(sender_type="bot", content="resposta da IA"),
            Message(sender_type="customer", content="obrigado"),
        ]
        history = build_history(msgs)
        roles = [m["role"] for m in history]
        assert roles == ["user", "assistant", "assistant", "user"]