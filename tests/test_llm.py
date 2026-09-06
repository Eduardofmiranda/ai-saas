from app.services.llm import provider_status_error_message


def test_rate_limit_message_guides_user_to_retry_or_check_config():
    message = provider_status_error_message(429)

    assert "Limite temporario" in message
    assert "Configuracao > IA" in message


def test_other_provider_status_keeps_http_code():
    assert provider_status_error_message(401) == "Provedor de IA retornou HTTP 401"
