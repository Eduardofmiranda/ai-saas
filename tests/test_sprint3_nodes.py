import pytest
from app.services.nodes.registry import list_node_types, run_node
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


class TestCodeNode:
    @pytest.mark.asyncio
    async def test_code_simple(self, db_session, config):
        node = {
            "id": "n1",
            "type": "code",
            "data": {"code": "result = len(data.get('message', {}).get('text', ''))", "result_variable": "result"},
        }
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={"message": {"text": "hello world"}}, config=config,
        )
        result = await run_node(ctx, node)
        assert result["outputs"]["result"] == 11

    @pytest.mark.asyncio
    async def test_code_error(self, db_session, config):
        node = {
            "id": "n1",
            "type": "code",
            "data": {"code": "result = 1/0", "result_variable": "result"},
        }
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={}, config=config,
        )
        from app.services.nodes.context import NodeError
        with pytest.raises(NodeError):
            await run_node(ctx, node)


class TestLoopNode:
    @pytest.mark.asyncio
    async def test_loop_basic(self, db_session, config):
        node = {
            "id": "n1",
            "type": "loop",
            "data": {"items": "items", "max_iterations": 10},
        }
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={"items": ["a", "b", "c"]}, config=config,
        )
        result = await run_node(ctx, node)
        assert result["outputs"]["count"] == 3
        assert ctx.data["_loop_items"] == ["a", "b", "c"]
        assert ctx.data["_loop_current"] == "a"

    @pytest.mark.asyncio
    async def test_loop_empty(self, db_session, config):
        node = {
            "id": "n1",
            "type": "loop",
            "data": {"items": "items"},
        }
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={}, config=config,
        )
        result = await run_node(ctx, node)
        assert result["outputs"]["count"] == 0


class TestAggregateNode:
    @pytest.mark.asyncio
    async def test_aggregate_join(self, db_session, config):
        node = {
            "id": "n1",
            "type": "aggregate",
            "data": {"mode": "join", "source": "my_list", "separator": " | "},
        }
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={"my_list": ["a", "b", "c"]}, config=config,
        )
        result = await run_node(ctx, node)
        assert result["outputs"]["result"] == "a | b | c"

    @pytest.mark.asyncio
    async def test_aggregate_count(self, db_session, config):
        node = {
            "id": "n1",
            "type": "aggregate",
            "data": {"mode": "count", "source": "my_list"},
        }
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={"my_list": [1, 2, 3, 4, 5]}, config=config,
        )
        result = await run_node(ctx, node)
        assert result["outputs"]["result"] == 5

    @pytest.mark.asyncio
    async def test_aggregate_sum(self, db_session, config):
        node = {
            "id": "n1",
            "type": "aggregate",
            "data": {"mode": "sum", "source": "my_list"},
        }
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={"my_list": [10, 20, 30]}, config=config,
        )
        result = await run_node(ctx, node)
        assert result["outputs"]["result"] == 60.0


class TestScheduleNode:
    @pytest.mark.asyncio
    async def test_schedule(self, db_session, config):
        node = {"id": "n1", "type": "schedule", "data": {"cron": "0 9 * * *"}}
        ctx = NodeContext(
            db=db_session, company_id=config.company_id, execution_id=1,
            workflow_id=1, data={}, config=config,
        )
        result = await run_node(ctx, node)
        assert result["outputs"]["triggered"] is True


class TestNodeRegistryCount:
    def test_all_node_types_present(self):
        types = list_node_types()
        names = {t["type"] for t in types}
        expected = {
            "trigger_message", "trigger_webhook", "schedule", "ai", "ai_rag",
            "set", "code", "condition", "loop", "aggregate", "delay", "http",
            "whatsapp_send", "filter", "log", "wait_until_message", "execute_workflow",
        }
        assert expected.issubset(names)

    def test_all_nodes_have_on_error(self):
        types = list_node_types()
        for t in types:
            field_keys = [f["key"] for f in t["fields"]]
            assert "on_error" in field_keys, f"{t['type']} missing on_error"
