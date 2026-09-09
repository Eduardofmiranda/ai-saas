"""Endpoint de auditoria — lista registros de acoes criticas.

GET /audit-logs — retorna logs paginados com filtros (user_id, action, entity).
Somente gestores da empresa.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.services.audit import get_audit_logs
from app.services.deps import get_current_user, require_company_manager

router = APIRouter(prefix="/audit-logs", tags=["Audit Logs"])


@router.get("/")
def list_audit_logs(
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
    user_id: int | None = Query(None, description="Filtrar por usuario"),
    action: str | None = Query(None, description="Filtrar por acao (ex.: user.create)"),
    entity: str | None = Query(None, description="Filtrar por entidade (ex.: user)"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    """Lista registros de auditoria da empresa (somente gestores)."""
    return get_audit_logs(
        db,
        current_user.company_id,
        user_id=user_id,
        action=action,
        entity=entity,
        limit=limit,
        offset=offset,
    )
