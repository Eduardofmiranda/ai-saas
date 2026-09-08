"""Adaptador de IA multi-provedor.

Todos os provedores suportados usam a API de chat "OpenAI-compativel"
(endpoint POST /chat/completions). Isso permite trocar de IA de forma trivial
apenas alterando a configuracao da empresa (provider, model, key, base_url).

Padrao barato (default): Groq com GPT-OSS 120B.
"""
from __future__ import annotations

import json
import re

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
        "model": "deepseek-v4-flash",
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


def provider_status_error_message(status_code: int) -> str:
    if status_code == 429:
        return (
            "Limite temporario do provedor de IA atingido. Aguarde alguns instantes e tente novamente; "
            "se persistir, confira a cota, credito e chave em Configuracao > IA."
        )
    return f"Provedor de IA retornou HTTP {status_code}"


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

    if cfg["provider"] not in {"ollama", "mock"} and not cfg["api_key"]:
        raise LLMError(
            f"Nenhuma chave de API foi configurada para o provedor {cfg['provider']}. "
            "Peça ao administrador da plataforma para cadastrar uma chave deste provedor."
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
        # A resposta externa pode conter dados enviados pelo cliente. Nunca a
        # propague para logs, banco ou API.
        raise LLMError(provider_status_error_message(exc.response.status_code)) from exc
    except httpx.HTTPError as exc:
        raise LLMError("Falha de rede ao chamar o provedor de IA") from exc

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError):
        raise LLMError("Resposta do provedor de IA em formato inesperado")


class _JSONModeUnsupported(Exception):
    """Levantado quando o provedor rejeita response_format json_object."""


def extract_json(text: str) -> dict:
    """Extrai o primeiro objeto JSON valido de um texto do LLM.

    Aceita markdown (```json ... ```), texto antes/depois e aspas simples.
    Retorna {} quando nao encontra JSON valido.
    """
    if not text:
        return {}
    cleaned = text.strip()
    # remove bloco de codigo markdown
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned)
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end <= start:
        return {}
    candidate = cleaned[start : end + 1]
    try:
        parsed = json.loads(candidate)
    except (json.JSONDecodeError, ValueError):
        try:
            candidate = candidate.replace("'", '"')
            parsed = json.loads(candidate)
        except (json.JSONDecodeError, ValueError):
            return {}
    return parsed if isinstance(parsed, dict) else {}


async def _chat_json(url: str, headers: dict, model: str, messages: list[dict], *, json_mode: bool, timeout: float = 40.0) -> dict:
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.0,
    }
    if json_mode:
        payload["response_format"] = {"type": "json_object"}
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()
    except httpx.HTTPStatusError as exc:
        if json_mode and exc.response.status_code in (400, 404, 422):
            raise _JSONModeUnsupported() from exc
        raise LLMError(provider_status_error_message(exc.response.status_code)) from exc
    except httpx.HTTPError as exc:
        raise LLMError("Falha de rede ao chamar o provedor de IA") from exc

    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        raise LLMError("Resposta do provedor de IA em formato inesperado")

    parsed = extract_json(content)
    if not parsed:
        raise LLMError("Provedor de IA nao retornou JSON valido para a extracao")
    return parsed


async def generate_structured_json(
    system_prompt: str,
    history: list[dict],
    *,
    provider: str | None = None,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    timeout: float = 40.0,
) -> dict:
    """Gera um objeto JSON estruturado (ex.: extracao de dados da conversa).

    Tenta response_format json_object (OpenAI-compativel) e, se o provedor
    rejeitar, repete sem o modo JSON e usa um parser tolerante.
    """
    cfg = _resolve(provider, model, api_key, base_url)

    if cfg["provider"] == "mock":
        return {
            "name": "",
            "email": "cliente@mock.com",
            "phone": "",
            "company": "",
            "city": "",
            "notes": "",
        }

    if cfg["provider"] not in {"ollama", "mock"} and not cfg["api_key"]:
        raise LLMError(
            f"Nenhuma chave de API foi configurada para o provedor {cfg['provider']}. "
            "Peça ao administrador da plataforma para cadastrar uma chave deste provedor."
        )

    if not cfg["base_url"]:
        raise LLMError("Base URL do provedor de IA nao configurada")

    url = f"{cfg['base_url']}/chat/completions"
    headers = {"Content-Type": "application/json"}
    if cfg["api_key"]:
        headers["Authorization"] = f"Bearer {cfg['api_key']}"

    messages = [
        {"role": "system", "content": system_prompt},
        *[m for m in history if isinstance(m, dict) and m.get("role") in ("user", "assistant")],
    ]

    try:
        return await _chat_json(url, headers, cfg["model"], messages, json_mode=True, timeout=timeout)
    except _JSONModeUnsupported:
        return await _chat_json(url, headers, cfg["model"], messages, json_mode=False, timeout=timeout)
