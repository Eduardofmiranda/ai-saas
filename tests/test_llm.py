import pytest

from app.services.llm import provider_status_error_message, extract_json, generate_structured_json


def test_rate_limit_message_guides_user_to_retry_or_check_config():
    message = provider_status_error_message(429)

    assert "Limite temporario" in message
    assert "Configuracao > IA" in message


def test_other_provider_status_keeps_http_code():
    assert provider_status_error_message(401) == "Provedor de IA retornou HTTP 401"


def test_extract_json_handles_markdown_fence():
    text = '```json\n{"name": "Joao", "email": "joao@x.com"}\n```'
    assert extract_json(text) == {"name": "Joao", "email": "joao@x.com"}


def test_extract_json_handles_text_around_json():
    text = 'Aqui esta o resultado: {"name": "Maria", "email": "maria@x.com"} Espero ter ajudado.'
    assert extract_json(text) == {"name": "Maria", "email": "maria@x.com"}


def test_extract_json_handles_single_quotes():
    text = "{'name': 'Ana', 'email': 'ana@x.com'}"
    assert extract_json(text) == {"name": "Ana", "email": "ana@x.com"}


def test_extract_json_returns_empty_on_invalid():
    assert extract_json("sem json aqui") == {}
    assert extract_json("") == {}


def test_extract_json_ignores_non_dict_json():
    assert extract_json("[1, 2, 3]") == {}


@pytest.mark.asyncio
async def test_generate_structured_json_mock_returns_fixed_schema():
    result = await generate_structured_json(
        system_prompt="extraia",
        history=[{"role": "user", "content": "ola"}],
        provider="mock",
    )
    assert result["email"] == "cliente@mock.com"
    assert set(result.keys()) >= {"name", "email", "phone", "company", "city", "notes"}
