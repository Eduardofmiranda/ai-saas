from pydantic import BaseModel


class ConfigCreate(BaseModel):
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    system_prompt: str | None = None
    evolution_base_url: str | None = None
    evolution_api_key: str | None = None
    evolution_instance: str | None = None
    ai_on: bool | None = None


class ConfigUpdate(BaseModel):
    ai_provider: str | None = None
    ai_model: str | None = None
    ai_api_key: str | None = None
    ai_base_url: str | None = None
    system_prompt: str | None = None
    evolution_base_url: str | None = None
    evolution_api_key: str | None = None
    evolution_instance: str | None = None
    ai_on: bool | None = None
    ai_daily_message_limit: int | None = None
    ai_daily_token_limit: int | None = None
    ai_timeout_seconds: int | None = None
    ai_max_retries: int | None = None
    ai_fallback_message: str | None = None


class ConfigResponse(BaseModel):
    company_id: int
    ai_provider: str
    ai_model: str
    ai_base_url: str | None
    system_prompt: str | None
    evolution_base_url: str | None
    evolution_instance: str | None
    has_evolution_key: bool
    ai_on: bool
    # Limites de abuso
    ai_daily_message_limit: int
    ai_daily_token_limit: int
    ai_timeout_seconds: int
    ai_max_retries: int
    ai_fallback_message: str
    # Valores efetivos para a interface; a chave nunca e exposta.
    resolved_ai_provider: str
    resolved_ai_model: str
    ai_credential_source: str
