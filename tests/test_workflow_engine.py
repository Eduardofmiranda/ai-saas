import pytest
import asyncio
from app.services.workflow_engine import execute_workflow, resume_workflow, WaitForMessage
from app.services.nodes.registry import list_node_types
from app.models.pending_flow import PendingFlow
from app.models.user import User
from app.models.workflow import Workflow
from fastapi import HTTPException
from app.routers.workflow_router import update_workflow
from app.schemas.workflow_schema import WorkflowUpdate


class TestWorkflowEngine:
    @pytest.mark.asyncio
    async def test_simple_ai_node(self, db_session, config, mock_payload):
        from app.models.workflow import Workflow
        wf = Workflow(
            company_id=config.company_id,
            name="AI Simples",
            active=True,
            trigger_type="message",
            data={
                "nodes": [
                    {"id": "t", "type": "trigger_message", "data": {}},
                    {"id": "ai", "type": "ai", "data": {"prompt": "Responda: {{ data.message.text }}", "history": "off"}},
                ],
                "edges": [{"id": "e1", "source": "t", "target": "ai", "sourceHandle": "", "targetHandle": ""}],
            },
        )
        db_session.add(wf)
        db_session.commit()
        db_session.refresh(wf)

        execution = await execute_workflow(db_session, workflow=wf, payload=mock_payload, config=config)
        assert execution.status == "success"
        assert "ai_reply" in execution.node_results
        assert "Responda: ola" in execution.node_results["ai_reply"]

    @pytest.mark.asyncio
    async def test_wait_until_message_pauses(self, db_session, config, mock_payload):
        from app.models.workflow import Workflow
        wf = Workflow(
            company_id=config.company_id,
            name="Wait Test",
            active=True,
            trigger_type="message",
            data={
                "nodes": [
                    {"id": "t", "type": "trigger_message", "data": {}},
                    {"id": "w", "type": "wait_until_message", "data": {}},
                    {"id": "ai", "type": "ai", "data": {"prompt": "Msg recebida: {{ data.message.text }}", "history": "off"}},
                ],
                "edges": [
                    {"id": "a", "source": "t", "target": "w"},
                    {"id": "b", "source": "w", "target": "ai"},
                ],
            },
        )
        db_session.add(wf)
        db_session.commit()
        db_session.refresh(wf)

        execution = await execute_workflow(db_session, workflow=wf, payload=mock_payload, config=config)
        assert execution.status == "waiting"

        # PendingFlow criado
        pending = db_session.query(PendingFlow).filter(PendingFlow.phone == "5511999999999").first()
        assert pending is not None
        assert (pending.snapshot or {}).get("next_node_id") == "ai"

    @pytest.mark.asyncio
    async def test_resume_after_wait(self, db_session, config, mock_payload, conversation):
        from app.models.workflow import Workflow
        wf = Workflow(
            company_id=config.company_id,
            name="Resume Test",
            active=True,
            trigger_type="message",
            data={
                "nodes": [
                    {"id": "t", "type": "trigger_message", "data": {}},
                    {"id": "w", "type": "wait_until_message", "data": {}},
                    {"id": "ai", "type": "ai", "data": {"prompt": "Segunda: {{ data.message.text }}", "history": "off"}},
                ],
                "edges": [
                    {"id": "a", "source": "t", "target": "w"},
                    {"id": "b", "source": "w", "target": "ai"},
                ],
            },
        )
        db_session.add(wf)
        db_session.commit()
        db_session.refresh(wf)

        # Primeira execucao -> waiting
        ex1 = await execute_workflow(db_session, workflow=wf, payload=mock_payload, config=config)
        assert ex1.status == "waiting"

        pending = db_session.query(PendingFlow).filter(PendingFlow.phone == "5511999999999").first()
        assert pending

        # Segunda mensagem -> resume
        payload2 = {**mock_payload, "message": {**mock_payload["message"], "text": "segunda", "wa_message_id": "wamid_456"}}
        ex2 = await resume_workflow(db_session, pending=pending, payload=payload2, config=config)
        assert ex2.status == "success"
        assert "Segunda: segunda" in ex2.node_results.get("ai_reply", "")

        # PendingFlow removido apos conclusao
        assert db_session.query(PendingFlow).filter(PendingFlow.phone == "5511999999999").first() is None

    @pytest.mark.asyncio
    async def test_condition_node_true_false(self, db_session, config, mock_payload):
        from app.models.workflow import Workflow
        wf = Workflow(
            company_id=config.company_id,
            name="Condition Test",
            active=True,
            trigger_type="message",
            data={
                "nodes": [
                    {"id": "t", "type": "trigger_message", "data": {}},
                    {"id": "set", "type": "set", "data": {"variable": "x", "value": "sim"}},
                    {"id": "cond", "type": "condition", "data": {"value": "data.x", "operator": "==", "reference": "sim"}},
                    {"id": "ai_true", "type": "ai", "data": {"prompt": "VERDADEIRO", "history": "off"}},
                    {"id": "ai_false", "type": "ai", "data": {"prompt": "FALSO", "history": "off"}},
                ],
                "edges": [
                    {"id": "e1", "source": "t", "target": "set"},
                    {"id": "e2", "source": "set", "target": "cond"},
                    {"id": "e3", "source": "cond", "target": "ai_true", "sourceHandle": "true-cell"},
                    {"id": "e4", "source": "cond", "target": "ai_false", "sourceHandle": "false-cell"},
                ],
            },
        )
        db_session.add(wf)
        db_session.commit()
        db_session.refresh(wf)

        execution = await execute_workflow(db_session, workflow=wf, payload=mock_payload, config=config)
        assert execution.status == "success"
        assert "VERDADEIRO" in execution.node_results.get("ai_reply", "")

    @pytest.mark.asyncio
    async def test_delay_node(self, db_session, config, mock_payload):
        from app.models.workflow import Workflow
        wf = Workflow(
            company_id=config.company_id,
            name="Delay Test",
            active=True,
            trigger_type="message",
            data={
                "nodes": [
                    {"id": "t", "type": "trigger_message", "data": {}},
                    {"id": "d", "type": "delay", "data": {"seconds": 0.01}},
                    {"id": "ai", "type": "ai", "data": {"prompt": "apos delay", "history": "off"}},
                ],
                "edges": [
                    {"id": "e1", "source": "t", "target": "d"},
                    {"id": "e2", "source": "d", "target": "ai"},
                ],
            },
        )
        db_session.add(wf)
        db_session.commit()
        db_session.refresh(wf)

        execution = await execute_workflow(db_session, workflow=wf, payload=mock_payload, config=config)
        assert execution.status == "success"
        assert "apos delay" in execution.node_results.get("ai_reply", "")

def test_activating_message_workflow_deactivates_other_message_workflows(db_session, company):
    user = User(
        company_id=company.id,
        name="Owner",
        email="owner@example.com",
        password_hash="not-used-in-this-unit-test",
        role="admin",
    )
    previous = Workflow(
        company_id=company.id,
        name="Previous message workflow",
        trigger_type="message",
        active=True,
    )
    target = Workflow(
        company_id=company.id,
        name="Target message workflow",
        trigger_type="message",
        active=False,
        data={"nodes": [{"id": "trigger", "type": "trigger_message", "data": {}}], "edges": []},
    )
    manual = Workflow(
        company_id=company.id,
        name="Manual workflow",
        trigger_type="manual",
        active=True,
    )
    db_session.add_all([user, previous, target, manual])
    db_session.commit()

    update_workflow(target.id, WorkflowUpdate(active=True), user, db_session)
    db_session.refresh(previous)
    db_session.refresh(target)
    db_session.refresh(manual)

    assert target.active is True
    assert previous.active is False
    assert manual.active is True


def test_activation_rejects_partial_node_graph(db_session, company):
    user = User(company_id=company.id, name="Owner", email="owner2@example.com", password_hash="not-used", role="admin")
    workflow = Workflow(
        company_id=company.id,
        name="Unsafe graph",
        trigger_type="message",
        active=False,
        data={
            "nodes": [
                {"id": "trigger", "type": "trigger_message", "data": {}},
                {"id": "code", "type": "code", "data": {"code": "result = 1"}},
            ],
            "edges": [{"source": "trigger", "target": "code"}],
        },
    )
    db_session.add_all([user, workflow])
    db_session.commit()

    with pytest.raises(HTTPException) as exc:
        update_workflow(workflow.id, WorkflowUpdate(active=True), user, db_session)

    assert exc.value.status_code == 422
    assert "code" in exc.value.detail
