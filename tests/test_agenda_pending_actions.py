"""Confirmacao server-side para remarcar/cancelar (consentimento real).

Fluxo testado:
- Tool de remarcar/cancelar cria pendencia em `pending_appointment_actions`
  e NAO altera o compromisso imediatamente (com `confirmation_required`).
- Cliente responde CONFIRMAR -> acao efetivada; CANCELAR -> descartada.
- Pendencia e escopada por telefone: outro numero nao confirma.
- Expiracao descarta pendencias antigas/mortas sem tocar o compromisso.
- Pipeline intercepta a resposta ANTES da IA (sem custo de LLM).
"""
import asyncio
import json
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.services import agenda as ag
from app.services import agenda_confirmation as ac
from app.services import agenda_tools as at
from app.services import evolution as evolution_module

PHONE = "5511999999999"
OTHER = "5511888888888"


@pytest.fixture
def db_session():
    """SQLite em arquivo (mesmo padrao de test_agenda_confirmation.py)."""
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


def _enable_agenda(db, company_id, *, confirmation_required=True):
    cfg = ag.get_or_create(db, company_id)
    cfg.enabled = 1
    cfg.schedule = ag.json_schedule({day: ["09:00", "18:00"] for day in ag.DAY_KEYS})
    cfg.slot_duration = 30
    cfg.min_advance = 0
    cfg.blocked = "[]"
    cfg.confirmation_required = 1 if confirmation_required else 0
    cfg.confirmation_expiry_hours = 24
    db.commit()
    db.refresh(cfg)
    return cfg


def _setup_evolution(db, company_id):
    from app.services.config_service import get_or_create_config

    config = get_or_create_config(db, company_id)
    config.evolution_base_url = "http://evo"
    config.evolution_api_key = "evo-key"
    config.evolution_instance = "default"
    db.commit()
    return config


def _create_scheduled(db, company_id, phone=PHONE, date="2026-09-21", start="10:00"):
    h, m = (int(part) for part in start.split(":"))
    end = f"{(h * 60 + m + 30) // 60:02d}:{(h * 60 + m + 30) % 60:02d}"
    return ag.add_appointment(
        db,
        company_id,
        date=date,
        start_time=start,
        end_time=end,
        phone=phone,
        customer_name="Maria",
        service="Consulta",
        origin="whatsapp",
        actor_type="system",
        user_name="Secretaria IA",
        skip_min_advance=True,
        status="scheduled",
    )


def _fake_send_factory(sends):
    async def _fake_send_text(**kwargs):
        sends.append(kwargs)
        return {}
    return _fake_send_text


def _alterar_tool(db, company_id, appt_id, **fields):
    return at.execute_customer_agenda_tool(
        db, company_id, "alterar_agendamento", {"appointment_id": appt_id, **fields}, phone=PHONE,
    )


def _cancelar_tool(db, company_id, appt_id):
    return at.execute_customer_agenda_tool(
        db, company_id, "cancelar_agendamento", {"appointment_id": appt_id}, phone=PHONE,
    )


def _reply(db, company_id, text, phone=PHONE):
    return asyncio.run(ac.process_confirmation_reply(db, company_id=company_id, phone=phone, text=text))


# ---------------------------------------------------------------------------
# Remarcar
# ---------------------------------------------------------------------------


def test_reschedule_tool_creates_pending_without_applying(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    result = _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")
    assert result["ok"] is True
    assert result["awaiting_confirmation"] is True

    db_session.refresh(appt)
    assert appt.date == "2026-09-21"
    assert appt.start_time == "10:00"

    pending = ac.find_pending_action(db_session, company.id, PHONE)
    assert pending is not None
    assert pending.action == "reschedule"
    assert pending.appointment_id == appt.id
    payload = json.loads(pending.payload)
    assert payload["date"] == "2026-09-22"
    assert payload["start_time"] == "14:00"


def test_client_confirms_reschedule(db_session, company, monkeypatch):
    _enable_agenda(db_session, company.id)
    _setup_evolution(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)
    sends = []
    monkeypatch.setattr(evolution_module, "send_text", _fake_send_factory(sends))

    result = _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")
    assert result["ok"] is True

    reply = _reply(db_session, company.id, "CONFIRMAR")

    assert reply["status"] == "confirmed"
    assert reply["appointment_id"] == appt.id
    assert reply["reply_text"]
    db_session.refresh(appt)
    assert appt.date == "2026-09-22"
    assert appt.start_time == "14:00"
    assert ac.find_pending_action(db_session, company.id, PHONE) is None
    # Mensagem de confirmacao (default da config) enviada apos efetivar.
    assert any("agendada" in m["text"].lower() for m in sends)


def test_client_rejects_reschedule_keeps_original(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")
    reply = _reply(db_session, company.id, "CANCELAR")

    assert reply["status"] == "rejected"
    db_session.refresh(appt)
    assert appt.date == "2026-09-21"
    assert appt.start_time == "10:00"
    assert appt.status == "scheduled"
    assert ac.find_pending_action(db_session, company.id, PHONE) is None


# ---------------------------------------------------------------------------
# Cancelar
# ---------------------------------------------------------------------------


def test_cancel_tool_creates_pending_without_canceling(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    result = _cancelar_tool(db_session, company.id, appt.id)
    assert result["ok"] is True
    assert result["awaiting_confirmation"] is True

    db_session.refresh(appt)
    assert appt.status == "scheduled"
    pending = ac.find_pending_action(db_session, company.id, PHONE)
    assert pending is not None
    assert pending.action == "cancel"


def test_client_confirms_cancel(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    _cancelar_tool(db_session, company.id, appt.id)
    reply = _reply(db_session, company.id, "CONFIRMAR")

    assert reply["status"] == "canceled"
    db_session.refresh(appt)
    assert appt.status == "canceled"
    assert ac.find_pending_action(db_session, company.id, PHONE) is None


def test_client_rejects_cancel_keeps_appointment(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    _cancelar_tool(db_session, company.id, appt.id)
    reply = _reply(db_session, company.id, "CANCELAR")

    assert reply["status"] == "rejected"
    db_session.refresh(appt)
    assert appt.status == "scheduled"
    assert ac.find_pending_action(db_session, company.id, PHONE) is None


# ---------------------------------------------------------------------------
# Seguranca / bordas
# ---------------------------------------------------------------------------


def test_other_phone_cannot_confirm_pending(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")
    reply = _reply(db_session, company.id, "CONFIRMAR", phone=OTHER)

    assert reply["status"] == "ignored"
    db_session.refresh(appt)
    assert appt.date == "2026-09-21"
    assert ac.find_pending_action(db_session, company.id, PHONE) is not None


def test_notes_only_change_applies_directly(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    result = _alterar_tool(db_session, company.id, appt.id, notes="Chegar 10 min antes")
    assert result["ok"] is True
    assert "awaiting_confirmation" not in result
    db_session.refresh(appt)
    assert appt.notes == "Chegar 10 min antes"
    assert ac.find_pending_action(db_session, company.id, PHONE) is None


def test_status_change_via_tool_still_rejected(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    result = at.execute_customer_agenda_tool(
        db_session, company.id, "alterar_agendamento",
        {"appointment_id": appt.id, "status": "confirmed"}, phone=PHONE,
    )
    assert result["ok"] is False
    db_session.refresh(appt)
    assert appt.status == "scheduled"


def test_direct_apply_when_confirmation_not_required(db_session, company):
    _enable_agenda(db_session, company.id, confirmation_required=False)
    appt = _create_scheduled(db_session, company.id)

    result = _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")
    assert result["ok"] is True
    assert "awaiting_confirmation" not in result
    db_session.refresh(appt)
    assert appt.date == "2026-09-22"

    result = _cancelar_tool(db_session, company.id, appt.id)
    assert result["ok"] is True
    assert "awaiting_confirmation" not in result
    db_session.refresh(appt)
    assert appt.status == "canceled"


def test_reschedule_to_occupied_slot_rejected(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id, date="2026-09-21", start="10:00")
    _create_scheduled(db_session, company.id, phone=OTHER, date="2026-09-22", start="14:00")

    result = _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")
    assert result["ok"] is False
    assert ac.find_pending_action(db_session, company.id, PHONE) is None


def test_confirm_reschedule_when_slot_taken_between(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id, date="2026-09-21", start="10:00")

    result = _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")
    assert result["ok"] is True

    # Outro cliente ocupa o slot antes da confirmacao.
    _create_scheduled(db_session, company.id, phone=OTHER, date="2026-09-22", start="14:00")

    reply = _reply(db_session, company.id, "CONFIRMAR")
    assert reply["status"] == "rejected"
    db_session.refresh(appt)
    assert appt.date == "2026-09-21"
    assert ac.find_pending_action(db_session, company.id, PHONE) is None


# ---------------------------------------------------------------------------
# Expiracao
# ---------------------------------------------------------------------------


def test_pending_action_expires_without_touching_appointment(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")
    pending = ac.find_pending_action(db_session, company.id, PHONE)
    pending.created_at = datetime.now(timezone.utc) - timedelta(hours=48)
    db_session.commit()

    expired = ac.expire_stale(db_session)
    assert ac.find_pending_action(db_session, company.id, PHONE) is None
    db_session.refresh(appt)
    assert appt.date == "2026-09-21"
    assert appt.status == "scheduled"


def test_pending_dropped_when_appointment_canceled(db_session, company):
    _enable_agenda(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)

    _cancelar_tool(db_session, company.id, appt.id)
    ag.cancel_appointment(db_session, company.id, appt.id, actor_type="user", user_name="Operador")

    ac.expire_stale(db_session)
    assert ac.find_pending_action(db_session, company.id, PHONE) is None


# ---------------------------------------------------------------------------
# Envio do pedido e pipeline
# ---------------------------------------------------------------------------


def test_send_pending_action_requests_deduplicates(db_session, company, monkeypatch):
    _enable_agenda(db_session, company.id)
    _setup_evolution(db_session, company.id)
    appt = _create_scheduled(db_session, company.id)
    sends = []
    monkeypatch.setattr(evolution_module, "send_text", _fake_send_factory(sends))

    _cancelar_tool(db_session, company.id, appt.id)
    sent = asyncio.run(ac.send_pending_action_requests_for_phone(db_session, company.id, PHONE))
    assert sent == 1
    assert any("cancelar" in m["text"].lower() for m in sends)

    # Idempotente: nao reenvia.
    sent_again = asyncio.run(ac.send_pending_action_requests_for_phone(db_session, company.id, PHONE))
    assert sent_again == 0
    assert len(sends) == 1


class TestPipeline:
    def _config(self, db_session, company):
        from app.services.config_service import get_or_create_config

        cfg = get_or_create_config(db_session, company.id)
        cfg.ai_provider = "mock"
        cfg.ai_model = "mock-model"
        cfg.ai_api_key = "mock-key"
        cfg.ai_base_url = "http://mock"
        cfg.evolution_base_url = "http://evo"
        cfg.evolution_api_key = "evo-key"
        cfg.evolution_instance = "default"
        cfg.system_prompt = "Voce e um assistente."
        cfg.ai_on = True
        db_session.commit()
        db_session.refresh(cfg)
        return cfg

    def test_pipeline_confirms_pending_reschedule_without_llm(self, db_session, company, monkeypatch):
        from app.services import conversation_service
        from app.services import llm

        self._config(db_session, company)
        _enable_agenda(db_session, company.id)
        appt = _create_scheduled(db_session, company.id)
        _alterar_tool(db_session, company.id, appt.id, date="2026-09-22", start_time="14:00")

        async def _fake_send_text(**kwargs):
            return {}

        async def _boom(**kwargs):
            raise AssertionError("IA nao deveria ser chamada para confirmar remarcacao")

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)
        monkeypatch.setattr(llm, "generate_reply", _boom)
        monkeypatch.setattr(llm, "generate_reply_with_tools", _boom)

        result = asyncio.run(conversation_service.handle_incoming_message(
            db_session, company_id=company.id, phone=PHONE,
            text="CONFIRMAR", wa_message_id="wamid_reschedule_confirm",
        ))
        assert result["status"] == "confirmed"
        db_session.refresh(appt)
        assert appt.date == "2026-09-22"
        assert appt.start_time == "14:00"

    def test_pipeline_sends_reschedule_request_after_tool(self, db_session, company, monkeypatch):
        from app.services import conversation_service
        from app.services import llm

        self._config(db_session, company)
        _enable_agenda(db_session, company.id)
        appt = _create_scheduled(db_session, company.id)
        sends = []

        async def _fake_send_text(**kwargs):
            sends.append(kwargs)
            return {}

        async def _fake_generate_reply_with_tools(**kwargs):
            result = kwargs["execute_tool"]("alterar_agendamento", {
                "appointment_id": appt.id,
                "date": "2026-09-22",
                "start_time": "14:00",
            })
            assert result["ok"] is True
            assert result["awaiting_confirmation"] is True
            return "Verifiquei e posso remarcar! Enviei um pedido de confirmacao para voce."

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)
        monkeypatch.setattr(llm, "generate_reply_with_tools", _fake_generate_reply_with_tools)

        result = asyncio.run(conversation_service.handle_incoming_message(
            db_session, company_id=company.id, phone=PHONE,
            text="quero remarcar para dia 22 as 14", wa_message_id="wamid_remarcar",
        ))
        assert result["status"] == "replied"
        # Compromisso ainda no horario original + pedido de remarcacao enviado.
        db_session.refresh(appt)
        assert appt.date == "2026-09-21"
        assert any("remarcar" in m["text"].lower() for m in sends)
