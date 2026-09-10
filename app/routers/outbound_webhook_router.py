from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.outbound_webhook import OutboundWebhook, OutboundWebhookLog
from app.models.user import User
from app.services.deps import require_company_manager
from app.services.field_crypto import encrypt_field
from app.services.outbound_webhook import ALLOWED_EVENTS, WebhookSecurityError, validate_webhook_url

router = APIRouter(
    prefix="/outbound-webhooks",
    tags=["Outbound Webhooks"],
)


class WebhookCreate(BaseModel):
    url: str = Field(max_length=2048)
    secret: str = Field(default="", max_length=1000)
    events: str = Field(default="workflow.completed,workflow.error", max_length=200)
    description: str = Field(default="", max_length=500)


class WebhookUpdate(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    secret: str | None = Field(default=None, max_length=1000)
    events: str | None = Field(default=None, max_length=200)
    active: bool | None = None
    description: str | None = Field(default=None, max_length=500)


def _normalized_events(events: str) -> str:
    values = [event.strip() for event in (events or "").split(",") if event.strip()]
    if not values or any(event not in ALLOWED_EVENTS for event in values):
        raise HTTPException(status_code=422, detail="Eventos de webhook invalidos")
    return ",".join(dict.fromkeys(values))


def _safe_url(url: str) -> str:
    try:
        return validate_webhook_url(url)
    except WebhookSecurityError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


class WebhookResponse(BaseModel):
    id: int
    company_id: int
    url: str
    events: str
    active: bool
    description: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class WebhookLogResponse(BaseModel):
    id: int
    webhook_id: int
    event: str
    url: str
    status_code: int
    success: bool
    error: str
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[WebhookResponse])
def list_webhooks(
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    return (
        db.query(OutboundWebhook)
        .filter(OutboundWebhook.company_id == current_user.company_id)
        .order_by(OutboundWebhook.id.desc())
        .all()
    )


@router.post("/", response_model=WebhookResponse, status_code=201)
def create_webhook(
    body: WebhookCreate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    if db.query(OutboundWebhook).filter(OutboundWebhook.company_id == current_user.company_id).count() >= 20:
        raise HTTPException(status_code=409, detail="Limite de 20 webhooks por empresa")
    wh = OutboundWebhook(
        company_id=current_user.company_id,
        url=_safe_url(body.url),
        secret=encrypt_field(body.secret.strip()) if body.secret.strip() else "",
        events=_normalized_events(body.events),
        description=body.description,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return wh


@router.patch("/{webhook_id}", response_model=WebhookResponse)
def update_webhook(
    webhook_id: int,
    body: WebhookUpdate,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    wh = (
        db.query(OutboundWebhook)
        .filter(OutboundWebhook.id == webhook_id, OutboundWebhook.company_id == current_user.company_id)
        .first()
    )
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook nao encontrado")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field == "url":
            value = _safe_url(value)
        elif field == "events":
            value = _normalized_events(value)
        elif field == "secret":
            value = encrypt_field((value or "").strip()) if (value or "").strip() else ""
        setattr(wh, field, value)
    db.commit()
    db.refresh(wh)
    return wh


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    wh = (
        db.query(OutboundWebhook)
        .filter(OutboundWebhook.id == webhook_id, OutboundWebhook.company_id == current_user.company_id)
        .first()
    )
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook nao encontrado")
    db.delete(wh)
    db.commit()
    return {"ok": True}


@router.get("/{webhook_id}/logs", response_model=list[WebhookLogResponse])
def list_webhook_logs(
    webhook_id: int,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    wh = (
        db.query(OutboundWebhook)
        .filter(OutboundWebhook.id == webhook_id, OutboundWebhook.company_id == current_user.company_id)
        .first()
    )
    if not wh:
        raise HTTPException(status_code=404, detail="Webhook nao encontrado")
    return (
        db.query(OutboundWebhookLog)
        .filter(OutboundWebhookLog.webhook_id == webhook_id)
        .order_by(OutboundWebhookLog.id.desc())
        .limit(50)
        .all()
    )
