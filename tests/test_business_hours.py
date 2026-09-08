import asyncio
from datetime import datetime

import pytest

from app.models.business_hours import BusinessHours
from app.models.execution import Execution
from app.models.workflow import Workflow
from app.services import business_hours as bh
from app.services import evolution as evolution_module
from app.services.conversation_service import handle_incoming_workflow
from app.services.nodes.context import NodeContext
from app.services.nodes.registry import list_node_types, run_node


def _bh(company_id=1, enabled=True, schedule="{}", timezone="America/Sao_Paulo", message="Fechado"):
    return BusinessHours(
        company_id=1,
        enabled=enabled,
        schedule=schedule,
        timezone=timezone,
        message=message,
    )


class TestParseSchedule:
    def test_returns_none_for_missing_days(self):
        s = bh.parse_schedule('{"mon": ["09:00", "18:00"]}')
        assert s["mon"] == ("09:00", "18:00")
        assert s["tue"] is None

    def test_invalid_entries_dropped(self):
        s = bh.parse_schedule({"mon": ["9", "18:00"], "tue": ["aa:bb", "x"], "wed": []})
        assert s["mon"] is None
        assert s["tue"] is None
        assert s["wed"] is None


class TestIsOpen:
    def test_disabled_is_always_open(self, db_session):
        record = _bh(enabled=False, schedule='{"mon": ["09:00", "18:00"]}')
        assert bh.is_open(record, now_local=datetime(2026, 9, 7, 5, 0)) is True
        assert bh.is_open(record, now_local=datetime(2026, 9, 6, 23, 0)) is True

    def test_empty_schedule_fails_open(self):
        record = _bh(enabled=True, schedule="{}")
        assert bh.is_open(record) is True

    def test_invalid_schedule_fails_open(self):
        record = _bh(enabled=True, schedule='{"mon": ["10:00", "18:00", "extra"]}')
        assert bh.is_open(record) is True

    def test_open_within_window(self):
        record = _bh(enabled=True, schedule='{"mon": ["09:00", "18:00"]}')
        assert bh.is_open(record, now_local=datetime(2026, 9, 7, 10, 0)) is True

    def test_closed_outside_window(self):
        record = _bh(enabled=True, schedule='{"mon": ["09:00", "18:00"]}')
        assert bh.is_open(record, now_local=datetime(2026, 9, 7, 8, 59)) is False
        assert bh.is_open(record, now_local=datetime(2026, 9, 7, 18, 0)) is False

    def test_closed_on_unconfigured_day(self):
        record = _bh(enabled=True, schedule='{"mon": ["09:00", "18:00"]}')
        assert bh.is_open(record, now_local=datetime(2026, 9, 12, 10, 0)) is False

    def test_window_crossing_midnight(self):
        record = _bh(enabled=True, schedule='{"fri": ["18:00", "02:00"]}')
        assert bh.is_open(record, now_local=datetime(2026, 9, 4, 19, 0)) is True
        assert bh.is_open(record, now_local=datetime(2026, 9, 4, 23, 0)) is True


class TestCheckBusinessHoursNode:
    def test_node_registered_and_available(self):
        types = {t["type"]: t for t in list_node_types()}
        node = types.get("check_business_hours")
        assert node is not None
        assert node["category"] == "logic"
        assert node["editor_available"] is True

    @pytest.mark.asyncio
    async def test_open_when_no_schedule(self, db_session, config, monkeypatch):
        from app.services import business_hours

        monkeypatch.setattr(
            business_hours, "_local_now",
            lambda instance: datetime(2026, 9, 7, 22, 0),
        )
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={"phone": "1"}, config=config,
        )
        node = {"id": "bh-1", "type": "check_business_hours", "data": {"label": "x"}}
        result = await run_node(ctx, node)
        assert result["outputs"]["business_hours"] is True

    @pytest.mark.asyncio
    async def test_closed_when_inside_config(self, db_session, config, monkeypatch):
        from app.services import business_hours

        db_session.add(_bh(
            company_id=config.company_id, enabled=True,
            schedule='{"mon": ["09:00", "18:00"]}',
        ))
        db_session.commit()

        monkeypatch.setattr(
            business_hours, "_local_now",
            lambda instance: datetime(2026, 9, 7, 22, 0),
        )
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={"phone": "1"}, config=config,
        )
        node = {"id": "bh-1", "type": "check_business_hours", "data": {"label": "x"}}
        result = await run_node(ctx, node)
        assert result["outputs"]["business_hours"] is False
        assert result["outputs"]["is_business_hours"] is False

    @pytest.mark.asyncio
    async def test_open_when_inside_window(self, db_session, config, monkeypatch):
        from app.services import business_hours

        db_session.add(_bh(
            company_id=config.company_id, enabled=True,
            schedule='{"mon": ["09:00", "18:00"]}',
        ))
        db_session.commit()

        monkeypatch.setattr(
            business_hours, "_local_now",
            lambda instance: datetime(2026, 9, 7, 10, 0),
        )
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={"phone": "1"}, config=config,
        )
        node = {"id": "bh-1", "type": "check_business_hours", "data": {"label": "x"}}
        result = await run_node(ctx, node)
        assert result["outputs"]["business_hours"] is True


class TestClosedGate:
    def _make_workflow(self, db_session, company_id):
        wf = Workflow(
            company_id=company_id,
            name="Voce conseguiu chegar aqui",
            active=True,
            trigger_type="message",
            data={
                "nodes": [
                    {"id": "trigger-1", "type": "trigger_message", "data": {"label": "Msg"}, "position": [0, 0]},
                    {"id": "ai-1", "type": "ai", "data": {"prompt": "resposta legal"}, "position": [1, 1]},
                    {"id": "wait-1", "type": "wait_until_message", "data": {"label": "Espera"}, "position": [2, 2]},
                ],
                "edges": [
                    {"id": "e1", "source": "trigger-1", "target": "ai-1", "sourceHandle": "success"},
                    {"id": "e2", "source": "ai-1", "target": "wait-1", "sourceHandle": "success"},
                ],
            },
        )
        db_session.add(wf)
        db_session.commit()
        db_session.refresh(wf)
        return wf

    def _closed_schedule(self, db_session, company_id):
        db_session.add(_bh(
            company_id=company_id, enabled=True,
            schedule='{"mon": ["09:00", "18:00"]}', message="Fora do horario, volte amanha!",
        ))
        db_session.commit()

    def test_closed_sends_message_once_and_skips_workflow(self, db_session, config, company, monkeypatch):
        from app.services import business_hours

        self._closed_schedule(db_session, company.id)
        self._make_workflow(db_session, company.id)

        monkeypatch.setattr(
            business_hours, "_local_now",
            lambda instance: datetime(2026, 9, 7, 22, 0),
        )
        sent = []

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)

        result = asyncio.run(handle_incoming_workflow(
            db_session, company_id=company.id, phone="5511999999999",
            text="oi", wa_message_id="wamid_1",
        ))
        assert result["status"] == "closed"
        assert len(sent) == 1
        assert sent[0]["text"] == "Fora do horario, volte amanha!"
        assert db_session.query(Execution).count() == 0

        # Segunda mensagem do mesmo cliente nao envia de novo
        result2 = asyncio.run(handle_incoming_workflow(
            db_session, company_id=company.id, phone="5511999999999",
            text="oi de novo", wa_message_id="wamid_2",
        ))
        assert result2["status"] == "closed"
        assert len(sent) == 1

    def test_open_does_not_gate(self, db_session, config, company, monkeypatch):
        from app.services import business_hours

        self._closed_schedule(db_session, company.id)
        self._make_workflow(db_session, company.id)

        monkeypatch.setattr(
            business_hours, "_local_now",
            lambda instance: datetime(2026, 9, 7, 11, 0),
        )
        sent = []

        async def _fake_send_text(**kwargs):
            sent.append(kwargs)

        monkeypatch.setattr(evolution_module, "send_text", _fake_send_text)

        result = asyncio.run(handle_incoming_workflow(
            db_session, company_id=company.id, phone="5511999999999",
            text="oi", wa_message_id="wamid_1",
        ))
        assert result["status"] == "success"
        assert db_session.query(Execution).count() == 1