import asyncio
import json

from fastapi import BackgroundTasks
from starlette.requests import Request

from app.models.execution import Execution
from app.models.workflow import Workflow
from app.routers import webhook_router
from app.services import evolution
from app.services.conversation_service import handle_incoming_workflow


def test_incoming_message_executes_active_workflow_and_sends_response(db_session, config, company, monkeypatch):
    workflow = Workflow(
        company_id=company.id,
        name="Smoke WhatsApp",
        active=True,
        trigger_type="message",
        data={
            "nodes": [
                {"id": "trigger", "type": "trigger_message", "data": {}},
                {"id": "ai", "type": "ai", "data": {"prompt": "Responda {{ data.message.text }}", "history": "off"}},
                {"id": "send", "type": "whatsapp_send", "data": {"phone": "{{ data.phone }}", "text": "{{ data.ai_reply }}"}},
            ],
            "edges": [
                {"id": "trigger-ai", "source": "trigger", "target": "ai"},
                {"id": "ai-send", "source": "ai", "target": "send"},
            ],
        },
    )
    db_session.add(workflow)
    db_session.commit()

    sent = {}

    async def fake_send_text(**kwargs):
        sent.update(kwargs)
        return {"key": {"id": "evolution-message-id"}}

    monkeypatch.setattr(evolution, "send_text", fake_send_text)

    result = asyncio.run(
        handle_incoming_workflow(
            db_session,
            company_id=company.id,
            phone="5511999999999",
            text="preciso de ajuda",
            wa_message_id="smoke-1",
        )
    )

    execution = db_session.query(Execution).filter(Execution.id == result["execution_id"]).one()
    assert result["status"] == "success"
    assert execution.status == "success"
    assert sent["to_phone"] == "5511999999999"
    assert sent["instance"] == "default"
    assert "[mock] Responda preciso de ajuda" in sent["text"]


def test_authenticated_webhook_schedules_extracted_message(monkeypatch):
    scheduled = {}

    def fake_pipeline(company_id, phone, text, wa_message_id):
        scheduled.update(
            company_id=company_id,
            phone=phone,
            text=text,
            wa_message_id=wa_message_id,
        )

    monkeypatch.setattr(webhook_router, "get_secret", lambda name: "webhook-secret")
    monkeypatch.setattr(webhook_router, "_run_pipeline", fake_pipeline)

    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"remoteJid": "5511999999999@s.whatsapp.net", "id": "smoke-2", "fromMe": False},
            "message": {"conversation": "ola"},
        },
    }
    body = json.dumps(payload).encode()
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/webhook/whatsapp/7",
        "headers": [(b"evolution-auth", b"webhook-secret"), (b"content-type", b"application/json")],
    }

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    tasks = BackgroundTasks()
    response = asyncio.run(webhook_router.whatsapp_webhook(7, Request(scope, receive), tasks))
    asyncio.run(tasks())

    assert response == {"status": "accepted"}
    assert scheduled == {
        "company_id": 7,
        "phone": "5511999999999",
        "text": "ola",
        "wa_message_id": "smoke-2",
    }
