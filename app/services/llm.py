"""Adaptador de IA multi-provedor.

Todos os provedores suportados usam a API de chat "OpenAI-compativel"
(endpoint POST /chat/completions). Isso permite trocar de IA de forma trivial
apenas alterando a configuracao da empresa (provider, model, key, base_url).

Padrao barato (default): Groq com GPT-OSS 120B.
"""
from __future__ import annotations

import httpx

# base_url padrao para cada provedor quando nao informado
PROVIDER_DEFAULTS: dict[str, dict] = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-120b",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
    },
    "deepseek": {
        "base_url": "https://api.deepseek.com/v1",
        "model": "deepseek-chat",
    },
    "mistral": {
        "base_url": "https://api.mistral.ai/v1",
        "model": "mistral-small-latest",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model": "llama3",
        "api_key": "ollama",  # nao requer chave
    },
    "mock": {
        # Simula uma IA sem chamar servico externo. Util para testes/demonstracao.
        "base_url": "mock://internal",
        "model": "mock-response",
    },
}


class LLMError(Exception):
    pass


def _resolve(provider: str | None, model: str | None, api_key: str | None, base_url: str | None) -> dict:
    defaults = PROVIDER_DEFAULTS.get((provider or "").lower(), {})
    return {
        "provider": (provider or "groq").lower(),
        "model": model or defaults.get("model") or "openai/gpt-oss-120b",
        "api_key": api_key or defaults.get("api_key") or "",
        "base_url": (base_url or defaults.get("base_url") or "").rstrip("/"),
    }


async def generate_reply(
    system_prompt: str,
    history: list[dict],
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    temperature: float = 0.4,
    timeout: float = 40.0,
) -> str:
    """Gera uma resposta do assistente dado um historico de mensagens.

    history: lista de dicts {"role": "user"|"assistant", "content": str}
    """
    cfg = _resolve(provider, model, api_key, base_url)

    if cfg["provider"] == "mock":
        last_user = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last_user = m.get("content", "")
                break
        return (
            f"Ola! Recebi sua mensagem e ja estou analisando. "
            f"(modo demonstracao - sem IA real). Voce perguntou: '{last_user[:60]}'"
        )

    if not cfg["base_url"]:
        raise LLMError("Base URL do provedor de IA nao configurada")

    url = f"{cfg['base_url']}/chat/completions"

    headers = {"Content-Type": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    payload = {
        "model": cfg["model"],
        "messages": [{"role": "system", "content": system_prompt}] + history,
        "temperature": temperature,
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        raise LLMError(f"Provedor de IA retornou erro {exc.response.status_code}: {exc.response.text}")
    except httpx.HTTPError as exc:
        raise LLMError(f"Erro ao chamar provedor de IA: {exc}")

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise LLMError("Resposta do provedor de IA em formato inesperado")
