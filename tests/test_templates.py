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

    assert "webhook_recebimento" not in template_ids
    assert {
        "atendimento_basico",
        "faq_com_rag",
        "captura_lead",
        "verificacao_horario",
        "secretaria_agenda",
    } <= template_ids


def test_business_hours_template_uses_check_business_hours_node():
    template = next(t for t in TEMPLATES if t["id"] == "verificacao_horario")
    node_types = {node["id"]: node["type"] for node in template["data"]["nodes"]}
    assert node_types["bh-1"] == "check_business_hours"
    edges = template["data"]["edges"]
    assert ("bh-1", "ai-1") in [(e["source"], e["target"]) for e in edges]
    assert ("bh-1", "send-ofh-1") in [(e["source"], e["target"]) for e in edges]


def test_template_trigger_type_matches_trigger_node():
    assert template_trigger_type(next(t for t in TEMPLATES if t["id"] == "atendimento_basico")) == "message"
    assert template_trigger_type(next(t for t in TEMPLATES if t["id"] == "webhook_recebimento")) == "webhook"


def test_lead_template_sends_to_current_customer():
    template = next(t for t in TEMPLATES if t["id"] == "captura_lead")
    send_node = next(node for node in template["data"]["nodes"] if node["id"] == "send-1")
    assert send_node["data"]["phone"] == "{{ data.phone }}"


def test_lead_template_collects_data_with_capture_lead_node():
    template = next(t for t in TEMPLATES if t["id"] == "captura_lead")
    node_types = {node["id"]: node["type"] for node in template["data"]["nodes"]}

    # Fluxo completo: pede dados -> aguarda -> captura e salva -> confirma
    assert node_types["ai-1"] == "ai"
    assert node_types["wait-1"] == "wait_until_message"
    assert node_types["capture-1"] == "capture_lead"
    assert node_types["ai-2"] == "ai"

    # Solicitar dados primeiro e capturar depois da pausa
    edges = template["data"]["edges"]
    order = [(e["source"], e["target"]) for e in edges]
    assert ("ai-1", "send-1") in order
    assert ("wait-1", "capture-1") in order
    assert ("capture-1", "ai-2") in order

    capture_node = next(n for n in template["data"]["nodes"] if n["id"] == "capture-1")
    assert capture_node["data"]["overwrite"] == "on"


def test_agenda_template_sends_to_current_customer():
    template = next(t for t in TEMPLATES if t["id"] == "secretaria_agenda")
    send_node = next(node for node in template["data"]["nodes"] if node["id"] == "send-1")
    assert send_node["data"]["phone"] == "{{ data.phone }}"


def test_agenda_template_uses_ai_node_and_flow():
    template = next(t for t in TEMPLATES if t["id"] == "secretaria_agenda")
    node_types = {node["id"]: node["type"] for node in template["data"]["nodes"]}

    assert node_types["ai-1"] == "ai"
    assert node_types["send-1"] == "whatsapp_send"
    assert node_types["wait-1"] == "wait_until_message"

    edges = template["data"]["edges"]
    order = [(e["source"], e["target"]) for e in edges]
    assert ("trigger-1", "ai-1") in order
    assert ("ai-1", "send-1") in order
    assert ("send-1", "wait-1") in order
