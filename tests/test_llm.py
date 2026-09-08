import httpx
import pytest

from app.services import llm
from app.services.llm import (
    generate_reply_with_tools,
    provider_status_error_message,
    extract_json,
    generate_structured_json,
)


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


# ---------------------------------------------------------------------------
# Function calling (generate_reply_with_tools)
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload, status=200):
        self._payload = payload
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            req = httpx.Request("POST", "http://fake")
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=req,
                response=httpx.Response(self.status_code, request=req),
            )

    def json(self):
        return self._payload


@pytest.fixture
def fake_llm(monkeypatch):
    """Substitui httpx.AsyncClient por um cliente falso com fila de respostas."""
    state = {"responses": [], "requests": []}

    class _FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def post(self, url, *, json=None, headers=None):
            state["requests"].append({"url": url, "json": json, "headers": headers})
            if not state["responses"]:
                raise AssertionError("fake_llm: nenhuma resposta agendada")
            return state["responses"].pop(0)

    monkeypatch.setattr(llm.httpx, "AsyncClient", _FakeClient)
    return state


def _assistant_message(content, tool_calls=None):
    msg = {"role": "assistant"}
    if content is not None:
        msg["content"] = content
    if tool_calls:
        msg["tool_calls"] = tool_calls
    return msg


def _chat_payload(message):
    return {"choices": [{"message": message}]}


def _tool_call(name, arguments, call_id="call_1"):
    return {
        "id": call_id,
        "type": "function",
        "function": {"name": name, "arguments": arguments},
    }


@pytest.mark.asyncio
async def test_tools_loop_executes_and_returns_final_content(fake_llm):
    fake_llm["responses"] = [
        _FakeResponse(
            _chat_payload(
                _assistant_message(
                    None,
                    [
                        _tool_call("verificar_disponibilidade", '{"date": "2026-09-21"}', "call_1"),
                        _tool_call("consultar_agenda", "{}", "call_2"),
                    ],
                )
            )
        ),
        _FakeResponse(
            _chat_payload(
                _assistant_message("Segunda-feira temos horario as 10:00 e 11:00.")
            )
        ),
    ]
    calls = []

    def execute_tool(name, args):
        calls.append((name, args))
        return {"ok": True, "slots": ["10:00"]}

    result = await generate_reply_with_tools(
        system_prompt="sistema",
        history=[{"role": "user", "content": "quero agendar"}],
        provider="openai",
        model="x",
        api_key="k",
        base_url="https://example.com/v1",
        tools=[{"type": "function", "function": {"name": "verificar_disponibilidade"}}],
        execute_tool=execute_tool,
    )

    assert result == "Segunda-feira temos horario as 10:00 e 11:00."
    assert calls == [
        ("verificar_disponibilidade", {"date": "2026-09-21"}),
        ("consultar_agenda", {}),
    ]

    second_request = fake_llm["requests"][1]["json"]
    assert second_request["tools"]
    roles = [m["role"] for m in second_request["messages"]]
    assert roles == ["system", "user", "assistant", "tool", "tool"]
    tool_msgs = [m for m in second_request["messages"] if m["role"] == "tool"]
    assert tool_msgs[0]["tool_call_id"] == "call_1"
    assert tool_msgs[0]["content"] == '{"ok": true, "slots": ["10:00"]}'


@pytest.mark.asyncio
async def test_tools_fallback_when_provider_rejects_tools(fake_llm):
    fake_llm["responses"] = [
        _FakeResponse({"error": "tools not supported"}, status=400),
        _FakeResponse(_chat_payload(_assistant_message("Sem tools, mas respondo mesmo assim."))),
    ]

    result = await generate_reply_with_tools(
        system_prompt="sistema",
        history=[{"role": "user", "content": "ola"}],
        provider="openai",
        model="x",
        api_key="k",
        base_url="https://example.com/v1",
        tools=[{"type": "function", "function": {"name": "x"}}],
        execute_tool=lambda name, args: {},
    )

    assert result == "Sem tools, mas respondo mesmo assim."
    assert "tools" not in fake_llm["requests"][1]["json"]


@pytest.mark.asyncio
async def test_tools_error_from_executor_is_delivered_to_model(fake_llm):
    fake_llm["responses"] = [
        _FakeResponse(
            _chat_payload(_assistant_message(None, [_tool_call("criar_agendamento", '{"appointment_id": 1}')]))
        ),
        _FakeResponse(_chat_payload(_assistant_message("Desculpe, sem horario livre."))),
    ]
    calls = []

    def execute_tool(name, args):
        calls.append((name, args))
        raise ValueError("agenda bloqueada")

    result = await generate_reply_with_tools(
        system_prompt="sistema",
        history=[{"role": "user", "content": "ola"}],
        provider="openai",
        model="x",
        api_key="k",
        base_url="https://example.com/v1",
        tools=[{"type": "function"}],
        execute_tool=execute_tool,
    )

    assert result == "Desculpe, sem horario livre."
    assert calls == [("criar_agendamento", {"appointment_id": 1})]
    tool_msg = [m for m in fake_llm["requests"][1]["json"]["messages"] if m["role"] == "tool"][0]
    assert "error" in tool_msg["content"]
    assert "agenda bloqueada" not in tool_msg["content"]


@pytest.mark.asyncio
async def test_tools_max_rounds_raises_llm_error(fake_llm):
    fake_llm["responses"] = [
        _FakeResponse(_chat_payload(_assistant_message(None, [_tool_call("x", "{}")])))
        for _ in range(5)
    ]

    with pytest.raises(llm.LLMError):
        await generate_reply_with_tools(
            system_prompt="sistema",
            history=[{"role": "user", "content": "ola"}],
            provider="openai",
            model="x",
            api_key="k",
            base_url="https://example.com/v1",
            tools=[{"type": "function"}],
            execute_tool=lambda name, args: {},
            max_tool_rounds=4,
        )


@pytest.mark.asyncio
async def test_tools_malformed_arguments_become_empty_dict(fake_llm):
    fake_llm["responses"] = [
        _FakeResponse(
            _chat_payload(_assistant_message(None, [_tool_call("verificar_disponibilidade", "nao e json", "call_9")]))
        ),
        _FakeResponse(_chat_payload(_assistant_message("ok"))),
    ]
    calls = []

    await generate_reply_with_tools(
        system_prompt="sistema",
        history=[],
        provider="openai",
        model="x",
        api_key="k",
        base_url="https://example.com/v1",
        tools=[{"type": "function"}],
        execute_tool=lambda name, args: calls.append((name, args)) or {"ok": True},
    )

    assert calls == [("verificar_disponibilidade", {})]


@pytest.mark.asyncio
async def test_tool_call_budget_rejects_batch_before_side_effects(fake_llm):
    fake_llm["responses"] = [
        _FakeResponse(_chat_payload(_assistant_message(None, [
            _tool_call("x", "{}", f"call_{i}") for i in range(3)
        ]))),
    ]
    executed = []
    with pytest.raises(llm.LLMError, match="Limite de chamadas"):
        await generate_reply_with_tools(
            system_prompt="synthetic", history=[], provider="openai", model="x",
            api_key="synthetic", base_url="https://example.com/v1",
            tools=[{"type": "function"}], max_tool_calls=2,
            execute_tool=lambda name, args: executed.append(name),
        )
    assert not executed


@pytest.mark.asyncio
async def test_tool_errors_do_not_disclose_sensitive_exception(fake_llm):
    fake_llm["responses"] = [
        _FakeResponse(_chat_payload(_assistant_message(None, [_tool_call("x", "{}")]))),
        _FakeResponse(_chat_payload(_assistant_message("safe response"))),
    ]

    def fail(name, args):
        raise RuntimeError("postgresql://synthetic-secret SQL PARAMETERS synthetic-customer")

    await generate_reply_with_tools(
        system_prompt="synthetic", history=[], provider="openai", model="x",
        api_key="synthetic", base_url="https://example.com/v1",
        tools=[{"type": "function"}], execute_tool=fail,
    )
    messages = fake_llm["requests"][1]["json"]["messages"]
    content = next(m["content"] for m in messages if m["role"] == "tool")
    assert "synthetic-secret" not in content
    assert "SQL" not in content
    assert "synthetic-customer" not in content
