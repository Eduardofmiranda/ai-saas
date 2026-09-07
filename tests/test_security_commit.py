"""Regressions for the first local security hardening step."""
import pytest
from fastapi import HTTPException
from starlette.requests import Request

from test_config import router_context
from app.models.user import User
from app.models.platform_ai_provider import PlatformAIProvider
from app.routers.config_router import _evo_config
from app.routers.webhook_router import _verify_webhook_auth
from app.services.config_service import get_or_create_config, resolve_ai_config


@pytest.mark.parametrize("role", ["owner", "admin", "agent"])
@pytest.mark.parametrize("field", [
    "ai_provider", "ai_model", "ai_api_key", "ai_base_url",
    "evolution_base_url", "evolution_api_key", "evolution_instance",
])
def test_tenant_cannot_update_infrastructure(router_context, monkeypatch, role, field):
    client, db, company = router_context
    monkeypatch.setattr("app.services.platform_access.get_secret", lambda name: "")
    user = db.query(User).filter(User.company_id == company.id).one()
    user.role = role
    db.commit()
    config = get_or_create_config(db, company.id)
    previous = getattr(config, field)
    response = client.patch("/config/", json={field: "unauthorized-value"})
    assert response.status_code == 403
    db.refresh(config)
    assert getattr(config, field) == previous


@pytest.mark.parametrize("source", ["platform", "environment"])
def test_global_key_never_uses_company_endpoint(db_session, config, monkeypatch, source):
    config.ai_provider = "openai"
    config.ai_api_key = ""
    config.ai_base_url = "https://untrusted.invalid"
    values = {
        "DEFAULT_AI_PROVIDER": "openai",
        "DEFAULT_AI_API_KEY": "test-environment-key",
        "DEFAULT_AI_BASE_URL": "https://environment.invalid/v1",
    }
    monkeypatch.setattr("app.services.config_service.get_secret", lambda name: values.get(name, ""))
    if source == "platform":
        db_session.add(PlatformAIProvider(
            provider="openai", api_key="test-platform-key",
            base_url="https://platform.invalid/v1", enabled=True,
        ))
        db_session.commit()
    resolved = resolve_ai_config(config, db_session)
    assert resolved["credential_source"] == source
    assert resolved["base_url"] == f"https://{source}.invalid/v1"


def test_evolution_route_ignores_legacy_endpoint_and_key(config, monkeypatch):
    values = {"EVOLUTION_BASE_URL": "http://evolution:8080", "EVOLUTION_API_KEY": "test-key"}
    monkeypatch.setattr("app.routers.config_router.get_secret", lambda name: values.get(name, ""))
    config.evolution_base_url = "https://untrusted.invalid"
    config.evolution_api_key = "legacy-key"
    base, key, instance = _evo_config(config)
    assert (base, key) == ("http://evolution:8080", "test-key")


@pytest.mark.parametrize("configured,received,status", [
    ("", "", 503), ("test-secret", "", 401), ("test-secret", "wrong", 401),
])
def test_webhook_fails_closed(monkeypatch, configured, received, status):
    monkeypatch.setattr("app.routers.webhook_router.get_secret", lambda name: configured)
    request = Request({"type": "http", "headers": [(b"evolution-auth", received.encode())]})
    with pytest.raises(HTTPException) as error:
        _verify_webhook_auth(request)
    assert error.value.status_code == status
