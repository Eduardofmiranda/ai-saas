import pytest

from app.services import evolution
from app.services.evolution import EvolutionError, _normalize_phone, send_text


class FakeResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {"ok": True}


@pytest.mark.asyncio
async def fake_post(self, url, json=None, headers=None):
    evolution._captured = {"url": url, "headers": headers or {}, "payload": json}
    return FakeResponse()


@pytest.mark.asyncio
async def test_send_text_uses_apikey_header():
    """O envio deve usar o header 'apikey' (Evolution API), nao Authorization Bearer."""
    original = evolution.httpx.AsyncClient.post
    evolution.httpx.AsyncClient.post = fake_post
    try:
        result = await send_text(
            to_phone="5511999999999",
            text="oi",
            base_url="http://evo:8080",
            api_key="meu-secret-key-123",
            instance="flowai",
        )
    finally:
        evolution.httpx.AsyncClient.post = original

    captured = evolution._captured
    assert captured["url"] == "http://evo:8080/message/sendText/flowai"
    assert captured["headers"].get("apikey") == "meu-secret-key-123"
    assert captured["headers"].get("Authorization") is None
    assert captured["payload"] == {"number": "5511999999999", "text": "oi"}
    assert result == {"ok": True}


@pytest.mark.asyncio
async def test_send_text_error_when_unreachable():
    with pytest.raises(EvolutionError):
        await send_text(
            to_phone="5511999999999",
            text="oi",
            base_url="http://127.0.0.1:1",  # porta que ninguem escuta
            api_key="x",
            instance="default",
        )


def test_normalize_phone():
    assert _normalize_phone("+55 (11) 99999-9999") == "5511999999999"
    assert _normalize_phone("5511999999999") == "5511999999999"
    assert _normalize_phone("11999999999") == "11999999999"