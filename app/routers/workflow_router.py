from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import Optional

from app.database.session import get_db
from app.models.execution import Execution
from app.models.department import Department
from app.models.user import User
from app.models.workflow import Workflow
from app.models.workflow_version import WorkflowVersion
from app.schemas.workflow_schema import (
    WorkflowCreate,
    WorkflowResponse,
    WorkflowUpdate,
)
from app.schemas.execution_schema import ExecutionResponse, TestRunRequest
from app.services.audit import log_action
from app.services.deps import get_current_user, require_company_manager
from app.services import access_rules
from app.services.nodes import registry
from app.services.workflow_validation import WorkflowValidationError, ensure_valid_workflow_graph
from app.services.workflow_engine import WorkflowEngineError, execute_workflow

router = APIRouter(prefix="/workflows", tags=["Workflows"])


def _get_owned_workflow(db: Session, workflow_id: int, user: User) -> Workflow:
    wf = (
        db.query(Workflow)
        .filter(
            Workflow.id == workflow_id,
            Workflow.company_id == user.company_id,
        )
        .first()
    )
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    if not access_rules.can_view_department(db, user, wf.department_id):
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


def _validate_department(db: Session, company_id: int, department_id: int | None) -> None:
    if department_id is None:
        return
    exists = db.query(Department.id).filter(
        Department.id == department_id,
        Department.company_id == company_id,
    ).first()
    if not exists:
        raise HTTPException(status_code=422, detail="Setor invalido para esta empresa")


@router.get("/node-types")
def list_node_types():
    """Tipos de no disponiveis para montar o fluxo no editor."""
    return {"node_types": registry.list_node_types()}


@router.get("/")
def list_workflows(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    q: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    query = db.query(Workflow).filter(Workflow.company_id == current_user.company_id)
    visible = access_rules.visible_department_condition(Workflow, db, current_user)
    if visible is not None:
        query = query.filter(visible)
    if q and q.strip():
        query = query.filter(Workflow.name.ilike(f"%{q.strip()}%"))
    total = query.count()
    items = query.order_by(Workflow.id.desc()).offset(offset).limit(limit).all()
    return {"total": total, "items": items}


@router.post("/", response_model=WorkflowResponse)
def create_workflow(
    data: WorkflowCreate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
    request: Request = None,
):
    _validate_department(db, current_user.company_id, data.department_id)
    wf = Workflow(
        company_id=current_user.company_id,
        user_id=current_user.id,
        name=data.name,
        description=data.description or "",
        data=data.data or {"nodes": [], "edges": []},
        trigger_type=data.trigger_type or "message",
        trigger_config=data.trigger_config or {},
        department_id=data.department_id,
    )
    db.add(wf)
    db.commit()
    db.refresh(wf)

    log_action(db, current_user.company_id, current_user.id, "workflow.create",
               entity="workflow", entity_id=wf.id, request=request)

    return wf


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _get_owned_workflow(db, workflow_id, current_user)


@router.patch("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(
    workflow_id: int,
    data: WorkflowUpdate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
    request: Request = None,
):
    wf = _get_owned_workflow(db, workflow_id, current_user)
    updates = data.model_dump(exclude_unset=True)
    if "department_id" in updates:
        _validate_department(db, current_user.company_id, updates["department_id"])

    if updates.get("active") is True:
        graph = updates.get("data", wf.data)
        trigger_type = updates.get("trigger_type", wf.trigger_type)
        try:
            ensure_valid_workflow_graph(graph, trigger_type=trigger_type)
        except WorkflowValidationError as exc:
            raise HTTPException(status_code=422, detail=str(exc))

    # Snapshot automatico: salva versao anterior antes de sobrescrever
    if "data" in updates and wf.data:
        last_version = (
            db.query(WorkflowVersion)
            .filter(WorkflowVersion.workflow_id == wf.id)
            .order_by(WorkflowVersion.version_number.desc())
            .first()
        )
        next_version = (last_version.version_number + 1) if last_version else 1
        snapshot = WorkflowVersion(
            workflow_id=wf.id,
            company_id=wf.company_id,
            version_number=next_version,
            name=wf.name,
            data=wf.data,
            trigger_type=wf.trigger_type,
            trigger_config=wf.trigger_config,
            created_by=current_user.id,
        )
        db.add(snapshot)

    # Uma mensagem recebida deve ter um unico fluxo principal. O motor executa
    # apenas um trigger "message" por empresa; manter varios ativos tornava o
    # resultado dependente da ordem do banco e confundia a operacao.
    will_activate_message = updates.get("active") is True and (
        updates.get("trigger_type", wf.trigger_type) == "message"
    )
    if will_activate_message:
        target_department_id = updates.get("department_id", wf.department_id)
        same_department = (
            Workflow.department_id.is_(None)
            if target_department_id is None
            else Workflow.department_id == target_department_id
        )
        (
            db.query(Workflow)
            .filter(
                Workflow.company_id == current_user.company_id,
                Workflow.id != wf.id,
                Workflow.trigger_type == "message",
                Workflow.active.is_(True),
                same_department,
            )
            .update({Workflow.active: False}, synchronize_session=False)
        )

    for field, value in updates.items():
        setattr(wf, field, value)
    db.commit()
    db.refresh(wf)

    log_action(db, current_user.company_id, current_user.id, "workflow.update",
               entity="workflow", entity_id=workflow_id, request=request)

    return wf


@router.delete("/{workflow_id}")
def delete_workflow(
    workflow_id: int,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
    request: Request = None,
):
    wf = _get_owned_workflow(db, workflow_id, current_user)
    # Remove execucoes vinculadas antes de apagar o fluxo (evita violacao de FK).
    from app.models.execution import Execution
    db.query(Execution).filter(Execution.workflow_id == wf.id).delete(synchronize_session=False)
    db.delete(wf)
    db.commit()

    log_action(db, current_user.company_id, current_user.id, "workflow.delete",
               entity="workflow", entity_id=workflow_id, request=request)

    return {"message": "Workflow deleted"}


@router.post("/{workflow_id}/duplicate", response_model=WorkflowResponse)
def duplicate_workflow(
    workflow_id: int,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    wf = _get_owned_workflow(db, workflow_id, current_user)
    new_wf = Workflow(
        company_id=current_user.company_id,
        user_id=current_user.id,
        name=f"{wf.name} (Copia)",
        description=wf.description or "",
        data=wf.data or {"nodes": [], "edges": []},
        trigger_type=wf.trigger_type or "message",
        trigger_config=wf.trigger_config or {},
        active=False,
        department_id=wf.department_id,
    )
    db.add(new_wf)
    db.commit()
    db.refresh(new_wf)
    return new_wf


@router.post("/{workflow_id}/run", response_model=ExecutionResponse)
async def run_workflow(
    workflow_id: int,
    body: TestRunRequest,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """Executa teste em modo seguro por padrao e retorna o resultado."""
    wf = _get_owned_workflow(db, workflow_id, current_user)
    from app.services.config_service import get_or_create_config
    config = get_or_create_config(db, current_user.company_id)

    try:
        execution = await execute_workflow(db, workflow=wf, payload=body.payload, config=config, dry_run=body.dry_run)
    except WorkflowEngineError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    log_action(db, current_user.company_id, current_user.id, "workflow.run",
               entity="workflow", entity_id=workflow_id, request=request)

    return execution


@router.get("/{workflow_id}/executions", response_model=list[ExecutionResponse])
def list_executions(
    workflow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wf = _get_owned_workflow(db, workflow_id, current_user)
    return (
        db.query(Execution)
        .filter(Execution.workflow_id == wf.id)
        .order_by(Execution.id.desc())
        .limit(50)
        .all()
    )


@router.get("/{workflow_id}/versions")
def list_versions(
    workflow_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_owned_workflow(db, workflow_id, current_user)
    return (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == workflow_id)
        .order_by(WorkflowVersion.version_number.desc())
        .limit(50)
        .all()
    )


@router.post("/{workflow_id}/versions/{version_id}/rollback")
def rollback_version(
    workflow_id: int,
    version_id: int,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
    request: Request = None,
):
    wf = _get_owned_workflow(db, workflow_id, current_user)
    version = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.id == version_id, WorkflowVersion.workflow_id == workflow_id)
        .first()
    )
    if not version:
        raise HTTPException(status_code=404, detail="Versao nao encontrada")

    # Snapshot da versao atual antes de restaurar
    last_version = (
        db.query(WorkflowVersion)
        .filter(WorkflowVersion.workflow_id == wf.id)
        .order_by(WorkflowVersion.version_number.desc())
        .first()
    )
    next_version = (last_version.version_number + 1) if last_version else 1
    snapshot = WorkflowVersion(
        workflow_id=wf.id,
        company_id=wf.company_id,
        version_number=next_version,
        name=wf.name,
        data=wf.data,
        trigger_type=wf.trigger_type,
        trigger_config=wf.trigger_config,
        note=f"Rollback para versao {version.version_number}",
        created_by=current_user.id,
    )
    db.add(snapshot)

    # Restaurar dados da versao selecionada
    wf.name = version.name
    wf.data = version.data
    wf.trigger_type = version.trigger_type
    wf.trigger_config = version.trigger_config
    db.commit()
    db.refresh(wf)

    log_action(db, current_user.company_id, current_user.id, "workflow.update",
               entity="workflow", entity_id=workflow_id, request=request)

    return wf

