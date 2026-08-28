import pytest
from app.services.nodes.registry import list_node_types, run_node, get_node_type
from app.services.nodes.context import NodeContext


class DummyConfig:
    ai_provider = "mock"
    ai_model = "mock"
    ai_api_key = "mock"
    ai_base_url = "http://mock"
    system_prompt = "test"
    evolution_base_url = "http://evo"
    evolution_api_key = "evo"
    evolution_instance = "default"


class TestNodeRegistry:
    def test_list_node_types_includes_all(self):
        types = list_node_types()
        names = {t["type"] for t in types}
        expected = {
            "trigger_message", "trigger_webhook", "ai", "set", "condition",
            "delay", "http", "whatsapp_send", "filter", "log", "wait_until_message",
        }
        assert expected.issubset(names)

    def test_get_node_type_unknown_returns_none(self):
        assert get_node_type("nao_existe") is None

    @pytest.mark.asyncio
    async def test_ai_node_with_mock(self, db_session, config):
        node = {"id": "n1", "type": "ai", "data": {"prompt": "Echo {{ data.message.text }}", "history": "off"}}
        ctx = NodeContext(
            db=db_session,
            company_id=config.company_id,
            execution_id=1,
            workflow_id=1,
            data={"message": {"text": "teste"}},
            config=config,
        )
        result = await run_node(ctx, node)
        assert "outputs" in result
        assert "ai_reply" in result["outputs"]
        assert "Echo teste" in result["outputs"]["ai_reply"]

    @pytest.mark.asyncio
    async def test_set_node(self, db_session, config):
        node = {"id": "n1", "type": "set", "data": {"variable": "minha_var", "value": "valor_123"}}
        ctx = NodeContext(
            db=db_session,
            company_id=config.company_id,
            execution_id=1,
            workflow_id=1,
            data={},
            config=config,
        )
        result = await run_node(ctx, node)
        assert result["outputs"]["minha_var"] == "valor_123"
        assert ctx.data["minha_var"] == "valor_123"

    @pytest.mark.asyncio
    async def test_condition_node_true_and_false(self, db_session, config):
        # TRUE
        ctx = NodeContext(
            db=db_session,
            company_id=config.company_id,
            execution_id=1,
            workflow_id=1,
            data={"x": "sim"},
            config=config,
        )
        node = {"id": "n1", "type": "condition", "data": {"value": "data.x", "operator": "==", "reference": "sim"}}
        result = await run_node(ctx, node)
        assert result["outputs"]["result"] is True
        assert ctx.data["condition_result"] is True

        # FALSE
        ctx2 = NodeContext(
            db=db_session,
            company_id=config.company_id,
            execution_id=2,
            workflow_id=1,
            data={"x": "nao"},
            config=config,
        )
        result2 = await run_node(ctx2, node)
        assert result2["outputs"]["result"] is False

    @pytest.mark.asyncio
    async def test_wait_until_message_returns_wait_signal(self, db_session, config):
        node = {"id": "n1", "type": "wait_until_message", "data": {}}
        ctx = NodeContext(
            db=db_session,
            company_id=config.company_id,
            execution_id=1,
            workflow_id=1,
            data={},
            config=config,
        )
        result = await run_node(ctx, node)
        assert result.get("wait_for_message") is True
        assert result.get("outputs", {}).get("waiting") is True