"""Templates prontos de workflows para novos usuarios."""
from copy import deepcopy

# Estes modelos dependem de recursos ainda parciais; ficam preservados no codigo
# como referencia, mas nao sao oferecidos para criar novos workflows.
UNAVAILABLE_TEMPLATE_IDS = frozenset({"webhook_recebimento"})


TEMPLATES = [
    {
        "id": "atendimento_basico",
        "name": "Atendimento Basico (IA)",
        "description": "Workflow basico: recebe mensagem, IA responde, aguarda proxima.",
        "category": "atendimento",
        "data": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger_message",
                    "data": {"label": "WhatsApp"},
                    "position": [250, 300],
                },
                {
                    "id": "ai-1",
                    "type": "ai",
                    "data": {
                        "label": "IA Atendente",
                        "prompt": "Responda a mensagem do cliente de forma educada e util: {{ data.message.text }}",
                        "history": "on",
                    },
                    "position": [500, 300],
                },
                {
                    "id": "send-1",
                    "type": "whatsapp_send",
                    "data": {
                        "label": "Enviar Resposta",
                        "phone": "{{ data.phone }}",
                        "text": "{{ data.ai_reply }}",
                    },
                    "position": [750, 300],
                },
                {
                    "id": "wait-1",
                    "type": "wait_until_message",
                    "data": {"label": "Aguardar Proxima"},
                    "position": [1000, 300],
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "ai-1", "sourceHandle": "success"},
                {"id": "e2", "source": "ai-1", "target": "send-1", "sourceHandle": "success"},
                {"id": "e3", "source": "send-1", "target": "wait-1", "sourceHandle": "success"},
            ],
        },
    },
    {
        "id": "faq_com_rag",
        "name": "FAQ com RAG",
        "description": "Usa base de conhecimento para responder perguntas frequentes.",
        "category": "atendimento",
        "data": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger_message",
                    "data": {"label": "Pergunta do Cliente"},
                    "position": [250, 300],
                },
                {
                    "id": "rag-1",
                    "type": "ai_rag",
                    "data": {
                        "label": "Buscar na Base",
                        "prompt": "{{ data.message.text }}",
                        "top_k": 3,
                        "system_prompt": "Responda com base na base de conhecimento. Se nao encontrar a resposta, diga que nao sabe.",
                    },
                    "position": [500, 300],
                },
                {
                    "id": "send-1",
                    "type": "whatsapp_send",
                    "data": {
                        "label": "Enviar Resposta",
                        "phone": "{{ data.phone }}",
                        "text": "{{ data.ai_reply }}",
                    },
                    "position": [750, 300],
                },
                {
                    "id": "wait-1",
                    "type": "wait_until_message",
                    "data": {"label": "Aguardar Proxima"},
                    "position": [1000, 300],
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "rag-1", "sourceHandle": "success"},
                {"id": "e2", "source": "rag-1", "target": "send-1", "sourceHandle": "success"},
                {"id": "e3", "source": "send-1", "target": "wait-1", "sourceHandle": "success"},
            ],
        },
    },
    {
        "id": "captura_lead",
        "name": "Coleta de Lead (IA)",
        "description": "A IA solicita nome, email, empresa e cidade, extrai e salva os dados no lead automaticamente e confirma com o cliente.",
        "category": "atendimento",
        "data": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger_message",
                    "data": {"label": "WhatsApp"},
                    "position": [250, 300],
                },
                {
                    "id": "ai-1",
                    "type": "ai",
                    "data": {
                        "label": "Solicitar Dados",
                        "prompt": "Voce e um assistente de vendas. Cumprimente o cliente e solicite, de forma educada e objetiva, os dados para cadastro: nome completo, email, empresa e cidade. Exemplo: \"Para agilizarmos seu atendimento, poderia me informar seu nome, email, empresa e cidade?\"",
                        "history": "on",
                    },
                    "position": [500, 300],
                },
                {
                    "id": "send-1",
                    "type": "whatsapp_send",
                    "data": {
                        "label": "Enviar Solicita\u00e7\u00e3o",
                        "phone": "{{ data.phone }}",
                        "text": "{{ data.ai_reply }}",
                    },
                    "position": [750, 300],
                },
                {
                    "id": "wait-1",
                    "type": "wait_until_message",
                    "data": {"label": "Aguardar Dados"},
                    "position": [1000, 300],
                },
                {
                    "id": "capture-1",
                    "type": "capture_lead",
                    "data": {
                        "label": "Capturar e Salvar",
                        "overwrite": "on",
                        "instruction": "Extraia exclusivamente os dados que o cliente informou na conversa.",
                    },
                    "position": [1250, 300],
                },
                {
                    "id": "ai-2",
                    "type": "ai",
                    "data": {
                        "label": "Confirmar Dados",
                        "prompt": "Confirme com o cliente os dados que ele acabou de fornecer: nome={{ data.lead.name }}, email={{ data.lead.email }}, empresa={{ data.lead.company }}, cidade={{ data.lead.city }}. Pergunte se os dados estao corretos ou se ele deseja ajustar algo.",
                        "history": "on",
                    },
                    "position": [1500, 300],
                },
                {
                    "id": "send-2",
                    "type": "whatsapp_send",
                    "data": {
                        "label": "Enviar Confirmacao",
                        "phone": "{{ data.phone }}",
                        "text": "{{ data.ai_reply }}",
                    },
                    "position": [1750, 300],
                },
                {
                    "id": "wait-2",
                    "type": "wait_until_message",
                    "data": {"label": "Continuar Atendimento"},
                    "position": [2000, 300],
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "ai-1", "sourceHandle": "success"},
                {"id": "e2", "source": "ai-1", "target": "send-1", "sourceHandle": "success"},
                {"id": "e3", "source": "send-1", "target": "wait-1", "sourceHandle": "success"},
                {"id": "e4", "source": "wait-1", "target": "capture-1", "sourceHandle": "success"},
                {"id": "e5", "source": "capture-1", "target": "ai-2", "sourceHandle": "success"},
                {"id": "e6", "source": "ai-2", "target": "send-2", "sourceHandle": "success"},
                {"id": "e7", "source": "send-2", "target": "wait-2", "sourceHandle": "success"},
            ],
        },
    },
    {
        "id": "verificacao_horario",
        "name": "Verificacao de Horario",
        "description": "Verifica se esta dentro do horario comercial configurado antes de atender.",
        "category": "logica",
        "data": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger_message",
                    "data": {"label": "Mensagem"},
                    "position": [250, 300],
                },
                {
                    "id": "bh-1",
                    "type": "check_business_hours",
                    "data": {"label": "Horario Comercial?"},
                    "position": [500, 300],
                },
                {
                    "id": "ai-1",
                    "type": "ai",
                    "data": {
                        "label": "Atender (IA)",
                        "prompt": "{{ data.message.text }}",
                        "history": "on",
                    },
                    "position": [750, 200],
                },
                {
                    "id": "send-ofh-1",
                    "type": "whatsapp_send",
                    "data": {
                        "label": "Resposta Fora do Horario",
                        "phone": "{{ data.phone }}",
                        "text": "Estamos fora do horario comercial. Retornaremos em breve!",
                    },
                    "position": [750, 400],
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "bh-1", "sourceHandle": "success"},
                {"id": "e2", "source": "bh-1", "target": "ai-1", "sourceHandle": "true"},
                {"id": "e3", "source": "bh-1", "target": "send-ofh-1", "sourceHandle": "false"},
                {"id": "e4", "source": "ai-1", "target": "send-ofh-1", "sourceHandle": "success"},
            ],
        },
    },
    {
        "id": "secretaria_agenda",
        "name": "Secretaria IA (Agenda)",
        "description": "Secretaria IA: verifica disponibilidade e cria/cancela agendamentos pela conversa. Requer a Agenda habilitada na configuracao.",
        "category": "atendimento",
        "data": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger_message",
                    "data": {"label": "WhatsApp"},
                    "position": [250, 300],
                },
                {
                    "id": "ai-1",
                    "type": "ai",
                    "data": {
                        "label": "Secretaria IA",
                        "prompt": "Voce e a Secretaria IA. Atenda o cliente de forma educada e objetiva. Identifique a intencao: agendar, consultar, remarcar ou cancelar um atendimento. Use obrigatoriamente as ferramentas da agenda disponiveis: verifique a disponibilidade antes de propor horario e confirme o horario escolhido antes de criar. Quando criar um agendamento, avise que o cliente precisa responder a confirmacao que sera enviada. Na resposta, use {nome} e {servico} quando aplicavel. Mantenha a conversa natural em portugues.",
                        "history": "on",
                    },
                    "position": [500, 300],
                },
                {
                    "id": "send-1",
                    "type": "whatsapp_send",
                    "data": {
                        "label": "Enviar Resposta",
                        "phone": "{{ data.phone }}",
                        "text": "{{ data.ai_reply }}",
                    },
                    "position": [750, 300],
                },
                {
                    "id": "wait-1",
                    "type": "wait_until_message",
                    "data": {"label": "Aguardar Proxima"},
                    "position": [1000, 300],
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "ai-1", "sourceHandle": "success"},
                {"id": "e2", "source": "ai-1", "target": "send-1", "sourceHandle": "success"},
                {"id": "e3", "source": "send-1", "target": "wait-1", "sourceHandle": "success"},
            ],
        },
    },
    {
        "id": "webhook_recebimento",
        "name": "Webhook de Recebimento",
        "description": "Recebe dados via webhook e processa com IA.",
        "category": "integracao",
        "data": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger_webhook",
                    "data": {"label": "Webhook Entrada"},
                    "position": [250, 300],
                },
                {
                    "id": "set-1",
                    "type": "set",
                    "data": {
                        "label": "Extrair Dados",
                        "variable": "input_data",
                        "value": "{{ data }}",
                    },
                    "position": [500, 300],
                },
                {
                    "id": "ai-1",
                    "type": "ai",
                    "data": {
                        "label": "Processar com IA",
                        "prompt": "Analise os dados recebidos e gere um resumo: {{ data.input_data }}",
                        "history": "off",
                    },
                    "position": [750, 300],
                },
                {
                    "id": "log-1",
                    "type": "log",
                    "data": {
                        "label": "Log Resultado",
                        "message": "Resultado: {{ data.ai_reply }}",
                    },
                    "position": [1000, 300],
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "set-1", "sourceHandle": "success"},
                {"id": "e2", "source": "set-1", "target": "ai-1", "sourceHandle": "success"},
                {"id": "e3", "source": "ai-1", "target": "log-1", "sourceHandle": "success"},
            ],
        },
    },
]


def prepare_template_data(data: dict) -> dict:
    """Converte o grafo legado para o contrato atual do React Flow."""
    graph = deepcopy(data)
    node_types = {}
    for node in graph.get("nodes", []):
        node_types[node.get("id")] = node.get("type")
        position = node.get("position")
        if isinstance(position, list) and len(position) >= 2:
            node["position"] = {"x": position[0], "y": position[1]}

    for edge in graph.get("edges", []):
        if (
            edge.get("sourceHandle") == "success"
            and node_types.get(edge.get("source")) != "condition"
        ):
            edge["sourceHandle"] = "out"
    return graph


def template_trigger_type(template: dict) -> str:
    """Deriva o tipo de disparo do node de entrada do template."""
    for node in template.get("data", {}).get("nodes", []):
        node_type = node.get("type")
        if node_type == "trigger_webhook":
            return "webhook"
        if node_type == "schedule":
            return "cron"
    return "message"


def template_is_available(template: dict) -> bool:
    return template["id"] not in UNAVAILABLE_TEMPLATE_IDS


def get_templates() -> list[dict]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
            "trigger_type": template_trigger_type(t),
        }
        for t in TEMPLATES if template_is_available(t)
    ]


def get_template(template_id: str) -> dict | None:
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
