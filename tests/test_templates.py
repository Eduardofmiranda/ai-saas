from app.services.nodes.registry import get_node_type
from app.services.templates import TEMPLATES, get_templates, prepare_template_data, template_trigger_type


def test_templates_normalize_positions_and_common_handles():
    for template in TEMPLATES:
        graph = prepare_template_data(template["data"])
        node_types = {node["id"]: node["type"] for node in graph["nodes"]}

        for node in graph["nodes"]:
            assert isinstance(node.get("position"), dict)
            assert {"x", "y"} <= node["position"].keys()
            assert get_node_type(node["type"]) is not None

        for edge in graph["edges"]:
            assert edge["source"] in node_types
            assert edge["target"] in node_types
            if node_types[edge["source"]] != "condition":
                assert edge.get("sourceHandle") != "success"


def test_unavailable_templates_are_not_offered_to_users():
    template_ids = {template["id"] for template in get_templates()}

    assert "verificacao_horario" not in template_ids
    assert "webhook_recebimento" not in template_ids
    assert {"atendimento_basico", "faq_com_rag", "captura_lead"} <= template_ids


def test_template_trigger_type_matches_trigger_node():
    assert template_trigger_type(next(t for t in TEMPLATES if t["id"] == "atendimento_basico")) == "message"
    assert template_trigger_type(next(t for t in TEMPLATES if t["id"] == "webhook_recebimento")) == "webhook"


def test_lead_template_sends_to_current_customer():
    template = next(t for t in TEMPLATES if t["id"] == "captura_lead")
    send_node = next(node for node in template["data"]["nodes"] if node["id"] == "send-1")
    assert send_node["data"]["phone"] == "{{ data.phone }}"
