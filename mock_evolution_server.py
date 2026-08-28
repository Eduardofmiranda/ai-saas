"""Servidor MOCK da Evolution API para testes ponta a ponta.

Simula a Evolution API localmente, permitindo testar todo o fluxo do backend
SEM precisar de um numero real de WhatsApp nem da Evolution API.

Como usar:
1. Suba o backend apontando a Evolution para este mock:
     set EVOLUTION_BASE_URL=http://localhost:8090
     set EVOLUTION_API_KEY=mock
     set EVOLUTION_INSTANCE=flowai
     uvicorn app.main:app --reload --port 8000
2. Suba este mock:
     python mock_evolution_server.py
3. Simule o cliente enviando uma mensagem:
     curl -X POST http://localhost:8090/simulate_message \
       -H "Content-Type: application/json" \
       -d '{"company_id": 1, "phone": "5511999999999", "text": "ola" }'
4. O mock chamara o webhook do backend e capturara a resposta enviada
   (visivel em /sent_messages ou no console).
"""
from __future__ import annotations

import json
import os
import threading
import time

import httpx
import uvicorn
from fastapi import FastAPI, Request
from pydantic import BaseModel

app = FastAPI(title="Mock Evolution API")

# URL do webhook do backend que deve receber as mensagens do cliente
# no docker compose: http://backend:8000
BACKEND_WEBHOOK_BASE = os.getenv("MOCK_BACKEND_URL", "http://localhost:8000")

# Lista em memoria das mensagens "enviadas" pelo backend (visaveis para inspecao)
SENT: list[dict] = []
# Lista dos webhooks que o mock "recebeu" da Evolution e encaminhou ao backend
RECEIVED: list[dict] = []


class SimulateMessage(BaseModel):
    company_id: int
    phone: str
    text: str


def _build_evolution_payload(phone: str, text: str) -> dict:
    """Monta o payload no formato que o backend espera (extract_webhook_message)."""
    return {
        "event": "messages.upsert",
        "data": {
            "key": {
                "remoteJid": f"{phone}@s.whatsapp.net",
                "id": f"wamid_mock_{int(time.time() * 1000)}",
                "fromMe": False,
            },
            "message": {"conversation": text},
            "pushName": "Cliente MOCK",
        },
    }


@app.get("/sent_messages")
def sent_messages():
    """Lista as mensagens que o backend tentou enviar via Evolution."""
    return {"count": len(SENT), "messages": SENT}


@app.get("/received_webhooks")
def received_webhooks():
    """Lista os webhooks que foram encaminhados ao backend."""
    return {"count": len(RECEIVED), "webhooks": RECEIVED}


@app.post("/simulate_message")
async def simulate_message(body: SimulateMessage):
    """Simula um cliente enviando mensagem: dispara o webhook do backend."""
    payload = _build_evolution_payload(body.phone, body.text)
    RECEIVED.append({"phone": body.phone, "text": body.text, "payload": payload})

    url = f"{BACKEND_WEBHOOK_BASE}/webhook/whatsapp/{body.company_id}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, json=payload)
            return {
                "simulated": True,
                "backend_status": resp.status_code,
                "backend_response": resp.text,
                "forwarded_to": url,
            }
    except httpx.HTTPError as exc:
        return {
            "simulated": True,
            "error": f"Falha ao chamar backend em {url}: {exc}",
            "dica": f"Verifique se o backend esta no ar e apontado para o mock "
                    f"(BACKEND_WEBHOOK_BASE={BACKEND_WEBHOOK_BASE}).",
        }


@app.post("/message/sendText/{instance}")
async def send_text(instance: str, request: Request):
    """Endpoint que o backend chama para ENVIAR mensagem. Aqui apenas capturamos."""
    body = await request.json()
    SENT.append(
        {
            "instance": instance,
            "number": body.get("number"),
            "text": body.get("text"),
            "received_at": time.time(),
        }
    )
    return {
        "key": {"remoteJid": f"{body.get('number')}@s.whatsapp.net", "id": "wamid_mock_out"},
        "status": "PENDING",
        "instance": instance,
    }


@app.post("/chat/sendText/{instance}")
async def chat_send_text(instance: str, request: Request):
    """Variante alternativa de envio usada por alguns clientes."""
    return await send_text(instance, request)


@app.get("/")
def root():
    return {"status": "mock evolution", "envio": "/message/sendText/{instance}", "simulate": "/simulate_message"}


if __name__ == "__main__":
    port = int(os.getenv("MOCK_EVOLUTION_PORT", "8090"))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
