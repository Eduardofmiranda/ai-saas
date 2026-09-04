import asyncio
import hmac

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException
from sqlalchemy.orm import Session

from app.config import get_secret
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


def _verify_webhook_auth(request: Request) -> None:
    """Valida a autenticacao do webhook da Evolution API.

    A Evolution API envia a chave de autenticacao no header 'evolution-auth'.
    Se EVOLUTION_AUTH_KEY estiver configurado, valida o header.
    """
    auth_key = get_secret("EVOLUTION_AUTH_KEY")
    if not auth_key:
        return

    received = request.headers.get("evolution-auth", "")
    if not hmac.compare_digest(received, auth_key):
        raise HTTPException(status_code=401, detail="Webhook authentication failed")


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
    _verify_webhook_auth(request)

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
