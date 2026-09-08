import tempfile

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.models.appointment import Appointment
from app.models.appointment_event import AppointmentEvent
from app.services import agenda as ag
from app.services.agenda_tools import AGENDA_TOOLS, execute_agenda_tool


@pytest.fixture
def db_session():
    """SQLite em arquivo (mesmo padrao de test_agenda.py)."""
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


def _enable_agenda(db, company_id, *, confirmation_required=False):
    cfg = ag.get_or_create(db, company_id)
    cfg.enabled = 1
    cfg.schedule = ag.json_schedule({"mon": ["09:00", "18:00"], "tue": ["09:00", "18:00"]})
    cfg.slot_duration = 30
    cfg.min_advance = 0
    cfg.blocked = "[]"
    cfg.confirmation_required = 1 if confirmation_required else 0
    db.commit()
    db.refresh(cfg)
    return cfg


def _create_manual(db, company_id, date="2026-09-21", start="10:00", end="10:30", phone="5511999999999"):
    return ag.add_appointment(
        db, company_id, date=date, start_time=start, end_time=end, phone=phone, origin="manual"
    )


TOOL_NAMES = {"verificar_disponibilidade", "consultar_agenda", "criar_agendamento", "alterar_agendamento", "cancelar_agendamento"}


class TestSchemas:
    def test_all_five_tools_present(self):
        names = {t["function"]["name"] for t in AGENDA_TOOLS}
        assert names == TOOL_NAMES

    def test_each_tool_has_parameters(self):
        for tool in AGENDA_TOOLS:
            fn = tool["function"]
            assert fn["name"]
            assert fn["description"]
            assert fn["parameters"]["type"] == "object"


class TestDisponibilidade:
    def test_returns_slots(self, db_session, company):
        _enable_agenda(db_session, company.id)
        result = execute_agenda_tool(db_session, company.id, "verificar_disponibilidade", {"date": "2026-09-21"})
        assert result["ok"] is True
        assert result["slots"][0] == "09:00"
        assert result["slots"][-1] == "17:30"

    def test_requires_date(self, db_session, company):
        result = execute_agenda_tool(db_session, company.id, "verificar_disponibilidade", {})
        assert result["ok"] is False
        assert "data" in result["error"]

    def test_invalid_date(self, db_session, company):
        result = execute_agenda_tool(db_session, company.id, "verificar_disponibilidade", {"date": "21/09/2026"})
        assert result["ok"] is False

    def test_disabled_agenda_returns_empty(self, db_session, company):
        result = execute_agenda_tool(db_session, company.id, "verificar_disponibilidade", {"date": "2026-09-21"})
        assert result["ok"] is True
        assert result["slots"] == []


class TestCriar:
    def test_requires_phone(self, db_session, company):
        _enable_agenda(db_session, company.id)
        result = execute_agenda_tool(
            db_session, company.id, "criar_agendamento", {"date": "2026-09-21", "start_time": "10:00", "phone": ""}
        )
        assert result["ok"] is False
        assert "telefone" in result["error"].lower()

    def test_requires_active_agenda(self, db_session, company):
        result = execute_agenda_tool(
            db_session, company.id, "criar_agendamento",
            {"date": "2026-09-21", "start_time": "10:00", "phone": "5511999999999"},
        )
        assert result["ok"] is False
        assert "nao esta ativa" in result["error"]

    def test_rejects_slot_not_in_availability(self, db_session, company):
        _enable_agenda(db_session, company.id)
        result = execute_agenda_tool(
            db_session, company.id, "criar_agendamento",
            {"date": "2026-09-21", "start_time": "10:45", "phone": "5511999999999"},
        )
        assert result["ok"] is False
        assert "nao esta disponivel" in result["error"]

    def test_conflict_is_not_confirmed(self, db_session, company):
        _enable_agenda(db_session, company.id)
        _create_manual(db_session, company.id, start="10:00", end="10:30")
        result = execute_agenda_tool(
            db_session, company.id, "criar_agendamento",
            {"date": "2026-09-21", "start_time": "10:00", "phone": "5511988888888"},
        )
        assert result["ok"] is False
        assert "alternativa" in result["error"]

    def test_creates_with_origin_whatsapp_and_system_event(self, db_session, company):
        _enable_agenda(db_session, company.id)
        result = execute_agenda_tool(
            db_session, company.id, "criar_agendamento",
            {
                "date": "2026-09-21",
                "start_time": "10:00",
                "end_time": "10:30",
                "service": "Consulta",
                "customer_name": "Maria",
                "phone": "+55 11 99999-0000",
            },
        )
        assert result["ok"] is True
        appt = db_session.query(Appointment).filter(Appointment.id == result["appointment_id"]).first()
        assert appt.origin == "whatsapp"
        assert appt.customer_name == "Maria"
        assert appt.service == "Consulta"
        event = (
            db_session.query(AppointmentEvent)
            .filter(AppointmentEvent.appointment_id == appt.id)
            .order_by(AppointmentEvent.id.desc())
            .first()
        )
        assert event.action == "created"
        assert event.actor_type == "system"


class TestAlterar:
    def test_updates_appointment(self, db_session, company):
        _enable_agenda(db_session, company.id, confirmation_required=False)
        appt = _create_manual(db_session, company.id, date="2026-09-21", start="10:00", end="10:30")
        result = execute_agenda_tool(
            db_session, company.id, "alterar_agendamento",
            {"appointment_id": appt.id, "date": "2026-09-22", "start_time": "11:00", "service": "Retorno"},
        )
        assert result["ok"] is True
        db_session.refresh(appt)
        assert appt.date == "2026-09-22"
        assert appt.start_time == "11:00"
        assert appt.service == "Retorno"

    def test_rejects_reschedule_to_occupied_slot(self, db_session, company):
        _enable_agenda(db_session, company.id)
        appt = _create_manual(db_session, company.id, date="2026-09-21", start="10:00", end="10:30")
        _create_manual(db_session, company.id, date="2026-09-21", start="11:00", end="11:30", phone="5511988888888")
        result = execute_agenda_tool(
            db_session, company.id, "alterar_agendamento",
            {"appointment_id": appt.id, "start_time": "11:00", "date": "2026-09-21"},
        )
        assert result["ok"] is False

    def test_not_found(self, db_session, company):
        result = execute_agenda_tool(db_session, company.id, "alterar_agendamento", {"appointment_id": 999})
        assert result["ok"] is False


class TestCancelar:
    def test_cancels_appointment(self, db_session, company):
        _enable_agenda(db_session, company.id, confirmation_required=False)
        appt = _create_manual(db_session, company.id)
        result = execute_agenda_tool(db_session, company.id, "cancelar_agendamento", {"appointment_id": appt.id})
        assert result["ok"] is True
        db_session.refresh(appt)
        assert appt.status == "canceled"

    def test_requires_id(self, db_session, company):
        result = execute_agenda_tool(db_session, company.id, "cancelar_agendamento", {})
        assert result["ok"] is False


class TestConsultar:
    def test_lists_appointments(self, db_session, company):
        _create_manual(db_session, company.id)
        result = execute_agenda_tool(db_session, company.id, "consultar_agenda", {})
        assert result["ok"] is True
        assert result["total"] == 1
        assert result["items"][0]["date"] == "2026-09-21"

    def test_status_filter(self, db_session, company):
        appt = _create_manual(db_session, company.id)
        ag.cancel_appointment(db_session, company.id, appt.id)
        result = execute_agenda_tool(db_session, company.id, "consultar_agenda", {"status": "canceled"})
        assert result["total"] == 1
        assert result["items"][0]["status"] == "canceled"


class TestUnknown:
    def test_unknown_tool(self, db_session, company):
        result = execute_agenda_tool(db_session, company.id, "nao_existe", {})
        assert result["ok"] is False
        assert "desconhecida" in result["error"]