"""Synthetic, in-memory regression checks for the WhatsApp trust boundary."""
import asyncio

import pytest

from app.models.appointment import Appointment
from app.models.company import Company
from app.models.customer import Customer
from app.services import agenda as ag
from app.services.agenda_tools import execute_customer_agenda_tool

PHONE = "5511000000001"
OTHER = "5511000000002"


@pytest.fixture
def bookings(db_session, company):
    cfg = ag.get_or_create(db_session, company.id)
    cfg.enabled = 1
    cfg.min_advance = 0
    cfg.schedule = ag.json_schedule({day: ["09:00", "18:00"] for day in ag.DAY_KEYS})
    other_company = Company(name="Other synthetic tenant")
    db_session.add(other_company)
    db_session.flush()
    rows = []
    for tenant, phone in [(company.id, PHONE), (company.id, OTHER), (other_company.id, PHONE)]:
        row = Appointment(company_id=tenant, phone=phone, customer_name="Synthetic",
                          date="2099-09-21", start_time="10:00", end_time="10:30",
                          status="scheduled", notes="Private synthetic note")
        db_session.add(row)
        rows.append(row)
    db_session.commit()
    return rows


def call(db, company, name, args, phone=PHONE):
    return execute_customer_agenda_tool(db, company.id, name, args, phone=phone)


def test_query_scopes_before_count_and_pagination(db_session, company, bookings):
    result = call(db_session, company, "consultar_agenda", {"date_from": "2099-01-01", "phone": OTHER})
    assert result["total"] == 1
    assert [item["id"] for item in result["items"]] == [bookings[0].id]
    assert not ({"notes", "phone", "customer_name", "customer_id", "company_id"} & result["items"][0].keys())


@pytest.mark.parametrize("index", [1, 2])
@pytest.mark.parametrize("tool", ["alterar_agendamento", "cancelar_agendamento"])
def test_rejects_other_customer_and_other_tenant(db_session, company, bookings, index, tool):
    row = bookings[index]
    result = call(db_session, company, tool, {"appointment_id": row.id, "notes": "unauthorized"})
    assert result["ok"] is False
    db_session.refresh(row)
    assert row.status == "scheduled"
    assert row.notes == "Private synthetic note"


@pytest.mark.parametrize("phone", ["", None, 123])
def test_missing_sender_fails_closed(db_session, company, bookings, phone):
    assert not call(db_session, company, "consultar_agenda", {}, phone)["ok"]


def test_create_ignores_model_phone(db_session, company, bookings):
    result = call(db_session, company, "criar_agendamento", {
        "phone": OTHER, "date": "2099-09-21", "start_time": "11:00",
    })
    assert result["ok"]
    row = db_session.get(Appointment, result["appointment_id"])
    assert row.phone == PHONE


def test_customer_can_cancel_own_booking(db_session, company, bookings):
    from app.services import agenda_confirmation as ac

    # Cancelamento via WhatsApp fica pendente de consentimento do cliente.
    result = call(db_session, company, "cancelar_agendamento", {"appointment_id": bookings[0].id})
    assert result["ok"] and result.get("awaiting_confirmation")
    db_session.refresh(bookings[0])
    assert bookings[0].status == "scheduled"

    reply = asyncio.run(ac.process_confirmation_reply(
        db_session, company_id=company.id, phone=PHONE, text="CONFIRMAR",
    ))
    assert reply["status"] == "canceled"
    db_session.refresh(bookings[0])
    assert bookings[0].status == "canceled"


def test_llm_cannot_override_confirmation_status(db_session, company, bookings):
    result = call(db_session, company, "alterar_agendamento", {
        "appointment_id": bookings[0].id, "status": "confirmed",
    })
    assert not result["ok"]
    assert bookings[0].status == "scheduled"


def test_disabled_agenda_cannot_mutate(db_session, company, bookings):
    cfg = ag.get_for_company(db_session, company.id)
    cfg.enabled = 0
    db_session.commit()
    assert not call(db_session, company, "cancelar_agendamento", {"appointment_id": bookings[0].id})["ok"]


def test_manual_customer_fk_is_tenant_scoped(db_session, company, bookings):
    other_customer = Customer(company_id=bookings[2].company_id, phone=OTHER)
    db_session.add(other_customer)
    db_session.commit()
    with pytest.raises(ag.AgendaError, match="Cliente nao encontrado"):
        ag.add_appointment(db_session, company.id, date="2099-09-21", start_time="11:00",
                           end_time="11:30", phone=PHONE, customer_id=other_customer.id)


def test_reactivation_checks_existing_conflicts(db_session, company, bookings):
    row = bookings[0]
    row.status = "canceled"
    db_session.commit()
    with pytest.raises(ag.AgendaError):
        ag.update_appointment(db_session, company.id, row.id, fields={"status": "confirmed"})
    assert row.status == "canceled"


def test_real_pipeline_binds_sender(db_session, company, config, bookings, monkeypatch):
    from app.services import conversation_service, evolution, llm
    observed = []

    async def fake_llm(**kwargs):
        result = kwargs["execute_tool"]("consultar_agenda", {"date_from": "2099-01-01"})
        observed.append(result)
        return "Synthetic reply"

    async def fake_send(**kwargs):
        return {}

    monkeypatch.setattr(llm, "generate_reply_with_tools", fake_llm)
    monkeypatch.setattr(evolution, "send_text", fake_send)
    asyncio.run(conversation_service.handle_incoming_message(
        db_session, company_id=company.id, phone=PHONE, text="agenda", wa_message_id="synthetic-security",
    ))
    assert observed and observed[0]["total"] == 1
    assert observed[0]["items"][0]["id"] == bookings[0].id


@pytest.mark.parametrize("dry_run", [False, True])
def test_workflow_scopes_tools_and_dry_run_has_no_agenda_effects(
    db_session, company, config, bookings, monkeypatch, dry_run,
):
    from app.models.workflow import Workflow
    from app.services.workflow_engine import execute_workflow
    from app.services.nodes import context
    observed = []

    async def fake_tools(**kwargs):
        result = kwargs["execute_tool"]("consultar_agenda", {"date_from": "2099-01-01"})
        observed.append(result)
        forbidden = kwargs["execute_tool"]("cancelar_agendamento", {"appointment_id": bookings[1].id})
        assert not forbidden["ok"]
        return "Synthetic reply"

    async def fake_plain(**kwargs):
        return "Synthetic preview"

    monkeypatch.setattr(context, "resolve_ai_config", lambda *a, **kw: {
        "provider": "openai", "model": "synthetic", "api_key": "synthetic", "base_url": "https://example.com",
    })
    monkeypatch.setattr(context.llm, "generate_reply_with_tools", fake_tools)
    monkeypatch.setattr(context.llm, "generate_reply", fake_plain)
    wf = Workflow(company_id=company.id, name="Synthetic security", active=True, trigger_type="message", data={
        "nodes": [{"id": "t", "type": "trigger_message", "data": {}},
                  {"id": "ai", "type": "ai", "data": {"prompt": "agenda", "history": "off"}}],
        "edges": [{"id": "e", "source": "t", "target": "ai"}],
    })
    db_session.add(wf)
    db_session.commit()
    result = asyncio.run(execute_workflow(
        db_session, workflow=wf, payload={"phone": PHONE, "message": {"text": "agenda"}},
        config=config, dry_run=dry_run,
    ))
    assert result.status == "success"
    assert not observed if dry_run else observed[0]["total"] == 1
    assert bookings[1].status == "scheduled"
