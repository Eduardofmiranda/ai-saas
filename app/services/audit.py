"""Servico de auditoria — registro de acoes criticas.

Uso:
    from app.services.audit import log_action
    log_action(db, company_id, user_id, "user.create", entity="user",
               entity_id=new_user.id, details={"email": ..., "role": ...},
               request=request)
"""
import json
import logging
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog

logger = logging.getLogger(__name__)


def log_action(
    db: Session,
    company_id: int,
    user_id: int | None,
    action: str,
    *,
    entity: str | None = None,
    entity_id: int | None = None,
    details: dict[str, Any] | None = None,
    request: Any = None,
) -> None:
    """Registra uma acao de auditoria.

    Args:
        db: sessao do banco
        company_id: empresa do usuario
        user_id: usuario que realizou a acao (None para acoes anonimas como login)
        action: tipo da acao (ex.: "user.create", "config.update")
        entity: entidade afetada (ex.: "user", "workflow")
        entity_id: ID da entidade afetada
        details: dict com detalhes (campos alterados, valores, etc.)
        request: objeto Request do FastAPI (para IP/user-agent)
    """
    ip_address = None
    user_agent = None

    if request is not None:
        ip_address = _get_client_ip(request)
        user_agent = str(request.headers.get("user-agent", ""))[:500]

    details_str = ""
    if details:
        try:
            details_str = json.dumps(details, default=str, ensure_ascii=False)
        except Exception:
            details_str = str(details)

    log = AuditLog(
        company_id=company_id,
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details_str,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()

    logger.info(
        "Audit: %s user=%s entity=%s/%s",
        action, user_id, entity, entity_id,
        extra={"company_id": company_id, "audit_action": action},
    )


def _get_client_ip(request: Any) -> str | None:
    """Extrai o IP real do cliente, considerando proxies."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    if hasattr(request, "client") and request.client:
        return request.client.host
    return None


def get_audit_logs(
    db: Session,
    company_id: int,
    *,
    user_id: int | None = None,
    action: str | None = None,
    entity: str | None = None,
    limit: int = 100,
    offset: int = 0,
) -> dict:
    """Lista registros de auditoria com filtros."""
    q = db.query(AuditLog).filter(AuditLog.company_id == company_id)

    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    if entity:
        q = q.filter(AuditLog.entity == entity)

    total = q.count()
    logs = (
        q.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return {
        "total": total,
        "items": [_log_to_dict(log) for log in logs],
    }


def _log_to_dict(log: AuditLog) -> dict:
    return {
        "id": log.id,
        "company_id": log.company_id,
        "user_id": log.user_id,
        "action": log.action,
        "entity": log.entity,
        "entity_id": log.entity_id,
        "details": log.details,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }
