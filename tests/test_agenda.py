import tempfile

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database.database import Base
from app.services import agenda as ag
from app.models.appointment import Appointment
from app.models.appointment_event import AppointmentEvent


@pytest.fixture
def db_session():
    """SQLite em arquivo (funciona com TestClient, que roda endpoints em outra thread)."""
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


def _enable_agenda(db, company_id, *, schedule=None, duration=30, min_advance=0, blocked=None):
    cfg = ag.get_or_create(db, company_id)
    cfg.enabled = 1
    if schedule is None:
        schedule = {"mon": ["09:00", "18:00"]}
    cfg.schedule = ag.json_schedule(schedule)
    cfg.slot_duration = duration
    cfg.min_advance = min_advance
    cfg.blocked = "[]" if blocked is None else ag.json.dumps(ag.parse_blocked(blocked), ensure_ascii=False)
    db.commit()
    db.refresh(cfg)
    return cfg


class TestAvailability:
    def test_disabled_returns_no_slots(self, db_session, company):
        assert ag.build_slots(db_session, company.id, "2026-09-07") == []

    def test_window_returns_all_slots(self, db_session, company):
        _enable_agenda(db_session, company.id, duration=30)
        slots = ag.build_slots(db_session, company.id, "2026-09-21")
        assert slots[0] == "09:00"
        assert slots[-1] == "17:30"
        assert len(slots) == 18

    def test_closed_day_returns_no_slots(self, db_session, company):
        _enable_agenda(db_session, company.id, schedule={"mon": ["09:00", "18:00"]})
        # 2026-09-21 = segunda (aberta), 2026-09-26 = sabado (fechado)
        assert ag.build_slots(db_session, company.id, "2026-09-26") == []

    def test_occupied_slot_is_excluded(self, db_session, company):
        _enable_agenda(db_session, company.id)
        ag.add_appointment(
            db_session, company.id, date="2026-09-21", start_time="09:00",
            end_time="10:00", phone="5511999999999",
        )
        slots = ag.build_slots(db_session, company.id, "2026-09-21")
        assert "09:00" not in slots
        assert "09:30" not in slots
        assert "10:00" in slots

    def test_blocked_range_is_excluded(self, db_session, company):
        _enable_agenda(db_session, company.id, blocked=[{"date": "2026-09-21", "start": "10:00", "end": "11:00"}])
        slots = ag.build_slots(db_session, company.id, "2026-09-21")
        assert "10:00" not in slots
        assert "09:30" in slots

    def test_min_advance_filter(self, db_session, company):
        _enable_agenda(db_session, company.id, duration=60, min_advance=120)
        from datetime import datetime
        now = datetime(2026, 9, 7, 8, 0)
        slots = ag.build_slots(db_session, company.id, "2026-09-07", now=now)
        # inicio tem que ser >= 10:00 (08:00 + 120min)
        assert "09:00" not in slots
        assert "10:00" in slots


class TestConflict:
    def test_overlap_detected(self, db_session, company):
        ag.add_appointment(
            db_session, company.id, date="2026-09-07", start_time="09:00",
            end_time="10:00", phone="5511999999999",
        )
        assert ag.has_conflict(db_session, company.id, "2026-09-07", "09:30", "10:30") is True
        assert ag.has_conflict(db_session, company.id, "2026-09-07", "10:00", "11:00") is False

    def test_canceled_does_not_conflict(self, db_session, company):
        appt = ag.add_appointment(
            db_session, company.id, date="2026-09-07", start_time="09:00",
            end_time="10:00", phone="5511999999999",
        )
        ag.cancel_appointment(db_session, company.id, appt.id)
        assert ag.has_conflict(db_session, company.id, "2026-09-07", "09:00", "10:00") is False


class TestCRUD:
    def test_add_without_agenda_allows_manual(self, db_session, company):
        appt = ag.add_appointment(
            db_session, company.id, date="2026-09-07", start_time="14:00",
            end_time="15:00", phone="5511999999999", service="Consulta",
        )
        assert appt.status == "scheduled"
        assert appt.service == "Consulta"
        event = db_session.query(AppointmentEvent).filter(AppointmentEvent.appointment_id == appt.id).one()
        assert event.action == "created"

    def test_add_conflict_raises(self, db_session, company):
        ag.add_appointment(
            db_session, company.id, date="2026-09-07", start_time="09:00",
            end_time="10:00", phone="5511999999999",
        )
        with pytest.raises(ag.AgendaError) as exc:
            ag.add_appointment(
                db_session, company.id, date="2026-09-07", start_time="09:30",
                end_time="10:30", phone="5511999999999",
            )
        assert exc.value.code == "conflict"

    def test_add_outside_window_raises(self, db_session, company):
        _enable_agenda(db_session, company.id)
        with pytest.raises(ag.AgendaError) as exc:
            ag.add_appointment(
                db_session, company.id, date="2026-09-07", start_time="19:00",
                end_time="20:00", phone="5511999999999",
            )
        assert exc.value.code == "window_closed"

    def test_update_reschedules_and_logs(self, db_session, company):
        appt = ag.add_appointment(
            db_session, company.id, date="2026-09-07", start_time="09:00",
            end_time="10:00", phone="5511999999999",
        )
        ag.update_appointment(
            db_session, company.id, appt.id,
            fields={"date": "2026-09-08", "start_time": "11:00", "end_time": "12:00"},
        )
        db_session.refresh(appt)
        assert (appt.date, appt.start_time, appt.end_time) == ("2026-09-08", "11:00", "12:00")
        actions = [e.action for e in db_session.query(AppointmentEvent).all()]
        assert actions == ["created", "rescheduled"]

    def test_update_conflict_excludes_self(self, db_session, company):
        _enable_agenda(db_session, company.id)
        appt = ag.add_appointment(
            db_session, company.id, date="2026-09-07", start_time="09:00",
            end_time="10:00", phone="5511999999999",
        )
        # manter o mesmo intervalo nao deve ser tratado como conflito
        updated = ag.update_appointment(
            db_session, company.id, appt.id,
            fields={"date": "2026-09-07", "start_time": "09:00", "end_time": "10:00"},
        )
        assert updated.date == "2026-09-07"

    def test_cancel_marks_and_logs(self, db_session, company):
        appt = ag.add_appointment(
            db_session, company.id, date="2026-09-07", start_time="09:00",
            end_time="10:00", phone="5511999999999",
        )
        ag.cancel_appointment(db_session, company.id, appt.id)
        db_session.refresh(appt)
        assert appt.status == "canceled"
        actions = [e.action for e in db_session.query(AppointmentEvent).all()]
        assert actions == ["created", "canceled"]

    def test_list_filters(self, db_session, company):
        ag.add_appointment(db_session, company.id, date="2026-09-07", start_time="09:00", end_time="10:00", phone="1")
        ag.add_appointment(db_session, company.id, date="2026-09-10", start_time="09:00", end_time="10:00", phone="2")
        result = ag.list_appointments(db_session, company.id, status="scheduled")
        assert result["total"] == 2
        assert len(result["items"]) == 2
        result2 = ag.list_appointments(db_session, company.id, date_from="2026-09-08")
        assert result2["total"] == 1
        assert result2["items"][0]["date"] == "2026-09-10"


# ---------------------------------------------------------------------------
# Router (API)
# ---------------------------------------------------------------------------


def _make_user(db, *, company_id, role="admin", name="Operador", email="op@test.com", is_platform_admin=False):
    from app.models.user import User

    user = User(company_id=company_id, name=name, email=email, password_hash="unused", role=role, is_platform_admin=is_platform_admin)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _client(db_session, user):
    from app.database.session import get_db
    from app.services.deps import get_current_user

    def _get_db():
        yield db_session

    app = pytest.importorskip("app.main").app
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = _get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


class TestConfigApi:
    def test_get_config_returns_default(self, db_session, company):
        user = _make_user(db_session, company_id=company.id)
        for client in _client(db_session, user):
            res = client.get("/agenda/config")
            assert res.status_code == 200
            body = res.json()
            assert body["enabled"] is False
            assert body["slot_duration"] == 30
            assert body["min_advance"] == 60
            assert body["schedule"]["mon"] == ["09:00", "18:00"]

    def test_put_config_saves(self, db_session, company):
        user = _make_user(db_session, company_id=company.id, role="admin")
        for client in _client(db_session, user):
            res = client.put("/agenda/config", json={
                "enabled": True,
                "schedule": {"mon": ["08:00", "12:00"]},
                "slot_duration": 60,
                "min_advance": 30,
                "blocked": [{"date": "2026-09-07", "start": "09:00", "end": "10:00"}],
                "confirmation_message": "Confirmado",
            })
            assert res.status_code == 200
            body = res.json()
            assert body["enabled"] is True
            assert body["schedule"]["mon"] == ["08:00", "12:00"]
            assert body["slot_duration"] == 60
            assert len(body["blocked"]) == 1

            res2 = client.get("/agenda/config")
            assert res2.json()["enabled"] is True

    def test_put_config_rejects_invalid(self, db_session, company):
        user = _make_user(db_session, company_id=company.id, role="admin")
        for client in _client(db_session, user):
            res = client.put("/agenda/config", json={"slot_duration": 0})
            assert res.status_code == 400
            res = client.put("/agenda/config", json={"schedule": {"mon": ["18:00", "09:00"]}})
            assert res.status_code == 400

    def test_put_config_requires_manager(self, db_session, company):
        user = _make_user(db_session, company_id=company.id, role="agent")
        for client in _client(db_session, user):
            res = client.put("/agenda/config", json={"enabled": True})
            assert res.status_code == 403


class TestAppointmentsApi:
    def test_availability(self, db_session, company):
        _enable_agenda(db_session, company.id)
        user = _make_user(db_session, company_id=company.id)
        for client in _client(db_session, user):
            res = client.get("/agenda/availability", params={"date": "2026-09-21"})
            assert res.status_code == 200
            assert res.json()["slots"][0] == "09:00"
            assert len(res.json()["slots"]) == 18

    def test_create_and_conflict_409(self, db_session, company):
        _enable_agenda(db_session, company.id)
        user = _make_user(db_session, company_id=company.id)
        payload = {"date": "2026-09-21", "start_time": "09:00", "end_time": "10:00", "phone": "5511999999999"}
        for client in _client(db_session, user):
            res = client.post("/agenda/appointments", json=payload)
            assert res.status_code == 200
            assert res.json()["status"] == "scheduled"

            res = client.post("/agenda/appointments", json={
                **payload, "start_time": "09:30", "end_time": "10:30",
            })
            assert res.status_code == 409

    def test_crud_flow(self, db_session, company):
        _enable_agenda(db_session, company.id)
        user = _make_user(db_session, company_id=company.id)
        for client in _client(db_session, user):
            created = client.post("/agenda/appointments", json={
                "date": "2026-09-21", "start_time": "14:00", "end_time": "15:00",
                "phone": "5511999999999", "service": "Reuniao",
            })
            appt_id = created.json()["id"]

            updated = client.patch(f"/agenda/appointments/{appt_id}", json={"status": "confirmed"})
            assert updated.json()["status"] == "confirmed"

            canceled = client.delete(f"/agenda/appointments/{appt_id}")
            assert canceled.json()["status"] == "canceled"

            assert client.get("/agenda/appointments").json()["total"] == 1
            assert client.get("/agenda/appointments", params={"status": "scheduled"}).json()["total"] == 0

    def test_isolation_between_companies(self, db_session, company):
        from app.models.company import Company

        _enable_agenda(db_session, company.id)
        appt = ag.add_appointment(
            db_session, company.id, date="2026-09-21", start_time="09:00",
            end_time="10:00", phone="5511999999999",
        )

        other = Company(name="Outra")
        db_session.add(other)
        db_session.commit()
        other_user = _make_user(db_session, company_id=other.id)

        for client in _client(db_session, other_user):
            assert client.get("/agenda/appointments").json()["total"] == 0
            assert client.get(f"/agenda/appointments/{appt.id}").status_code == 404
            res = client.delete(f"/agenda/appointments/{appt.id}")
            assert res.status_code == 404

        db_session.refresh(appt)
        assert appt.status == "scheduled"