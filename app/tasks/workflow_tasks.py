import asyncio
import logging
from datetime import datetime, timedelta, timezone

from celery import shared_task
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.workflow import Workflow
from app.models.execution import Execution
from app.models.company_config import CompanyConfig
from app.services.workflow_engine import execute_workflow
from app.services.config_service import get_or_create_config
logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def run_workflow_task(self, workflow_id: int, payload: dict, company_id: int):
    """Executa um workflow de forma assincrona."""
    db: Session = SessionLocal()
    try:
        wf = (
            db.query(Workflow)
            .filter(Workflow.id == workflow_id, Workflow.company_id == company_id)
            .first()
        )
        if not wf:
            logger.warning("Workflow da tarefa nao encontrado", extra={"workflow_id": workflow_id, "company_id": company_id})
            return {"status": "error", "error": "Workflow not found"}

        config = get_or_create_config(db, company_id)
        execution = asyncio.run(execute_workflow(db, workflow=wf, payload=payload, config=config))
        logger.info("Workflow da tarefa concluido", extra={"workflow_id": workflow_id, "company_id": company_id, "status": execution.status})
        return {"status": execution.status, "execution_id": execution.id}
    except Exception as exc:
        logger.exception("Falha na tarefa de workflow", extra={"workflow_id": workflow_id, "company_id": company_id})
        raise self.retry(exc=exc)
    finally:
        db.close()

@shared_task
def cleanup_old_executions():
    """Remove execucoes antigas (mais de 30 dias) para economizar espaco."""
    db: Session = SessionLocal()
    try:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        deleted = db.query(Execution).filter(Execution.created_at < cutoff).delete()
        db.commit()
        logger.info(f"Cleaned up {deleted} old executions")
        return {"deleted": deleted}
    except Exception as exc:
        logger.exception(f"Cleanup failed: {exc}")
        db.rollback()
        return {"error": str(exc)}
    finally:
        db.close()