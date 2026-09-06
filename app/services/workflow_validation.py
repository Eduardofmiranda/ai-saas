"""Validacao estrutural de grafos antes de executa-los em producao."""

from __future__ import annotations

from app.services.nodes.registry import NODE_TYPES, PARTIAL_NODE_TYPES


class WorkflowValidationError(ValueError):
    """O grafo salvo nao pode ser ativado ou executado."""


_TRIGGER_FOR_TYPE = {
    "message": "trigger_message",
    "webhook": "trigger_webhook",
    "cron": "schedule",
}
_TRIGGER_TYPES = frozenset(_TRIGGER_FOR_TYPE.values())
_REQUIRED_FIELDS = {
    "ai": ("prompt",),
    "ai_rag": ("prompt",),
    "set": ("variable",),
    "condition": ("value", "operator"),
    "whatsapp_send": ("phone", "text"),
    "log": ("message",),
    "execute_workflow": ("workflow_id",),
}


def validate_workflow_graph(graph: dict | None, *, trigger_type: str) -> list[str]:
    """Retorna erros estruturais do grafo sem alterar o rascunho salvo."""
    if not isinstance(graph, dict):
        return ["O grafo do workflow deve ser um objeto."]

    nodes = graph.get("nodes")
    edges = graph.get("edges")
    if not isinstance(nodes, list) or not isinstance(edges, list):
        return ["O grafo deve conter listas 'nodes' e 'edges'."]
    if not nodes:
        return ["Adicione um node de trigger antes de ativar o workflow."]

    errors: list[str] = []
    node_ids: set[str] = set()
    node_types: dict[str, str] = {}
    trigger_nodes: list[dict] = []

    for index, node in enumerate(nodes, start=1):
        if not isinstance(node, dict):
            errors.append(f"Node {index} invalido.")
            continue
        node_id = node.get("id")
        node_type = node.get("type")
        if not isinstance(node_id, str) or not node_id.strip():
            errors.append(f"Node {index} sem id valido.")
            continue
        if node_id in node_ids:
            errors.append(f"Id de node duplicado: '{node_id}'.")
            continue
        node_ids.add(node_id)
        if node_type not in NODE_TYPES:
            errors.append(f"Node '{node_id}' usa tipo desconhecido: '{node_type}'.")
            continue
        node_types[node_id] = node_type
        if node_type in PARTIAL_NODE_TYPES:
            errors.append(f"Node '{node_type}' ainda nao esta disponivel para ativacao.")
        if node_type in _TRIGGER_TYPES:
            trigger_nodes.append(node)
        data = node.get("data") or {}
        if not isinstance(data, dict):
            errors.append(f"Configuracao do node '{node_id}' deve ser um objeto.")
            continue
        for field in _REQUIRED_FIELDS.get(node_type, ()):
            value = data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                errors.append(f"Node '{node_id}' exige o campo '{field}'.")

    if trigger_type not in {*_TRIGGER_FOR_TYPE, "manual"}:
        errors.append(f"Tipo de trigger invalido: '{trigger_type}'.")
    if len(trigger_nodes) != 1:
        errors.append("O workflow deve ter exatamente um node de trigger.")
    elif trigger_type in _TRIGGER_FOR_TYPE:
        expected = _TRIGGER_FOR_TYPE[trigger_type]
        if trigger_nodes[0].get("type") != expected:
            errors.append(
                f"O trigger configurado ('{trigger_type}') nao corresponde ao node '{trigger_nodes[0].get('type')}'."
            )

    adjacency = {node_id: set() for node_id in node_ids}
    for index, edge in enumerate(edges, start=1):
        if not isinstance(edge, dict):
            errors.append(f"Conexao {index} invalida.")
            continue
        source = edge.get("source")
        target = edge.get("target")
        if source not in node_ids or target not in node_ids:
            errors.append(f"Conexao {index} aponta para um node inexistente.")
            continue
        if source == target:
            errors.append(f"Conexao {index} nao pode apontar um node para ele mesmo.")
            continue
        if target in {node.get("id") for node in trigger_nodes}:
            errors.append("Nenhuma conexao pode entrar no node de trigger.")
            continue
        adjacency[source].add(target)

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node_id: str) -> bool:
        if node_id in visiting:
            return True
        if node_id in visited:
            return False
        visiting.add(node_id)
        cyclic = any(visit(target) for target in adjacency[node_id])
        visiting.remove(node_id)
        visited.add(node_id)
        return cyclic

    if any(visit(node_id) for node_id in node_ids if node_id not in visited):
        errors.append("O workflow contem um ciclo; remova a conexao que retorna a um node anterior.")

    return errors


def ensure_valid_workflow_graph(graph: dict | None, *, trigger_type: str) -> None:
    errors = validate_workflow_graph(graph, trigger_type=trigger_type)
    if errors:
        raise WorkflowValidationError(" ".join(errors))