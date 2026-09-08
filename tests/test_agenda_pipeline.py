import asyncio
import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.services import agenda as ag
from app.services import evolution as evolution_module


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


def _enable_agenda(db, company_id):
    cfg = ag.get_or_create(db, company_id)
    cfg.enabled = 1
    cfg.schedule = ag.json_schedule({"mon": ["09:00", "18:00"]})
    cfg.slot_duration = 30
    cfg.min_advance = 0
    cfg.blocked = "[]"
    db.commit()
    db.refresh(cfg)


class TestPipelineWiring:
    def test_tools_used_when_agenda_enabled(self, db_session, config, company, monkeypatch):
        from app.services import conversation_service
        from app.services import llm

        _enable_agenda(db_session, company.id)
        sent = []

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)

        async def _fake_generate_reply_with_tools(**kwargs):
            return "Resposta com agenda (tools)"

        async def _fake_generate_reply(**kwargs):
            return "Resposta sem agenda"

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)
        monkeypatch.setattr(llm, "generate_reply_with_tools", _fake_generate_reply_with_tools)
        monkeypatch.setattr(llm, "generate_reply", _fake_generate_reply)

        result = asyncio.run(conversation_service.handle_incoming_message(
            db_session, company_id=company.id, phone="5511999999999",
            text="quero agendar", wa_message_id="wamid_agenda",
        ))

        assert result["status"] == "replied"
        assert sent[0]["text"] == "Resposta com agenda (tools)"

    def test_plain_reply_when_agenda_disabled(self, db_session, config, company, monkeypatch):
        from app.services import conversation_service
        from app.services import llm

        sent = []
        calls = {"tools": 0, "plain": 0}

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)

        async def _fake_generate_reply_with_tools(**kwargs):
            calls["tools"] += 1
            return "tools"

        async def _fake_generate_reply(**kwargs):
            calls["plain"] += 1
            return "Resposta sem agenda"

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)
        monkeypatch.setattr(llm, "generate_reply_with_tools", _fake_generate_reply_with_tools)
        monkeypatch.setattr(llm, "generate_reply", _fake_generate_reply)

        result = asyncio.run(conversation_service.handle_incoming_message(
            db_session, company_id=company.id, phone="5511999999999",
            text="ola", wa_message_id="wamid_plain",
        ))

        assert result["status"] == "replied"
        assert sent[0]["text"] == "Resposta sem agenda"
        assert calls["tools"] == 0
        assert calls["plain"] == 1