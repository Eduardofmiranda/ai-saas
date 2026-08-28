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


class ConfigResponse(BaseModel):
    company_id: int
    ai_provider: str
    ai_model: str
    ai_base_url: str | None
    system_prompt: str | None
    evolution_base_url: str | None
    evolution_instance: str | None
    ai_on: bool
