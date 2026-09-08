import asyncio
import tempfile
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.services import agenda as ag
from app.services import agenda_confirmation as ac
from app.services import evolution as evolution_module


@pytest.fixture
def db_session():
    """SQLite em arquivo (mesmo padrao de test_agenda.py / pipeline)."""
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


def _enable_agenda(db, company_id, *, confirmation_required=True, reminders=False):
    cfg = ag.get_or_create(db, company_id)
    cfg.enabled = 1
    cfg.schedule = ag.json_schedule(
        {
            "mon": ["09:00", "18:00"],
            "tue": ["09:00", "18:00"],
            "wed": ["09:00", "18:00"],
            "thu": ["09:00", "18:00"],
            "fri": ["09:00", "18:00"],
            "sat": ["09:00", "18:00"],
            "sun": ["09:00", "18:00"],
        }
    )
    cfg.slot_duration = 30
    cfg.min_advance = 0
    cfg.blocked = "[]"
    cfg.confirmation_required = 1 if confirmation_required else 0
    cfg.confirmation_expiry_hours = 24
    cfg.reminders_enabled = 1 if reminders else 0
    cfg.reminder_hours = "[24]"
    db.commit()
    db.refresh(cfg)
    return cfg


def _fmt(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"


def _create_awaiting(db, company_id, phone="5511999999999", date="2026-09-21", start="10:00"):
    h, m = (int(part) for part in start.split(":"))
    end = _fmt((h * 60 + m + 30) % (24 * 60))
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
        skip_min_advance=False,
        status=ag.AWAITING_CONFIRMATION,
    )


# ---------------------------------------------------------------------------
# Parse da resposta do cliente
# ---------------------------------------------------------------------------


class TestParseReply:
    @pytest.mark.parametrize(
        "text",
        [
            "confirmar",
            "CONFIRMAR",
            "Confirmo",
            "quero confirmar",
            "sim",
            "ok",
            "pode sim",
            "confirmado, pode",
        ],
    )
    def test_confirm(self, text):
        assert ac.parse_confirmation_reply(text) == "confirm"

    @pytest.mark.parametrize(
        "text",
        [
            "cancelar",
            "cancelado",
            "quero cancelar",
            "nao quero",
            "não quero",
            "desmarcar",
            "cancela por favor",
        ],
    )
    def test_cancel(self, text):
        assert ac.parse_confirmation_reply(text) == "cancel"

    @pytest.mark.parametrize(
        "text",
        ["", "qual o horario de amanha?", "quanto custa a consulta?", "obrigado"],
    )
    def test_ignored(self, text):
        assert ac.parse_confirmation_reply(text) is None


# ---------------------------------------------------------------------------
# Pedido de confirmacao (enviado apos criacao provisoria)
# ---------------------------------------------------------------------------


class TestSendRequest:
    @pytest.mark.asyncio
    async def test_sends_once_and_deduplicates(self, db_session, company, monkeypatch):
        cfg = _enable_agenda(db_session, company.id)
        appt = _create_awaiting(db_session, company.id)
        sent = []

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)

        status = await ac.send_confirmation_request(db_session, company.id, appt.id)
        assert status == "sent"
        assert len(sent) == 1
        assert appt.phone in sent[0]["to_phone"]
        assert "{nome}" not in sent[0]["text"]
        assert "CONFIRMAR" in sent[0]["text"]

        status2 = await ac.send_confirmation_request(db_session, company.id, appt.id)
        assert status2 == "skipped"
        assert len(sent) == 1

    @pytest.mark.asyncio
    async def test_sends_requests_for_phone(self, db_session, company, monkeypatch):
        _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id, phone="5511999999999")
        _create_awaiting(db_session, company.id, phone="5511999999999", start="10:30")
        sent = []

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)
        count = await ac.send_confirmation_requests_for_phone(db_session, company.id, "5511999999999")
        assert count == 2
        assert len(sent) == 2

    @pytest.mark.asyncio
    async def test_skips_when_no_evolution(self, db_session, company, monkeypatch):
        _enable_agenda(db_session, company.id)
        appt = _create_awaiting(db_session, company.id)

        async def _fake_send_text(**kwargs):
            raise evolution_module.EvolutionError("sem evolution")

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)
        assert await ac.send_confirmation_request(db_session, company.id, appt.id) == "send_failed"


# ---------------------------------------------------------------------------
# Processamento da resposta do cliente (interceptado antes da IA)
# ---------------------------------------------------------------------------


class TestProcessReply:
    @pytest.mark.asyncio
    async def test_confirm_flips_status_and_sends_confirmation(self, db_session, company, monkeypatch):
        cfg = _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id)
        sent = []

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)

        result = await ac.process_confirmation_reply(
            db_session, company_id=company.id, phone="5511999999999", text="CONFIRMAR"
        )
        assert result["status"] == "confirmed"
        assert result["reply_text"] == cfg.confirmation_message
        appt = ag.list_appointments(db_session, company.id)["items"][0]
        assert appt["status"] == "confirmed"
        assert len(sent) == 1

    @pytest.mark.asyncio
    async def test_cancel_releases_slot(self, db_session, company, monkeypatch):
        _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id)

        async def _fake_send_text(**kwargs):
            raise AssertionError("nao deve enviar mensagem ao cancelar")

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)

        result = await ac.process_confirmation_reply(
            db_session, company_id=company.id, phone="5511999999999", text="quero cancelar"
        )
        assert result["status"] == "canceled"
        appt = ag.list_appointments(db_session, company.id)["items"][0]
        assert appt["status"] == "canceled"
        assert appt["notes"] is None

    @pytest.mark.asyncio
    async def test_normal_message_is_ignored(self, db_session, company, monkeypatch):
        _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id)

        result = await ac.process_confirmation_reply(
            db_session, company_id=company.id, phone="5511999999999", text="qual o endereco?"
        )
        assert result["status"] == "ignored"
        appt = ag.list_appointments(db_session, company.id)["items"][0]
        assert appt["status"] == "awaiting_confirmation"

    @pytest.mark.asyncio
    async def test_no_pending_is_ignored(self, db_session, company, monkeypatch):
        _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id, phone="5511988888888")

        result = await ac.process_confirmation_reply(
            db_session, company_id=company.id, phone="5511999999999", text="CONFIRMAR"
        )
        assert result["status"] == "ignored"


# ---------------------------------------------------------------------------
# Expiracao de provisorios e lembretes
# ---------------------------------------------------------------------------


class TestBackground:
    def test_expires_only_old_provisionals(self, db_session, company):
        cfg = _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id)
        now = datetime.now(timezone.utc)

        # envelhece o created_at do unico provisorio
        old = datetime.now(timezone.utc) - timedelta(hours=25)
        from app.services import agenda_confirmation as acmod

        appt = ag.list_appointments(db_session, company.id)["items"][0]
        row = db_session.get(ag.Appointment, appt["id"])
        row.created_at = old.replace(tzinfo=None)
        db_session.commit()

        expired = ac.expire_stale(db_session, now=now)
        assert expired == 1
        assert row.status == "canceled"

    def test_new_provisional_is_not_expired(self, db_session, company):
        _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id)
        expired = ac.expire_stale(db_session, now=datetime.now(timezone.utc))
        assert expired == 0
        appt = ag.list_appointments(db_session, company.id)["items"][0]
        assert appt["status"] == "awaiting_confirmation"

    def test_reminder_sent_once_per_appointment(self, db_session, company, monkeypatch):
        from zoneinfo import ZoneInfo

        cfg = _enable_agenda(db_session, company.id, reminders=True)
        cfg.reminder_hours = "[24]"
        db_session.commit()
        db_session.refresh(cfg)

        tz = ZoneInfo("America/Sao_Paulo")
        tomorrow = datetime.now(tz).date() + timedelta(days=1)
        target = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0, tzinfo=tz)
        now = (target - timedelta(hours=23, minutes=50)).astimezone(timezone.utc)

        _create_awaiting(db_session, company.id, date=target.strftime("%Y-%m-%d"), start="10:00")
        ag.update_appointment(
            db_session,
            company.id,
            ag.list_appointments(db_session, company.id)["items"][0]["id"],
            fields={"status": "confirmed"},
        )
        sent = []

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)

        count = ac.send_due_reminders(db_session, now=now)
        assert count == 1
        assert len(sent) == 1
        assert "Lembrete" in sent[0]["text"]

        count2 = ac.send_due_reminders(db_session, now=now)
        assert count2 == 0
        assert len(sent) == 1


# ---------------------------------------------------------------------------
# Pipeline de atendimento: interceptacao antes da IA/workflow
# ---------------------------------------------------------------------------


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

    def test_incoming_message_intercepts_confirmation(self, db_session, company, monkeypatch):
        from app.services import conversation_service
        from app.services import llm

        self._config(db_session, company)
        _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id)

        async def _fake_send_text(**kwargs):
            return {}

        async def _boom(**kwargs):
            raise AssertionError("IA nao deveria ser chamada para confirmar")

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)
        monkeypatch.setattr(llm, "generate_reply", _boom)
        monkeypatch.setattr(llm, "generate_reply_with_tools", _boom)

        result = asyncio.run(conversation_service.handle_incoming_message(
            db_session, company_id=company.id, phone="5511999999999",
            text="CONFIRMAR", wa_message_id="wamid_confirm",
        ))
        assert result["status"] == "confirmed"
        appt = ag.list_appointments(db_session, company.id)["items"][0]
        assert appt["status"] == "confirmed"

    def test_incoming_workflow_intercepts_confirmation(self, db_session, company, monkeypatch):
        from app.services import conversation_service

        self._config(db_session, company)
        _enable_agenda(db_session, company.id)
        _create_awaiting(db_session, company.id)

        async def _fake_send_text(**kwargs):
            return {}

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)

        result = asyncio.run(conversation_service.handle_incoming_workflow(
            db_session, company_id=company.id, phone="5511999999999",
            text="CONFIRMO", wa_message_id="wamid_confirm_wf",
        ))
        assert result["status"] == "confirmed"
        appt = ag.list_appointments(db_session, company.id)["items"][0]
        assert appt["status"] == "confirmed"

    def test_pipeline_sends_request_after_tool_creation(self, db_session, company, monkeypatch):
        from app.services import conversation_service
        from app.services import llm

        self._config(db_session, company)
        _enable_agenda(db_session, company.id)
        sent = []

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)
            return {}

        async def _fake_generate_reply_with_tools(**kwargs):
            result = kwargs["execute_tool"]("criar_agendamento", {
                "date": "2026-09-22",
                "start_time": "10:00",
                "service": "Consulta",
                "customer_name": "Maria",
                "phone": "5511999999999",
            })
            assert result["ok"] is True
            assert result["awaiting_confirmation"] is True
            return "Certo! Enviei um pedido de confirmacao para voce no WhatsApp."

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)
        monkeypatch.setattr(llm, "generate_reply_with_tools", _fake_generate_reply_with_tools)

        result = asyncio.run(conversation_service.handle_incoming_message(
            db_session, company_id=company.id, phone="5511999999999",
            text="quero agendar dia 22 as 10", wa_message_id="wamid_agendar",
        ))
        assert result["status"] == "replied"
        # pedido de confirmacao enviado (alem da resposta da IA)
        assert any("CONFIRMAR" in m["text"] for m in sent)
        appt = ag.list_appointments(db_session, company.id)["items"][0]
        assert appt["status"] == "awaiting_confirmation"