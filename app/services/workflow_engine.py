"""Motor de execucao de workflows.

Entrada: JSON do grafo no formato do editor -> {"nodes":[{"id","type","data","position"}], "edges":[{"id","source","target","sourceHandle"}]}

Executa os nos a partir do trigger, seguindo as edges, propagando ctx.data
e registrando resultados/logs em uma Execucao.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.company_config import CompanyConfig
from app.models.execution import Execution
from app.models.pending_flow import PendingFlow
from app.models.workflow import Workflow
from app.services.nodes.context import NodeContext, NodeError
from app.services.nodes import registry
from datetime import datetime, timezone


def _utcnow():
    return datetime.now(timezone.utc)


class WorkflowEngineError(Exception):
    pass


class WaitForMessage(Exception):
    """Sinal interno: o fluxo deve pausar aguardando a proxima mensagem.

    `next_node_id` e o proximo no a executar quando a mensagem chegar.
    """

    def __init__(self, next_node_id: str):
        super().__init__(next_node_id)
        self.next_node_id = next_node_id


def _find_entry(nodes: list[dict]) -> dict | None:
    for n in nodes:
        if n.get("type", "").startswith("trigger_"):
            return n
    return None


def _find_triggered_entry(nodes: list[dict], trigger_type: str) -> dict | None:
    for n in nodes:
        if n.get("type") == trigger_type:
            return n
    return None


def build_outgoing_edges(edges: list[dict], node_id: str) -> list[dict]:
    return [e for e in edges if e.get("source") == node_id]


def _customer_phone(payload: dict) -> str:
    """Extrai o numero do cliente do payload para chavear o PendingFlow."""
    msg = payload.get("message") or {}
    phone = (
        msg.get("from")
        or msg.get("number")
        or msg.get("phone")
        or payload.get("customer")
        or payload.get("phone")
        or ""
    )
    return str(phone) if phone else ""


async def execute_workflow(
    db: Session,
    *,
    workflow: Workflow,
    payload: dict,
    config: CompanyConfig,
    resume_from: str | None = None,
) -> Execution:
    """Executa o workflow e retorna a Execution registrada.

    Se o fluxo encontrar um no `wait_until_message`, salva um PendingFlow
    e retorna a Execution com status "waiting" (nao finaliza).
    """
    graph = workflow.data or {}
    nodes: list[dict] = graph.get("nodes", [])
    edges: list[dict] = graph.get("edges", [])

    if not nodes:
        raise WorkflowEngineError("Workflow sem nos.")

    entry = _find_entry(nodes)
    if not entry:
        raise WorkflowEngineError("Workflow sem no de trigger.")

    # Cria a execucao
    execution = Execution(
        workflow_id=workflow.id,
        company_id=workflow.company_id,
        status="running",
        context={"trigger": payload},
        node_results={},
        started_at=_utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    ctx = NodeContext(
        db=db,
        company_id=workflow.company_id,
        execution_id=execution.id,
        workflow_id=workflow.id,
        data={"message": payload.get("message", {}), "customer": payload.get("customer"), **payload},
        config=config,
    )

    node_map = {n.get("id"): n for n in nodes}

    try:
        await _run_graph(ctx, entry, nodes, edges, node_map, start_at=resume_from)
        execution.status = "success"
        execution.finished_at = _utcnow()
    except WaitForMessage as wait:
        # Fluxo aguardando nova mensagem -> salva snapshot e marca como waiting
        execution.status = "waiting"
        _save_pending(
            db,
            company_id=workflow.company_id,
            workflow_id=workflow.id,
            execution_id=execution.id,
            phone=_customer_phone(payload),
            snapshot={"data": ctx.data, "next_node_id": wait.next_node_id},
        )
        ctx.log(f"Fluxo pausado; retomara em {wait.next_node_id}")
    except NodeError as exc:
        execution.status = "error"
        execution.error = f"{exc.node_id}: {exc.message}"
        ctx.log(f"ERRO: {exc.message}")
    except Exception as exc:
        execution.status = "error"
        execution.error = str(exc)
        ctx.log(f"ERRO: {exc}")

    execution.node_results = ctx.data
    execution.context = {"trigger": payload, "logs": ctx.logs}
    db.commit()
    db.refresh(execution)
    return execution


def _save_pending(
    db: Session,
    *,
    company_id: int,
    workflow_id: int,
    execution_id: int,
    phone: str,
    snapshot: dict,
) -> None:
    """Remove qualquer pendencia anterior da mesma conversa e salva a nova."""
    db.query(PendingFlow).filter(PendingFlow.company_id == company_id).filter(
        PendingFlow.phone == phone
    ).delete()
    pending = PendingFlow(
        company_id=company_id,
        workflow_id=workflow_id,
        execution_id=execution_id,
        phone=phone,
        snapshot=snapshot,
    )
    db.add(pending)
    db.commit()


async def resume_workflow(db: Session, *, pending: PendingFlow, payload: dict, config: CompanyConfig) -> Execution:
    """Retoma um fluxo pausado quando o cliente envia a proxima mensagem.

    Cria uma nova Execution (continuacao) que começa no no salvo, com o
    contexto restaurado e mesclado a nova mensagem.
    """
    workflow = db.query(Workflow).filter(Workflow.id == pending.workflow_id).first()
    if not workflow:
        raise WorkflowEngineError("Workflow do fluxo pausado nao encontrado.")

    snapshot = pending.snapshot or {}
    saved_data = snapshot.get("data", {})
    next_node_id = snapshot.get("next_node_id")

    # garante que a nova mensagem sobrepoe a antiga no contexto
    merged = dict(saved_data)
    merged["message"] = payload.get("message", saved_data.get("message", {}))
    merged["customer"] = payload.get("customer", saved_data.get("customer"))
    merged.update(payload)

    graph = workflow.data or {}
    nodes: list[dict] = graph.get("nodes", [])
    edges: list[dict] = graph.get("edges", [])
    node_map = {n.get("id"): n for n in nodes}

    if not next_node_id or next_node_id not in node_map:
        raise WorkflowEngineError("Ponto de retomada do fluxo invalido.")

    execution = Execution(
        workflow_id=workflow.id,
        company_id=workflow.company_id,
        status="running",
        context={"trigger": payload, "resumed": True},
        node_results={},
        started_at=_utcnow(),
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    ctx = NodeContext(
        db=db,
        company_id=workflow.company_id,
        execution_id=execution.id,
        workflow_id=workflow.id,
        data=merged,
        config=config,
    )

    try:
        await _run_graph(ctx, node_map[next_node_id], nodes, edges, node_map)
        execution.status = "success"
        execution.finished_at = _utcnow()
        # fluxo concluido: remove a pendencia
        db.delete(pending)
    except WaitForMessage as wait:
        execution.status = "waiting"
        db.delete(pending)
        _save_pending(
            db,
            company_id=workflow.company_id,
            workflow_id=workflow.id,
            execution_id=execution.id,
            phone=_customer_phone(payload),
            snapshot={"data": ctx.data, "next_node_id": wait.next_node_id},
        )
    except NodeError as exc:
        execution.status = "error"
        execution.error = f"{exc.node_id}: {exc.message}"
        ctx.log(f"ERRO: {exc.message}")
    except Exception as exc:
        execution.status = "error"
        execution.error = str(exc)
        ctx.log(f"ERRO: {exc}")

    execution.node_results = ctx.data
    execution.context = {"trigger": payload, "logs": ctx.logs}
    db.commit()
    db.refresh(execution)
    return execution


async def _run_graph(
    ctx: NodeContext,
    entry: dict,
    nodes: list[dict],
    edges: list[dict],
    node_map: dict,
    start_at: str | None = None,
) -> None:
    """Executa a partir do trigger (ou de um no especifico em retomada).

    Segue as edges em ordem. Para no de condicao, respeita a edge
    verdadeira/falsa. Se um no pedir `wait_for_message`, o fluxo para
    e o proximo no e sinalizado via WaitForMessage.

    Suporta error handling por no via campo `on_error`:
    - "continue": ignora erro e segue para proximo no
    - "stop": encerra o fluxo com erro
    - "fallback_edge": segue a edge de erro (sourceHandle="error")
    """
    visited = set()
    current = node_map.get(start_at) if start_at else entry
    if current is None:
        return

    while current is not None and current["id"] not in visited:
        visited.add(current["id"])
        on_error = current.get("data", {}).get("on_error", "stop")

        try:
            result = await registry.run_node(ctx, current)
        except NodeError as exc:
            ctx.log(f"ERRO no no '{current.get('type')}': {exc.message}")
            if on_error == "continue":
                result = {"outputs": {"error": exc.message}}
            elif on_error == "fallback_edge":
                outgoing = build_outgoing_edges(edges, current["id"])
                error_edge = None
                for e in outgoing:
                    handle = e.get("sourceHandle") or ""
                    if "error" in handle:
                        error_edge = e
                        break
                if error_edge:
                    nxt = node_map.get(error_edge.get("target"))
                    if nxt:
                        current = nxt
                        continue
                raise
            else:
                raise

        outputs = result.get("outputs", {})
        for k, v in outputs.items():
            ctx.data[k] = v

        if result.get("wait_for_message"):
            nxt = _next_node_after_wait(current, edges, node_map)
            if nxt is None:
                return
            raise WaitForMessage(nxt)

        if result.get("stop"):
            return
        if result.get("next"):
            nxt = node_map.get(result["next"])
            if nxt is None:
                return
            current = nxt
            continue

        outgoing = build_outgoing_edges(edges, current["id"])
        if not outgoing:
            return

        if current["type"] == "condition":
            cond = ctx.data.get("condition_result", False)
            chosen = None
            for e in outgoing:
                handle = e.get("sourceHandle") or ""
                if (cond and "true" in handle) or (not cond and "false" in handle):
                    chosen = node_map.get(e.get("target"))
                    break
            current = chosen
            continue

        for e in outgoing:
            target = node_map.get(e.get("target"))
            if target is None:
                continue
            if target["id"] not in visited:
                await _run_graph(ctx, target, nodes, edges, node_map)
        return


def _next_node_after_wait(current: dict, edges: list[dict], node_map: dict):
    """Determina o proximo no apos um no de espera (primeira edge valida)."""
    outgoing = build_outgoing_edges(edges, current["id"])
    for e in outgoing:
        target = node_map.get(e.get("target"))
        if target is not None:
            return target["id"]
    return None
