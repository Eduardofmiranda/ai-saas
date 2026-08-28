"""Templates prontos de workflows para novos usuarios."""

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
        "name": "Captura de Lead",
        "description": "Coleta dados do cliente e salva no contexto.",
        "category": "marketing",
        "data": {
            "nodes": [
                {
                    "id": "trigger-1",
                    "type": "trigger_message",
                    "data": {"label": "Nova Mensagem"},
                    "position": [250, 300],
                },
                {
                    "id": "set-1",
                    "type": "set",
                    "data": {
                        "label": "Salvar Nome",
                        "variable": "customer_name",
                        "value": "{{ data.message.text }}",
                    },
                    "position": [500, 300],
                },
                {
                    "id": "ai-1",
                    "type": "ai",
                    "data": {
                        "label": "Perguntar Email",
                        "prompt": "Obrigado {{ data.customer_name }}! Qual e seu email para podermos entrar em contato?",
                        "history": "on",
                    },
                    "position": [750, 300],
                },
                {
                    "id": "send-1",
                    "type": "whatsapp_send",
                    "data": {
                        "label": "Enviar Pergunta",
                        "text": "{{ data.ai_reply }}",
                    },
                    "position": [1000, 300],
                },
                {
                    "id": "wait-1",
                    "type": "wait_until_message",
                    "data": {"label": "Aguardar Email"},
                    "position": [1250, 300],
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "set-1", "sourceHandle": "success"},
                {"id": "e2", "source": "set-1", "target": "ai-1", "sourceHandle": "success"},
                {"id": "e3", "source": "ai-1", "target": "send-1", "sourceHandle": "success"},
                {"id": "e4", "source": "send-1", "target": "wait-1", "sourceHandle": "success"},
            ],
        },
    },
    {
        "id": "verificacao_horario",
        "name": "Verificacao de Horario",
        "description": "Verifica se esta dentro do horario comercial antes de atender.",
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
                    "id": "code-1",
                    "type": "code",
                    "data": {
                        "label": "Verificar Horario",
                        "code": "from datetime import datetime\nnow = datetime.now()\nresult = 9 <= now.hour < 18",
                        "result_variable": "is_business_hours",
                    },
                    "position": [500, 300],
                },
                {
                    "id": "cond-1",
                    "type": "condition",
                    "data": {
                        "label": "Horario Comercial?",
                        "value": "data.is_business_hours",
                        "operator": "==",
                        "reference": "True",
                    },
                    "position": [750, 300],
                },
                {
                    "id": "ai-1",
                    "type": "ai",
                    "data": {
                        "label": "Atender (IA)",
                        "prompt": "{{ data.message.text }}",
                        "history": "on",
                    },
                    "position": [1000, 200],
                },
                {
                    "id": "send-auto-1",
                    "type": "whatsapp_send",
                    "data": {
                        "label": "Resposta Automatica",
                        "text": "Estamos fora do horario comercial. Retornaremos em breve!",
                    },
                    "position": [1000, 400],
                },
            ],
            "edges": [
                {"id": "e1", "source": "trigger-1", "target": "code-1", "sourceHandle": "success"},
                {"id": "e2", "source": "code-1", "target": "cond-1", "sourceHandle": "success"},
                {"id": "e3", "source": "cond-1", "target": "ai-1", "sourceHandle": "true"},
                {"id": "e4", "source": "cond-1", "target": "send-auto-1", "sourceHandle": "false"},
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


def get_templates() -> list[dict]:
    return [
        {
            "id": t["id"],
            "name": t["name"],
            "description": t["description"],
            "category": t["category"],
        }
        for t in TEMPLATES
    ]


def get_template(template_id: str) -> dict | None:
    for t in TEMPLATES:
        if t["id"] == template_id:
            return t
    return None
