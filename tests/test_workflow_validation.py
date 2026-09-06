from app.services.workflow_validation import validate_workflow_graph


def _valid_graph():
    return {
        "nodes": [
            {"id": "trigger", "type": "trigger_message", "data": {}},
            {"id": "ai", "type": "ai", "data": {"prompt": "Ola"}},
        ],
        "edges": [{"id": "trigger-ai", "source": "trigger", "target": "ai", "sourceHandle": "out"}],
    }


def test_valid_message_workflow_has_no_validation_errors():
    assert validate_workflow_graph(_valid_graph(), trigger_type="message") == []


def test_validation_rejects_cycle_and_dangling_edge():
    graph = _valid_graph()
    graph["edges"].extend(
        [
            {"id": "cycle", "source": "ai", "target": "trigger"},
            {"id": "missing", "source": "ai", "target": "absent"},
        ]
    )

    errors = validate_workflow_graph(graph, trigger_type="message")

    assert any("trigger" in error and "entrar" in error for error in errors)
    assert any("inexistente" in error for error in errors)


def test_validation_rejects_partial_node_and_mismatched_trigger():
    graph = _valid_graph()
    graph["nodes"][1] = {"id": "http", "type": "http", "data": {"url": "https://example.com"}}

    errors = validate_workflow_graph(graph, trigger_type="webhook")

    assert any("http" in error and "disponivel" in error for error in errors)
    assert any("nao corresponde" in error for error in errors)


def test_validation_rejects_duplicate_node_ids():
    graph = _valid_graph()
    graph["nodes"].append({"id": "ai", "type": "log", "data": {"message": "duplicado"}})

    errors = validate_workflow_graph(graph, trigger_type="message")

    assert any("duplicado" in error for error in errors)