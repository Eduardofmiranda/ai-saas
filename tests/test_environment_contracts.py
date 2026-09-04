import asyncio
from pathlib import Path

import pytest

from app.services.config_service import resolve_embedding_config
from app.services.embedding import EmbeddingError, generate_embeddings

ROOT = Path(__file__).resolve().parents[1]


def test_embedding_configuration_is_independent_from_chat(monkeypatch):
    values = {
        "DEFAULT_EMBEDDING_PROVIDER": "openai",
        "DEFAULT_EMBEDDING_MODEL": "text-embedding-3-small",
        "DEFAULT_EMBEDDING_API_KEY": "embedding-key",
        "DEFAULT_EMBEDDING_BASE_URL": "https://embeddings.example/v1",
    }
    monkeypatch.setattr("app.services.config_service.get_secret", lambda name: values.get(name, ""))

    assert resolve_embedding_config() == {
        "provider": "openai",
        "model": "text-embedding-3-small",
        "api_key": "embedding-key",
        "base_url": "https://embeddings.example/v1",
    }


def test_embeddings_require_own_api_key():
    with pytest.raises(EmbeddingError, match="DEFAULT_EMBEDDING_API_KEY"):
        asyncio.run(generate_embeddings(["texto"], api_key=""))


def test_frontend_api_proxy_contract_is_kept():
    api = (ROOT / "frontend" / "src" / "api.js").read_text(encoding="utf-8")
    nginx = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    vite = (ROOT / "frontend" / "vite.config.js").read_text(encoding="utf-8")

    assert '|| "/api"' in api
    assert "location /api/" in nginx
    assert "proxy_pass http://backend:8000/;" in nginx
    assert "rewrite: (path) => path.replace(/^\\/api/, '')" in vite