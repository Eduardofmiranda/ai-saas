import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.campaign import Campaign, CampaignLog
from app.models.customer import Customer
from app.models.user import User
from app.services.deps import require_company_manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/campaigns",
    tags=["Campaigns"],
)

MAX_RECIPIENTS = 5_000
MAX_NAME_LENGTH = 120
MAX_MESSAGE_LENGTH = 4_000


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


def _campaign_or_404(db: Session, company_id: int, campaign_id: int) -> Campaign:
    campaign = (
        db.query(Campaign)
        .filter(Campaign.id == campaign_id, Campaign.company_id == company_id)
        .first()
    )
    if not campaign:
        raise HTTPException(status_code=404, detail="Campanha nao encontrada")
    return campaign


@router.get("/", response_model=list[CampaignResponse])
def list_campaigns(
    current_user: User = Depends(require_company_manager),
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
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    name = body.name.strip()
    message = body.message.strip()
    if not name or len(name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=400, detail="Nome da campanha invalido")
    if not message or len(message) > MAX_MESSAGE_LENGTH:
        raise HTTPException(status_code=400, detail="Mensagem da campanha invalida")
    if body.send_all and body.customer_ids:
        raise HTTPException(status_code=400, detail="Escolha todos os clientes ou uma lista de destinatarios")

    customers_query = db.query(Customer).filter(Customer.company_id == current_user.company_id)
    if body.send_all:
        customers = customers_query.order_by(Customer.id).limit(MAX_RECIPIENTS + 1).all()
        if len(customers) > MAX_RECIPIENTS:
            raise HTTPException(status_code=400, detail=f"Limite de {MAX_RECIPIENTS} destinatarios por campanha")
    else:
        customer_ids = list(dict.fromkeys(body.customer_ids))
        if not customer_ids:
            raise HTTPException(status_code=400, detail="Selecione destinatarios")
        if len(customer_ids) > MAX_RECIPIENTS or any(customer_id <= 0 for customer_id in customer_ids):
            raise HTTPException(status_code=400, detail=f"Limite de {MAX_RECIPIENTS} destinatarios por campanha")
        customers = customers_query.filter(Customer.id.in_(customer_ids)).all()
        if len(customers) != len(customer_ids):
            raise HTTPException(status_code=400, detail="Um ou mais destinatarios nao estao disponiveis")

    recipients: list[tuple[int, str]] = []
    seen_phones: set[str] = set()
    for customer in customers:
        phone = "".join(char for char in (customer.phone or "") if char.isdigit())
        if len(phone) < 10 or len(phone) > 15:
            raise HTTPException(status_code=400, detail="Todos os destinatarios devem ter telefone valido")
        if phone not in seen_phones:
            seen_phones.add(phone)
            recipients.append((customer.id, phone))

    if not recipients:
        raise HTTPException(status_code=400, detail="Nenhum destinatario valido foi encontrado")

    campaign = Campaign(
        company_id=current_user.company_id,
        name=name,
        message=message,
        total_recipients=len(recipients),
        created_by=current_user.id,
    )
    db.add(campaign)
    db.flush()
    db.add_all(
        [
            CampaignLog(campaign_id=campaign.id, customer_id=customer_id, phone=phone)
            for customer_id, phone in recipients
        ]
    )
    db.commit()
    db.refresh(campaign)
    return campaign


@router.post("/{campaign_id}/start")
def start_campaign(
    campaign_id: int,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    campaign = _campaign_or_404(db, current_user.company_id, campaign_id)
    if campaign.status not in ("draft", "error"):
        raise HTTPException(status_code=400, detail="Campanha nao pode ser iniciada")

    # Uma campanha que falhou por indisponibilidade de infraestrutura pode ser
    # reiniciada sem reenviar os destinatarios que ja tiveram entrega registrada.
    if campaign.status == "error":
        db.query(CampaignLog).filter(
            CampaignLog.campaign_id == campaign.id,
            CampaignLog.status == "error",
        ).update({CampaignLog.status: "pending", CampaignLog.error: ""}, synchronize_session=False)
        campaign.error_count = 0
        campaign.finished_at = None

    campaign.status = "pending"
    campaign.started_at = None
    db.commit()

    from app.tasks.campaign_tasks import send_campaign
    try:
        send_campaign.delay(campaign.id)
    except Exception:
        # A campanha fica reiniciavel; detalhes do broker nao saem pela API.
        logger.exception("Nao foi possivel enfileirar campanha", extra={"campaign_id": campaign.id})
        campaign.status = "error"
        db.commit()
        raise HTTPException(status_code=503, detail="Fila de envio indisponivel. Tente novamente.")

    return {"ok": True, "status": "pending"}


@router.delete("/{campaign_id}")
def delete_campaign(
    campaign_id: int,
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    campaign = _campaign_or_404(db, current_user.company_id, campaign_id)
    if campaign.status in ("pending", "sending"):
        raise HTTPException(status_code=400, detail="Nao e possivel excluir campanha em envio")
    db.delete(campaign)
    db.commit()
    return {"ok": True}


@router.get("/{campaign_id}/logs")
def list_campaign_logs(
    campaign_id: int,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(require_company_manager),
    db: Session = Depends(get_db),
):
    _campaign_or_404(db, current_user.company_id, campaign_id)
    return (
        db.query(CampaignLog)
        .filter(CampaignLog.campaign_id == campaign_id)
        .order_by(CampaignLog.id)
        .limit(limit)
        .all()
    )
