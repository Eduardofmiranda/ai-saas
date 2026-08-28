import pytest
import asyncio
from app.services.workflow_engine import execute_workflow, resume_workflow, WaitForMessage
from app.services.nodes.registry import list_node_types
from app.models.pending_flow import PendingFlow


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