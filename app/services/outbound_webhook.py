import hashlib
import hmac
import asyncio
import ipaddress
import json
import logging
import socket
import time
from urllib.parse import urlsplit, urlunsplit
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from app.models.outbound_webhook import OutboundWebhook, OutboundWebhookLog
from app.services.field_crypto import decrypt_field

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_DELAY_SECONDS = [5, 30, 120]
MAX_PAYLOAD_BYTES = 64 * 1024
ALLOWED_EVENTS = frozenset({"workflow.completed", "workflow.error"})


class WebhookSecurityError(ValueError):
    pass


def _is_public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_global and not (
        address.is_loopback or address.is_private or address.is_link_local
        or address.is_multicast or address.is_reserved or address.is_unspecified
    )


def validate_webhook_url(url: str) -> str:
    raw = (url or "").strip()
    if not raw or len(raw) > 2048:
        raise WebhookSecurityError("URL de webhook invalida")
    parsed = urlsplit(raw)
    if parsed.scheme.lower() != "https":
        raise WebhookSecurityError("O webhook deve usar HTTPS")
    if not parsed.hostname or parsed.username or parsed.password:
        raise WebhookSecurityError("URL de webhook invalida")
    try:
        port = parsed.port or 443
    except ValueError as exc:
        raise WebhookSecurityError("Porta de webhook invalida") from exc
    host = parsed.hostname.rstrip(".").lower()
    try:
        host = host.encode("idna").decode("ascii")
    except UnicodeError as exc:
        raise WebhookSecurityError("Host de webhook invalido") from exc
    try:
        addresses = {row[4][0] for row in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise WebhookSecurityError("Nao foi possivel resolver o host do webhook") from exc
    if not addresses or any(not _is_public_address(address) for address in addresses):
        raise WebhookSecurityError("Destino de webhook nao permitido")
    return urlunsplit(("https", parsed.netloc, parsed.path or "/", parsed.query, ""))


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
        if event not in ALLOWED_EVENTS or event not in wh.events.split(","):
            continue
        await _send_with_retry(db, wh, event, payload)


async def _send_with_retry(
    db: Session,
    webhook: OutboundWebhook,
    event: str,
    payload: dict,
) -> None:
    body = json.dumps(payload, default=str, ensure_ascii=False)
    if len(body.encode("utf-8")) > MAX_PAYLOAD_BYTES:
        _log_delivery(db, webhook, event, 0, False, "Payload excede o limite de entrega")
        return
    try:
        destination = validate_webhook_url(webhook.url)
    except WebhookSecurityError:
        _log_delivery(db, webhook, event, 0, False, "Destino bloqueado pela politica de seguranca")
        return
    headers = {
        "Content-Type": "application/json",
        "X-FlowAI-Event": event,
        "X-FlowAI-Delivery": str(int(time.time())),
    }
    secret = decrypt_field(webhook.secret) or ""
    if secret:
        sig = _sign_payload(body.encode(), secret)
        headers["X-FlowAI-Signature"] = f"sha256={sig}"

    last_error = ""
    last_status = 0

    for attempt in range(MAX_RETRIES):
        try:
            # Re-resolve immediately before each attempt. Redirects and proxy env
            # are disabled so policy cannot be bypassed through another target.
            destination = validate_webhook_url(destination)
            timeout = httpx.Timeout(15, connect=5)
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=False, trust_env=False) as client:
                resp = await client.post(destination, content=body, headers=headers)
                last_status = resp.status_code
                if 200 <= resp.status_code < 300:
                    _log_delivery(db, webhook, event, last_status, True)
                    return
                last_error = f"HTTP {resp.status_code}"
        except WebhookSecurityError:
            last_error = "Destino bloqueado pela politica de seguranca"
            break
        except httpx.HTTPError:
            last_error = "Falha de conexao ao destino"

        if attempt < MAX_RETRIES - 1:
            await asyncio.sleep(RETRY_DELAY_SECONDS[attempt])

    _log_delivery(db, webhook, event, last_status, False, last_error)


def _log_delivery(
    db: Session,
    webhook: OutboundWebhook,
    event: str,
    status_code: int,
    success: bool,
    error: str = "",
) -> None:
    log = OutboundWebhookLog(
        webhook_id=webhook.id,
        company_id=webhook.company_id,
        event=event,
        url=webhook.url,
        status_code=status_code,
        success=success,
        # Payloads and remote responses can contain PII/secrets. Keep outcome only.
        request_body="",
        response_body="",
        error=error[:500],
    )
    db.add(log)
    db.commit()
