"""Catalogo de tipos de no do motor de workflows.

Cada tipo de no descreve: identificacao, campos de configuracao (para o editor) e
uma funcao run(ctx, node) que executa a logica e retorna um NodeResult.

NodeResult:
    {
        "outputs": {...},       # dados de saida do no (mesclados no contexto)
        "next": str | None,     # id do proximo no (se nao especificado, segue as edges)
        "stop": bool,           # se True, encerra o fluxo
    }
"""
from __future__ import annotations

import asyncio
import json
import re

from app.config import get_secret
from app.services import llm
from app.services.nodes.context import NodeError
from app.services.nodes.rag_node import run_rag_node

# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------


def _resolve_path(data: dict, path: str):
    """Acessa data["a"]["b"] usando a notacao a.b.c. Retorna None se inexistente."""
    cur = data
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def _eval_condition(left, operator: str, right) -> bool:
    try:
        if operator == "==":
            return left == right
        if operator == "!=":
            return left != right
        if operator == "contains":
            return str(right) in str(left) if left is not None else False
        if operator == "not_contains":
            return str(right) not in str(left) if left is not None else True
        if operator == ">":
            return float(left) > float(right)
        if operator == "<":
            return float(left) < float(right)
        if operator == ">=":
            return float(left) >= float(right)
        if operator == "<=":
            return float(left) <= float(right)
        if operator == "is_true":
            return bool(left) is True
        if operator == "is_empty":
            return left in (None, "", [], {})
        if operator == "is_not_empty":
            return left not in (None, "", [], {})
    except (TypeError, ValueError):
        return False
    return False


def _eval_expression(text: str, data: dict) -> str:
    """Substitui {{ data.campo }} pelo valor do contexto."""

    def repl(m):
        return str(_resolve_path(data, m.group(1)) or "")

    return re.sub(r"{{\s*data\.([\w.]+)\s*}}", repl, text)


# ---------------------------------------------------------------
# Implementacoes dos nos
# ---------------------------------------------------------------


async def _run_ai(ctx, node):
    cfg = node.get("data", {})
    prompt = _eval_expression(cfg.get("prompt", ""), ctx.data)
    use_history = str(cfg.get("history", "on")) not in ("", "off", "false", "False")
    system_prompt = cfg.get("system_prompt", "") or None

    history_msgs = await ctx.load_history(force=use_history)
    if history_msgs:
        ctx.log(f"Igualando com {len(history_msgs)} mensagens de historico")

    reply = await ctx.ask_ai(
        prompt,
        history=history_msgs or None,
        system_prompt=system_prompt,
    )
    ctx.data["ai_reply"] = reply
    await ctx.save_bot_message(reply)
    ctx.log(f"IA respondeu: {reply[:80]}...")
    return {"outputs": {"ai_reply": reply}}


async def _run_set(ctx, node):
    cfg = node.get("data", {})
    var = cfg.get("variable", "")
    value = cfg.get("value", "")
    value = _eval_expression(str(value), ctx.data)
    ctx.data[var] = value
    ctx.log(f"definida variavel {var}={value}")
    return {"outputs": {var: value}}


async def _run_condition(ctx, node):
    cfg = node.get("data", {})
    value_path = cfg.get("value", "")
    operator = cfg.get("operator", "==")
    reference = cfg.get("reference", "")
    reference = _eval_expression(str(reference), ctx.data)

    left = _resolve_path(ctx.data, value_path.lstrip("data.")) if value_path else ctx.data.get(value_path.lstrip("data."))

    result = _eval_condition(left, operator, reference)
    ctx.data["condition_result"] = result
    ctx.log(f"condicao {value_path} {operator} {reference} -> {result}")
    return {"outputs": {"result": result}}


async def _run_delay(ctx, node):
    cfg = node.get("data", {})
    seconds = float(cfg.get("seconds", 1))
    await asyncio.sleep(seconds)
    ctx.log(f"aguardou {seconds}s")
    return {"outputs": {"seconds": seconds}}


async def _run_http(ctx, node):
    cfg = node.get("data", {})
    method = cfg.get("method", "GET").upper()
    url = _eval_expression(cfg.get("url", ""), ctx.data)
    body_raw = cfg.get("body", "")
    headers_raw = cfg.get("headers", "")
    query_raw = cfg.get("query", "")
    import httpx

    headers = {"Content-Type": "application/json"}
    if headers_raw:
        try:
            parsed_headers = json.loads(headers_raw) if isinstance(headers_raw, str) else headers_raw
            headers.update(parsed_headers)
        except json.JSONDecodeError:
            pass

    params = None
    if query_raw:
        try:
            params = json.loads(query_raw) if isinstance(query_raw, str) else query_raw
        except json.JSONDecodeError:
            pass

    body = None
    if body_raw:
        body = json.loads(_eval_expression(body_raw, ctx.data))

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.request(method, url, json=body, headers=headers, params=params)

    try:
        parsed = resp.json()
    except Exception:
        parsed = resp.text

    ctx.data["http_status"] = resp.status_code
    ctx.data["http_body"] = parsed
    ctx.log(f"HTTP {method} {url} -> {resp.status_code}")
    return {"outputs": {"status": resp.status_code, "body": parsed}}


async def _run_whatsapp_send(ctx, node):
    cfg = node.get("data", {})
    phone = _eval_expression(cfg.get("phone", ""), ctx.data)
    text = _eval_expression(cfg.get("text", ""), ctx.data)
    result = await ctx.send_whatsapp(phone, text)
    ctx.log(f"WhatsApp para {phone}: {text[:60]}... (sent={result['sent']})")
    return {"outputs": result}


async def _run_filter(ctx, node):
    cfg = node.get("data", {})
    condition_bool = cfg.get("keep_if", True)
    ctx.log("no de filtro executado")
    return {"outputs": {"keep": bool(condition_bool)}}


async def _run_log(ctx, node):
    cfg = node.get("data", {})
    msg = _eval_expression(cfg.get("message", ""), ctx.data)
    ctx.log(f"[log] {msg}")
    return {"outputs": {"message": msg}}


async def _run_lookup(ctx, node):
    cfg = node.get("data", {})
    field = cfg.get("field", "customer")
    ctx.log(f"lookup de {field} executado")
    return {"outputs": {}}


# --- Sprint 3: Novos nos ---


async def _run_code(ctx, node):
    cfg = node.get("data", {})
    code = cfg.get("code", "")
    code = _eval_expression(code, ctx.data)

    sandbox_vars = {
        "data": ctx.data,
        "json": json,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
        "len": len,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "map": map,
        "filter": filter,
        "sorted": sorted,
        "list": list,
        "dict": dict,
        "True": True,
        "False": False,
        "None": None,
    }

    try:
        exec(code, {"__builtins__": {}}, sandbox_vars)
    except Exception as exc:
        raise NodeError(f"Erro no codigo: {exc}", node.get("id", ""))

    result_var = cfg.get("result_variable", "code_result")
    result = sandbox_vars.get(result_var, sandbox_vars.get("result"))
    ctx.data[result_var] = result
    ctx.log(f"code executado, resultado em {result_var}")
    return {"outputs": {result_var: result}}


async def _run_loop(ctx, node):
    cfg = node.get("data", {})
    items_path = cfg.get("items", "items")
    items = _resolve_path(ctx.data, items_path.lstrip("data."))
    if items is None:
        items = []

    max_iterations = int(cfg.get("max_iterations", 100))
    if not isinstance(items, list):
        items = [items]

    items = items[:max_iterations]

    ctx.data["_loop_items"] = items
    ctx.data["_loop_index"] = 0
    ctx.data["_loop_current"] = items[0] if items else None
    ctx.log(f"loop: {len(items)} itens")
    return {"outputs": {"items": items, "count": len(items)}}


async def _run_aggregate(ctx, node):
    cfg = node.get("data", {})
    mode = cfg.get("mode", "concat")
    source = cfg.get("source", "_loop_results")
    items = _resolve_path(ctx.data, source.lstrip("data.")) or []

    if mode == "concat":
        result = "".join(str(i) for i in items)
    elif mode == "join":
        separator = cfg.get("separator", ", ")
        result = separator.join(str(i) for i in items)
    elif mode == "count":
        result = len(items)
    elif mode == "sum":
        try:
            result = sum(float(i) for i in items)
        except (TypeError, ValueError):
            result = 0
    else:
        result = items

    ctx.data["aggregate_result"] = result
    ctx.log(f"aggregate ({mode}): {result}")
    return {"outputs": {"result": result}}


async def _run_execute_workflow(ctx, node):
    cfg = node.get("data", {})
    workflow_id = cfg.get("workflow_id")
    if not workflow_id:
        raise NodeError("workflow_id e obrigatorio", node.get("id", ""))

    workflow_id = int(workflow_id)
    from app.models.workflow import Workflow
    from app.services.workflow_engine import execute_workflow

    wf = ctx.db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise NodeError(f"Workflow {workflow_id} nao encontrado", node.get("id", ""))

    ctx.log(f"executando sub-workflow {workflow_id}: {wf.name}")

    payload = {
        "message": ctx.data.get("message", {}),
        "customer": ctx.data.get("customer", {}),
        "parent_context": {k: v for k, v in ctx.data.items() if not k.startswith("_")},
    }

    result = await execute_workflow(
        ctx.db, workflow_id, ctx.company_id, payload,
    )

    if isinstance(result, dict):
        for key, value in result.items():
            ctx.data[f"sub_{key}"] = value

    ctx.log(f"sub-workflow {workflow_id} finalizado: {result.get('status', 'unknown')}")
    return {"outputs": {"status": result.get("status", "unknown"), "result": result}}


async def _run_schedule(ctx, node):
    cfg = node.get("data", {})
    ctx.log("schedule trigger ativado")
    return {"outputs": {"triggered": True}}


# ---------------------------------------------------------------
# Definicoes dos tipos (metadata para o editor + run)
# ---------------------------------------------------------------

async def _run_trigger_message(ctx, node):
    ctx.log("Trigger: mensagem recebida")
    ctx.data.setdefault("message", ctx.data.get("_trigger_message", {}))
    return {"outputs": {"triggered": True}}


async def _run_trigger_webhook(ctx, node):
    ctx.log("Trigger: webhook chamado")
    return {"outputs": {"triggered": True}}


async def _run_wait_until_message(ctx, node):
    """Pausa o fluxo ate que o cliente envie a proxima mensagem."""
    ctx.log("Aguardando proxima mensagem do cliente...")
    return {"outputs": {"waiting": True}, "wait_for_message": True}


def _make_node(label, category, description, fields, run, extra_fields=None):
    all_fields = [
        {"key": "on_error", "label": "Em caso de erro", "type": "select",
         "options": ["stop", "continue", "fallback_edge"],
         "default": "stop",
         "help": "stop: encerra com erro | continue: ignora e segue | fallback_edge: segue edge de erro"},
    ]
    if extra_fields:
        all_fields.extend(extra_fields)
    return {
        "label": label,
        "category": category,
        "description": description,
        "fields": all_fields,
        "run": run,
    }


NODE_TYPES: dict[str, dict] = {
    "trigger_message": {
        "type": "trigger_message",
        **_make_node("Mensagem (Trigger)", "trigger", "Inicia o fluxo quando chega uma mensagem no WhatsApp.", [], _run_trigger_message),
    },
    "trigger_webhook": {
        "type": "trigger_webhook",
        **_make_node("Webhook (Trigger)", "trigger", "Inicia o fluxo quando o webhook e chamado.", [], _run_trigger_webhook),
    },
    "schedule": {
        "type": "schedule",
        **_make_node("Agendamento (Cron)", "trigger", "Inicia o fluxo em horario agendado.", [], _run_schedule,
            [{"key": "cron", "label": "Cron Expression", "type": "text",
              "placeholder": "Ex: 0 9 * * * (todo dia as 9h)"}]),
    },
    "wait_until_message": {
        "type": "wait_until_message",
        **_make_node("Aguardar mensagem", "whatsapp", "Pausa o fluxo ate o cliente enviar a proxima mensagem.", [], _run_wait_until_message),
    },
    "ai": {
        "type": "ai",
        **_make_node("IA (Gerar resposta)", "ai", "Chama o LLM da empresa para gerar uma resposta.", [], _run_ai,
            [{"key": "prompt", "label": "Prompt", "type": "textarea",
              "placeholder": "Ex: Responda a mensagem {{ data.message.text }} de forma educada"},
             {"key": "history", "label": "Usar memoria da conversa", "type": "toggle", "default": True},
             {"key": "system_prompt", "label": "System prompt (opcional)", "type": "textarea",
              "placeholder": "Deixe vazio para usar o da empresa."}]),
    },
    "ai_rag": {
        "type": "ai_rag",
        **_make_node("IA RAG (Base de Conhecimento)", "ai", "Busca contexto na base de conhecimento e gera resposta com IA.", [], run_rag_node,
            [{"key": "prompt", "label": "Pergunta / Prompt", "type": "textarea",
              "placeholder": "Ex: {{ data.message.text }}"},
             {"key": "top_k", "label": "No. de contextos relevantes", "type": "number", "default": 5},
             {"key": "system_prompt", "label": "System prompt (opcional)", "type": "textarea"}]),
    },
    "set": {
        "type": "set",
        **_make_node("Definir variavel", "data", "Guarda um valor em uma variavel do fluxo.", [], _run_set,
            [{"key": "variable", "label": "Nome da variavel", "type": "text"},
             {"key": "value", "label": "Valor", "type": "text",
              "placeholder": "Valor literal ou {{ data.campo }}"}]),
    },
    "code": {
        "type": "code",
        **_make_node("Codigo (Python)", "data", "Executa codigo Python customizado nos dados do fluxo.", [], _run_code,
            [{"key": "code", "label": "Codigo Python", "type": "textarea",
              "placeholder": "# data esta disponivel\nresult = len(data.get('message', {}).get('text', ''))"},
             {"key": "result_variable", "label": "Variavel de resultado", "type": "text", "default": "code_result"}]),
    },
    "condition": {
        "type": "condition",
        **_make_node("Condicao", "logic", "Desvia o fluxo conforme uma condicao (saidas true/false).", [], _run_condition,
            [{"key": "value", "label": "Variavel", "type": "text",
              "placeholder": "data.mensagem.texto"},
             {"key": "operator", "label": "Operador", "type": "select",
              "options": ["==", "!=", "contains", "not_contains", ">", "<", ">=", "<=", "is_true", "is_empty", "is_not_empty"]},
             {"key": "reference", "label": "Comparar com", "type": "text"}]),
    },
    "loop": {
        "type": "loop",
        **_make_node("Loop (Iterar)", "logic", "Itera sobre uma lista de itens.", [], _run_loop,
            [{"key": "items", "label": "Caminho da lista", "type": "text",
              "placeholder": "data.items ou variavel"},
             {"key": "max_iterations", "label": "Maximo de iteracoes", "type": "number", "default": 100}]),
    },
    "aggregate": {
        "type": "aggregate",
        **_make_node("Agregar dados", "data", "Junta itens em um so resultado.", [], _run_aggregate,
            [{"key": "mode", "label": "Modo", "type": "select",
              "options": ["concat", "join", "count", "sum"]},
             {"key": "source", "label": "Fonte dos dados", "type": "text", "default": "_loop_results"},
             {"key": "separator", "label": "Separador (join)", "type": "text", "default": ", "}]),
    },
    "delay": {
        "type": "delay",
        **_make_node("Aguardar (Delay)", "logic", "Pausa o fluxo por alguns segundos.", [], _run_delay,
            [{"key": "seconds", "label": "Segundos", "type": "number", "default": 1}]),
    },
    "http": {
        "type": "http",
        **_make_node("HTTP Request", "integration", "Faz uma requisicao HTTP (API externa).", [], _run_http,
            [{"key": "method", "label": "Metodo", "type": "select", "options": ["GET", "POST", "PUT", "PATCH", "DELETE"]},
             {"key": "url", "label": "URL", "type": "text"},
             {"key": "headers", "label": "Headers (JSON)", "type": "textarea",
              "placeholder": "{\"Authorization\": \"Bearer token\"}"},
             {"key": "query", "label": "Query Params (JSON)", "type": "textarea",
              "placeholder": "{\"page\": \"1\"}"},
             {"key": "body", "label": "Body (JSON)", "type": "textarea"}]),
    },
    "whatsapp_send": {
        "type": "whatsapp_send",
        **_make_node("Enviar WhatsApp", "whatsapp", "Envia uma mensagem de texto pelo WhatsApp.", [], _run_whatsapp_send,
            [{"key": "phone", "label": "Telefone", "type": "text",
              "placeholder": "{{ data.customer }}"},
             {"key": "text", "label": "Texto", "type": "textarea"}]),
    },
    "filter": {
        "type": "filter",
        **_make_node("Filtro", "logic", "Decide se o fluxo continua (saida true/false).", [], _run_filter),
    },
    "log": {
        "type": "log",
        **_make_node("Registrar (Log)", "data", "Escreve uma mensagem no log da execucao.", [], _run_log,
            [{"key": "message", "label": "Mensagem", "type": "textarea"}]),
    },
    "execute_workflow": {
        "type": "execute_workflow",
        **_make_node("Executar Workflow", "core", "Chama outro workflow (sub-workflow reutilizavel).", [], _run_execute_workflow,
            [{"key": "workflow_id", "label": "ID do Workflow", "type": "number"}]),
    },
}


def get_node_type(node_type: str) -> dict | None:
    return NODE_TYPES.get(node_type)


def list_node_types() -> list[dict]:
    """Retorna os tipos de no (metadata) para o editor montar a paleta."""
    out = []
    for nt in NODE_TYPES.values():
        out.append(
            {
                "type": nt["type"],
                "label": nt["label"],
                "category": nt["category"],
                "description": nt["description"],
                "fields": nt["fields"],
            }
        )
    return out


async def run_node(ctx, node: dict) -> dict:
    """Executa um no. node: {"id":..., "type":..., "data":{...}}"""
    node_type = node.get("type", "")
    spec = NODE_TYPES.get(node_type)
    if not spec:
        raise NodeError(f"Tipo de no desconhecido: {node_type}", node.get("id", ""))
    try:
        result = await spec["run"](ctx, node)
    except NodeError:
        raise
    except Exception as exc:
        raise NodeError(f"Erro no no '{node_type}': {exc}", node.get("id", ""))
    if result is None:
        result = {"outputs": {}}
    return result
