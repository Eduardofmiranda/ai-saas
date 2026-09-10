import asyncio
import time
import logging
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import func

from app.database.database import SessionLocal
from app.models.campaign import Campaign, CampaignLog
from app.routers.config_router import _evo_config
from app.services.config_service import get_or_create_config
from app.services import evolution

logger = logging.getLogger(__name__)

SEND_DELAY_SECONDS = 2
BATCH_SIZE = 5
EVOLUTION_TIMEOUT_SECONDS = 15.0
RECOVERY_LIMIT = 100
GENERIC_DELIVERY_ERROR = "Nao foi possivel enviar esta mensagem"
GENERIC_CONFIGURATION_ERROR = "Configuracao de envio indisponivel"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _campaign_counts(db, campaign_id: int) -> tuple[int, int, int]:
    """Retorna pendentes, enviados e erros sem confiar em contadores antigos."""
    rows = (
        db.query(CampaignLog.status, func.count(CampaignLog.id))
        .filter(CampaignLog.campaign_id == campaign_id)
        .group_by(CampaignLog.status)
        .all()
    )
    counts = {status: count for status, count in rows}
    return counts.get("pending", 0), counts.get("sent", 0), counts.get("error", 0)


def _finish_if_terminal(db, campaign_id: int) -> bool:
    """Fecha a campanha apenas quando nao ha destinatarios pendentes."""
    pending, sent, errors = _campaign_counts(db, campaign_id)
    if pending:
        return False
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if not campaign or campaign.status not in ("pending", "sending"):
        return False
    campaign.sent_count = sent
    campaign.error_count = errors
    campaign.status = "completed"
    campaign.finished_at = _utcnow()
    db.commit()
    return True


def _fail_campaign(db, campaign_id: int, error: str) -> None:
    """Falha terminal sem expor detalhes de infraestrutura ou credenciais."""
    db.query(CampaignLog).filter(
        CampaignLog.campaign_id == campaign_id,
        CampaignLog.status == "pending",
    ).update({CampaignLog.status: "error", CampaignLog.error: error}, synchronize_session=False)
    campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
    if campaign:
        _, sent, errors = _campaign_counts(db, campaign_id)
        campaign.status = "error"
        campaign.sent_count = sent
        campaign.error_count = errors
        campaign.finished_at = _utcnow()
    db.commit()


@shared_task(bind=True, max_retries=2, acks_late=True, reject_on_worker_lost=True)
def send_campaign(self, campaign_id: int):
    """Envia no maximo um lote e agenda a continuacao, se necessaria."""
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign or campaign.status not in ("pending", "sending"):
            return {"status": "ignored"}

        if campaign.status == "pending":
            campaign.status = "sending"
            campaign.started_at = campaign.started_at or _utcnow()
            db.commit()

        config = get_or_create_config(db, campaign.company_id)
        base_url, api_key, instance = _evo_config(config)
        if not base_url or not api_key or not instance:
            _fail_campaign(db, campaign_id, GENERIC_CONFIGURATION_ERROR)
            return {"status": "error", "reason": "configuration"}

        # O lock e mantido ate os status sent/error serem persistidos. Em
        # PostgreSQL, SKIP LOCKED permite que tarefas duplicadas trabalhem em
        # lotes diferentes; no SQLite de testes o with_for_update e inofensivo.
        logs = (
            db.query(CampaignLog)
            .filter(CampaignLog.campaign_id == campaign_id, CampaignLog.status == "pending")
            .order_by(CampaignLog.id)
            .with_for_update(skip_locked=True)
            .limit(BATCH_SIZE)
            .all()
        )
        if not logs:
            db.rollback()
            _finish_if_terminal(db, campaign_id)
            return {"status": "idle"}

        for index, log in enumerate(logs):
            if index:
                time.sleep(SEND_DELAY_SECONDS)
            try:
                asyncio.run(
                    evolution.send_text(
                        to_phone=log.phone,
                        text=campaign.message,
                        base_url=base_url,
                        api_key=api_key,
                        instance=instance,
                        timeout=EVOLUTION_TIMEOUT_SECONDS,
                    )
                )
                log.status = "sent"
                log.error = ""
                log.sent_at = _utcnow()
            except Exception:
                # A resposta da Evolution pode conter JIDs, URLs ou outros
                # dados operacionais. O usuario recebe somente um erro neutro.
                logger.warning("Falha no envio de campanha", extra={"campaign_id": campaign_id, "log_id": log.id})
                log.status = "error"
                log.error = GENERIC_DELIVERY_ERROR

        db.commit()
        pending, _, _ = _campaign_counts(db, campaign_id)
        if pending:
            send_campaign.apply_async(args=(campaign_id,), countdown=SEND_DELAY_SECONDS)
            return {"status": "scheduled", "processed": len(logs)}

        _finish_if_terminal(db, campaign_id)
        return {"status": "completed", "processed": len(logs)}
    except Exception:
        db.rollback()
        logger.exception("Falha interna ao processar lote de campanha", extra={"campaign_id": campaign_id})
        if self.request.retries < self.max_retries:
            raise self.retry(exc=RuntimeError("campaign batch failed"), countdown=30)
        _fail_campaign(db, campaign_id, GENERIC_DELIVERY_ERROR)
        return {"status": "error"}
    finally:
        db.close()


@shared_task
def recover_pending_campaigns() -> int:
    """Garante progresso apos reinicio do worker ou falha ao publicar job."""
    db = SessionLocal()
    try:
        campaign_ids = [
            row[0]
            for row in (
                db.query(Campaign.id)
                .filter(Campaign.status.in_(("pending", "sending")))
                .order_by(Campaign.id)
                .limit(RECOVERY_LIMIT)
                .all()
            )
        ]
        for campaign_id in campaign_ids:
            send_campaign.delay(campaign_id)
        return len(campaign_ids)
    finally:
        db.close()
