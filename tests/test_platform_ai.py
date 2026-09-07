from app.models.platform_ai_provider import PlatformAIProvider
from app.services.config_service import resolve_ai_config
from app.services.field_crypto import encrypt_field


def test_selected_provider_never_inherits_key_from_another_provider(db_session, config, monkeypatch):
    """Trocar DeepSeek por OpenAI sem chave não pode continuar usando a anterior."""
    values = {
        "DEFAULT_AI_PROVIDER": "deepseek",
        "DEFAULT_AI_MODEL": "deepseek-v4-flash",
        "DEFAULT_AI_API_KEY": "deepseek-key",
        "DEFAULT_AI_BASE_URL": "https://api.deepseek.com/v1",
    }
    monkeypatch.setattr("app.services.config_service.get_secret", lambda name: values.get(name, ""))
    config.ai_provider = "openai"
    config.ai_model = "gpt-4o-mini"
    config.ai_api_key = ""
    config.ai_base_url = ""

    resolved = resolve_ai_config(config, db_session)

    assert resolved["provider"] == "openai"
    assert resolved["api_key"] == ""
    assert resolved["credential_source"] == "missing"


def test_platform_credential_is_used_only_for_matching_provider(db_session, config):
    config.ai_provider = "openai"
    config.ai_api_key = ""
    config.ai_base_url = ""
    db_session.add(
        PlatformAIProvider(
            provider="openai",
            model="gpt-4o-mini",
            api_key=encrypt_field("platform-openai-key"),
            base_url="https://api.openai.com/v1",
            enabled=True,
        )
    )
    db_session.commit()

    resolved = resolve_ai_config(config, db_session)

    assert resolved["api_key"] == "platform-openai-key"
    assert resolved["credential_source"] == "platform"