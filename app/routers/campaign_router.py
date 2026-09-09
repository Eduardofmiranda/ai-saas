from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.campaign import Campaign, CampaignLog
from app.models.customer import Customer
from app.models.user import User
from app.services.deps import get_current_user

router = APIRouter(
    prefix="/campaigns",
    tags=["Campaigns"],
)


class CampaignCreate(BaseModel):
    name: str
    message: str
    customer_ids: list[int] = []
    send_all: bool = False


class CampaignResponse(BaseModel):
    id: int
    company_id: int
    name: str
    message: str
    status: str
    total_recipients: int
    sent_count: int
    error_count: int
    scheduled_at: str | None
    started_at: str | None
    finished_at: str | None
    created_at: str

    class Config:
        from_attributes = True


@router.get("/", response_model=list[CampaignResponse])
def list_campaigns(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Campaign)
        .filter(Campaign.company_id == current_user.company_id)
        .order_by(Campaign.id.desc())
        .limit(50)
        .all()
    )


@router.post("/", response_model=CampaignResponse, status_code=201)
def create_campaign(
    body: CampaignCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.send_all:
        customers = (
            db.query(Customer)
            .filter(Customer.company_id == current_user.company_id)
            .all()
        )
    elif body.customer_ids:
        customers = (
            db.query(Customer)
            .filter(
                Customer.company_id == current_user.company_id,
                Customer.id.in_(body.customer_ids),
            )
            .all()
        )
    else:
        raise HTTPException(status_code=400, detail="Selecione destinatarios")

    campaign = Campaign(
        company_id=current_user.company_id,
        name=body.name,
        message=body.message,
        total_recipients=len(customers),
        created_by=current_user.id,
    )
    db.add(campaign)
    db.flush()

    for cust in customers:
        log = CampaignLog(
            campaign_id=campaign.id,
            customer_id=cust.id,
            phone=cust.phone,
        )
        db.add(log)

    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/start")
def start_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.company_id == current_user.company_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")
    if campaign.status not in ("draft", "error"):
        raise HTTPException(status_code=400, detail="Campanha nao pode ser iniciada")

    campaign.status = "pending"
    db.commit()

    from app.tasks.campaign_tasks import send_campaign
    send_campaign.delay(campaign.id)

    return {"ok": True, "status": "pending"}


@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.company_id == current_user.company_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")
    if campaign.status == "sending":
        raise HTTPException(status_code=400, detail="Nao e possivel excluir campanha em envio")
    db.delete(campaign)
    db.commit()
    return {"ok": True}


@router.get("/{campaign_id}/logs")
def list_campaign_logs(
    campaign_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.company_id == current_user.company_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")
    return (
        db.query(CampaignLog)
        .filter(CampaignLog.campaign_id == campaign_id)
        .order_by(CampaignLog.id)
        .all()
    )
