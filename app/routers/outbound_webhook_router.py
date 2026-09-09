from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.outbound_webhook import OutboundWebhook, OutboundWebhookLog
from app.models.user import User
from app.services.deps import get_current_user

router = APIRouter(
    prefix="/outbound-webhooks",
    tags=["Outbound Webhooks"],
)


class WebhookCreate(BaseModel):
    url: str
    secret: str = ""
    events: str = "workflow.completed,workflow.error"
    description: str = ""


class WebhookUpdate(BaseModel):
    url: str | None = None
    secret: str | None = None
    events: str | None = None
    active: bool | None = None
    description: str | None = None


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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    wh = OutboundWebhook(
        company_id=current_user.company_id,
        url=body.url,
        secret=body.secret,
        events=body.events,
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
    current_user: User = Depends(get_current_user),
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
        setattr(wh, field, value)
    db.commit()
    db.refresh(wh)
    return wh


@router.delete("/{webhook_id}")
def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
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
