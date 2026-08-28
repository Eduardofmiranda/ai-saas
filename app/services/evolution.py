"""Cliente da Evolution API (WhatsApp).

Recebimento de mensagens chega via webhook (que nosso router aceita) e o envio
usamos o endpoint REST da Evolution.
"""
from __future__ import annotations

import httpx


class EvolutionError(Exception):
    pass


def _resolve(base_url: str | None, api_key: str | None, instance: str | None) -> tuple[str, str, str]:
    if not base_url:
        raise EvolutionError("Evolution API: base_url nao configurada")
    return base_url.rstrip("/"), (api_key or ""), (instance or "default")


async def send_text(
    *,
    to_phone: str,
    text: str,
    base_url: str | None,
    api_key: str | None,
    instance: str | None,
    timeout: float = 30.0,
) -> dict:
    """Envia mensagem de texto para um numero do WhatsApp."""
    base, key, inst = _resolve(base_url, api_key, instance)

    url = f"{base}/message/sendText/{inst}"

    # Evolution envia para o formato de numero do WhatsApp
    number = _normalize_phone(to_phone)

    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    payload = {"number": number, "text": text}

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()
    except httpx.HTTPStatusError as exc:
        raise EvolutionError(f"Evolution retornou erro {exc.response.status_code}: {exc.response.text}")
    except httpx.HTTPError as exc:
        raise EvolutionError(f"Erro ao chamar Evolution API: {exc}")


def _normalize_phone(phone: str) -> str:
    digits = "".join(ch for ch in phone if ch.isdigit())
    # Evolution espera o numero com codigo do pais (ex: +5511999999999)
    if digits.startswith("55") and len(digits) == 12:
        # adiciona o 9 do celular quando faltar (DDD + 8 digitos)
        pass
    return digits


def build_history(messages: list) -> list[dict]:
    """Converte mensagens do banco em historico para o LLM."""
    history = []
    for msg in messages:
        role = "assistant" if msg.sender_type == "bot" else "user"
        history.append({"role": role, "content": msg.content})
    return history


def extract_webhook_message(payload: dict) -> dict | None:
    """Extrai os dados uteis de um webhook da Evolution.

    Evolucao v2 envia: {"event":"messages.upsert","data":{"key":{...},"message":{...}}}
    Retorna None se nao for uma mensagem de texto de usuario.
    """
    try:
        data = payload.get("data") or {}
        event = payload.get("event")
        message = data.get("message") or {}
        key = data.get("key") or {}

        remote_jid = key.get("remoteJid") or ""
        # ignora mensagens provenientes do proprio numero (grupos recados etc)
        if not remote_jid or "@g.us" in remote_jid:
            return None

        conversation_text = message.get("conversation")
        if conversation_text is None and message.get("extendedTextMessage"):
            conversation_text = message["extendedTextMessage"].get("text")

        if not conversation_text:
            return None

        wa_id = key.get("id") or ""
        from_me = key.get("fromMe", False)
        if from_me:
            return None

        return {
            "wa_message_id": wa_id,
            "phone": remote_jid.split("@")[0],
            "text": conversation_text,
        }
    except Exception:
        return None
