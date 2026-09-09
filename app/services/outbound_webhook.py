import hashlib
import hmac
import json
import logging
import time
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.outbound_webhook import OutboundWebhook, OutboundWebhookLog

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = [5, 30, 120]


def _sign_payload(payload: bytes, secret: str) -> str:
    return hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()


async def dispatch_webhook(
    db: Session,
    *,
    company_id: int,
    event: str,
    payload: dict,
) -> None:
    webhooks = (
        db.query(OutboundWebhook)
        .filter(
            OutboundWebhook.company_id == company_id,
            OutboundWebhook.active.is_(True),
        )
        .all()
    )

    for wh in webhooks:
        if event not in wh.events.split(","):
            continue
        await _send_with_retry(db, wh, event, payload)


async def _send_with_retry(
    db: Session,
    webhook: OutboundWebhook,
    event: str,
    payload: dict,
) -> None:
    body = json.dumps(payload, default=str, ensure_ascii=False)
    headers = {
        "Content-Type": "application/json",
        "X-FlowAI-Event": event,
        "X-FlowAI-Delivery": str(int(time.time())),
    }
    if webhook.secret:
        sig = _sign_payload(body.encode(), webhook.secret)
        headers["X-FlowAI-Signature"] = f"sha256={sig}"

    last_error = ""
    last_status = 0
    last_response = ""

    for attempt in range(MAX_RETRIES):
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(webhook.url, content=body, headers=headers)
                last_status = resp.status_code
                last_response = resp.text[:2000]
                if 200 <= resp.status_code < 300:
                    _log_delivery(db, webhook, event, body, last_status, True, last_response, "")
                    return
                last_error = f"HTTP {resp.status_code}"
        except Exception as exc:
            last_error = str(exc)[:500]

        if attempt < MAX_RETRIES - 1:
            time.sleep(RETRY_DELAY_SECONDS[attempt])

    _log_delivery(db, webhook, event, body, last_status, False, last_response, last_error)


def _log_delivery(
    db: Session,
    webhook: OutboundWebhook,
    event: str,
    request_body: str,
    status_code: int,
    success: bool,
    response_body: str,
    error: str,
) -> None:
    log = OutboundWebhookLog(
        webhook_id=webhook.id,
        company_id=webhook.company_id,
        event=event,
        url=webhook.url,
        status_code=status_code,
        success=success,
        request_body=request_body[:5000],
        response_body=response_body[:2000],
        error=error[:500],
    )
    db.add(log)
    db.commit()
