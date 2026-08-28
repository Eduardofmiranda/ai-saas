# 12 — Integracoes Externas

## Evolution API (WhatsApp)

### O que e

A Evolution API e um projeto **open-source e self-hosted** (NÃO e um servico pago/SaaS com inscricao). Voce mesmo instala via Docker na sua VPS e conecta no seu proprio numero de WhatsApp. **Nao ha cadastro/inscricao** no "site deles" — o unico passo manual e escanear o QR Code do WhatsApp uma vez por instancia.

**Fluxo de "instalacao" (so uma vez):**

1. Subir a imagem pelo Docker (feito pelo `docker-compose.evolution.yml`).
2. Criar uma **instancia** (`createFlowAi`) — e neste momento que o `EVOLUTION_API_KEY` e definido por VOCE.
3. Escanear o QR Code com o WhatsApp que sera usado para atender.
4. Configurar o webhook para apontar ao nosso backend.

**O que e cada configuracao:**
- `EVOLUTION_BASE_URL`: endereco da sua propria instalacao (ex: `http://localhost:8080` ou `http://evolution:8080` dentro do docker).
- `EVOLUTION_API_KEY`: uma senha que VOCE cria ao instalar (param `AUTHENTICATION_API_KEY`). Nao e dada por nenhum provedor.
- `EVOLUTION_INSTANCE`: nome que voce deu a sua instancia (ex: `flowai`).

### Configuracao

```python
# Necessario configurar por empresa:
EVOLUTION_BASE_URL = "http://evolution:8080"
EVOLUTION_API_KEY = "sua-chave"
EVOLUTION_INSTANCE = "sua-instancia"
```

> **Alternativa paga (opcional):** existem provedores que hospedam a Evolution API para voce (ex: hosting gerenciado), cobrando por instancia. Nesse caso voce so usa a URL e a chave que eles te passam. Para este projeto usamos a instalacao self-hosted gratuita na VPS.

### Endpoints Utilizados

| Metodo | URL | Finalidade |
|--------|-----|-----------|
| POST | `{base}/message/sendText/{instance}` | Enviar mensagem de texto |
| POST | `{base}/chat/sendText/{instance}` | Alternativa para envio |

### Webhook

**URL:** `POST /webhook/whatsapp/{company_id}`

**Payload esperado (Evolution API v2):**
```json
{
  "key": {
    "remoteJid": "5511999999999@s.whatsapp.net",
    "id": "3EB0A1F2C4F5E6D7A8B9C0D1E2F3A4B5"
  },
  "message": {
    "conversation": "Ola, preciso de ajuda"
  },
  "pushName": "Nome do Cliente"
}
```

**Dados extraidos:**
- `phone`: `remoteJid` limpo (removido `@s.whatsapp.net`)
- `text`: `message.conversation` ou `message.extendedTextMessage.text`
- `wa_message_id`: `key.id`

### Servico

```python
# app/services/evolution.py
async def send_text(
    company_id, phone, text, config=None, db=None
) -> dict: ...

def extract_webhook_message(body) -> dict:
    # Retorna: {"phone": str, "text": str, "wa_message_id": str}

def build_history(messages) -> list[dict]:
    # Converte mensagens do banco para formato LLM
```

## LLM Providers

### Suportados

| Provider | Base URL | Modelos |
|----------|---------|---------|
| Groq | `https://api.groq.com/openai/v1` | llama-3.3-70b-versatile, qwen3.8-27b, etc. |
| OpenAI | `https://api.openai.com/v1` | gpt-4o, gpt-4o-mini, etc. |
| DeepSeek | `https://api.deepseek.com` | deepseek-chat, etc. |
| Mistral | `https://api.mistral.ai/v1` | mistral-large, etc. |
| Ollama | `http://localhost:11434/v1` | llama3, etc. |
| Mock | — | Retorna echo (para testes) |

### Adaptador

```python
# app/services/llm.py
async def generate(provider, api_key, system_prompt, prompt,
                   history=None, model=None, base_url=None) -> str
```

Todos os providers seguem a interface OpenAI (chat.completions).

### Resolucao de Base URL

1. `config.ai_base_url` (configuracao da empresa)
2. `DEFAULT_AI_BASE_URL` (variavel de ambiente)
3. URL padrao por provider (auto-resolvido)
