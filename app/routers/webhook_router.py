import asyncio

from fastapi import APIRouter, BackgroundTasks, Request
from sqlalchemy.orm import Session

from app.database.session import SessionLocal
from app.services import evolution
from app.services.conversation_service import handle_incoming_workflow

router = APIRouter(prefix="/webhook", tags=["Webhooks"])


def _run_pipeline(company_id: int, phone: str, text: str, wa_message_id: str) -> None:
    db: Session = SessionLocal()
    try:
        asyncio.run(
            handle_incoming_workflow(
                db,
                company_id=company_id,
                phone=phone,
                text=text,
                wa_message_id=wa_message_id,
            )
        )
    finally:
        db.close()


@router.post("/whatsapp/{company_id}")
async def whatsapp_webhook(
    company_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
):
    """Ponto de entrada para o webhook da Evolution API.

    Configure o webhook da instancia da Evolution para apontar para
    POST /webhook/whatsapp/{company_id} (o id da empresa da plataforma).
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    extracted = evolution.extract_webhook_message(payload)
    if not extracted:
        return {"status": "ignored"}

    background_tasks.add_task(
        _run_pipeline,
        company_id,
        extracted["phone"],
        extracted["text"],
        extracted["wa_message_id"],
    )
    return {"status": "accepted"}
