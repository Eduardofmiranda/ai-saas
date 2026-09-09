import asyncio
import time
import logging

from app.tasks.celery_app import shared_task
from app.database.database import SessionLocal
from app.models.campaign import Campaign, CampaignLog
from app.models.customer import Customer
from app.services.config_service import get_or_create_config
from app.services import evolution

logger = logging.getLogger(__name__)

SEND_DELAY_SECONDS = 2


@shared_task(bind=True, max_retries=1)
def send_campaign(self, campaign_id: int):
    db = SessionLocal()
    try:
        campaign = db.query(Campaign).filter(Campaign.id == campaign_id).first()
        if not campaign or campaign.status not in ("pending", "sending"):
            return

        campaign.status = "sending"
        campaign.started_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()

        config = get_or_create_config(db, campaign.company_id)
        base_url = config.evolution_base_url if config else ""
        api_key = config.evolution_api_key if config else ""
        instance = config.evolution_instance if config else "default"

        logs = db.query(CampaignLog).filter(
            CampaignLog.campaign_id == campaign_id,
            CampaignLog.status == "pending",
        ).all()

        for log in logs:
            try:
                asyncio.run(evolution.send_text(
                    to_phone=log.phone,
                    text=campaign.message,
                    base_url=base_url,
                    api_key=api_key,
                    instance=instance,
                ))
                log.status = "sent"
                log.sent_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
                campaign.sent_count += 1
            except Exception as exc:
                log.status = "error"
                log.error = str(exc)[:500]
                campaign.error_count += 1

            db.commit()
            time.sleep(SEND_DELAY_SECONDS)

        campaign.status = "completed"
        campaign.finished_at = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
        db.commit()

    except Exception as exc:
        logger.exception("Erro na campanha %s", campaign_id)
        if campaign:
            campaign.status = "error"
            db.commit()
    finally:
        db.close()
