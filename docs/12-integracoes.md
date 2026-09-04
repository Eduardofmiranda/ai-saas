# 12 — Integracoes Externas

## Evolution API (WhatsApp)

### O que e

A Evolution API e um projeto **open-source e self-hosted** (NÃO e um servico pago/SaaS com inscricao). Voce mesmo instala via Docker na sua VPS e conecta no seu proprio numero de WhatsApp. E **100% gratuito** (tier `community`), sem limite de mensagens ou instancias.

**Licenciamento (versao 2.4.0+):** desde a v2.4.0 a Evolution exige a **ativacao de licenca gratuita** da instancia antes de servir trafego. O fluxo:

1. A instancia gera um `instance_id` (UUID) e um token de registro.
2. A instancia exibe uma URL de ativacao no terminal/manager (`https://<host>/manager/login`).
3. O operador autentica no servidor de licencas (`license.evolutionfoundation.com.br` — Magic Link/Google/GitHub) e autoriza a instancia.
4. O servidor retorna um `api_key` (chave de 64 caracteres hex).
5. A instancia ativa a licenca chamando `POST /v1/activate` com assinatura `HMAC-SHA256` (exemplo abaixo) e envia *heartbeats* periodicos.

> **Instalacoes em versoes anteriores (ex: `evoapicloud/evolution-api:v2.3.7`, a imagem fixada no `docker-compose.evolution.yml`) NAO exigem ativacao** e continuam funcionando com a chave que voce define no param `AUTHENTICATION_API_KEY`.

### Fluxo de "instalacao" (so uma vez)

1. Subir a imagem pelo Docker (feito pelo `docker-compose.evolution.yml`).
2. **Se v2.4.0+:** ativar a licenca gratuita da instancia (guia acima) e copiar o `api_key`.
   **Se v2.3.x e anteriores (a versao fixada):** definir `EVOLUTION_AUTH_KEY` no `.env` (vira o `AUTHENTICATION_API_KEY` da Evolution) e `EVOLUTION_API_KEY` (mesma chave, usada pelo backend).
3. Criar uma **instancia** (`POST /instance/create`, obrigatorio `integration: "WHATSAPP-BAILEYS"`).
4. Obter o **QR** (`GET /instance/connect/{instance}`, expira em ~1min) e escanear com o WhatsApp.
5. Configurar o **webhook** para apontar ao backend (`POST /webhook/set/{instance}`, com `"enabled": true`).

**O que e cada configuracao:**
- `EVOLUTION_BASE_URL`: endereco da instalacao — dentro do docker e `http://evolution:8080` (deve estar na **mesma rede** do backend).
- `EVOLUTION_AUTH_KEY`: chave injetada como `AUTHENTICATION_API_KEY` da Evolution (v2.3.x = a que VOCE define). NAO e a chave da Groq.
- `EVOLUTION_API_KEY`: a mesma chave, usada pelo **backend** para autenticar nas chamadas (`send_text`).
- `EVOLUTION_INSTANCE`: default automatico por empresa (`inst-<company_id>`, criada pelo `POST /config/whatsapp/setup` com `integration: "WHATSAPP-BAILEYS"`). O env `EVOLUTION_INSTANCE` e so fallback global — nao compartilhar uma instancia entre empresas.

### Como obter o api_key (Evolution v2.4.0+)

O `api_key` (64 caracteres hex) e retornado pelo servidor de licencas apos o operador autorizar a instancia. A ativacao em si usa HMAC-SHA256 no corpo da requisicao:

```python
import hmac, hashlib, json, requests

api_key = "64chars_hex..."
payload = {
    "instance_id": "550e8400-e29b-41d4-a716-446655440000",
    "version": "2.4.0",
}
body = json.dumps(payload, separators=(",", ":"))
sig = hmac.new(api_key.encode(), body.encode(), hashlib.sha256).hexdigest()

requests.post(
    "https://license.evolutionfoundation.com.br/v1/activate",
    data=body,
    headers={
        "Content-Type": "application/json",
        "X-API-Key": api_key,
        "X-Signature": sig,
    },
)
```

> **Importante:** o corpo usado no HMAC deve ser **byte a byte identico** ao enviado na requisicao (nao reformatar o JSON entre assinar e enviar).

### Configuracao

```python
# Necessario configurar por empresa:
EVOLUTION_BASE_URL = "http://evolution:8080"
EVOLUTION_API_KEY = "sua-chave"
EVOLUTION_INSTANCE = "sua-instancia"
```

> **Rede:** a Evolution precisa estar na **mesma rede docker** do backend
> (`ai-saas_ai-saas-network`). No `docker-compose.evolution.yml` ela entra nessa
> rede via `external: true` + `name: ai-saas_ai-saas-network`. Se o backend
> tentar `http://evolution:8080` e der "Name or service not known", a Evolution
> esta numa rede separada.

> **Compose da Evolution nao usa `env_file: .env`.** Todas as variaveis sao
> definidas explicitamente (para nao injetar as chaves do app).

> **Alternativa paga (opcional):** existem provedores que hospedam a Evolution API para voce (ex: hosting gerenciado), cobrando por instancia. Nesse caso voce so usa a URL e a chave que eles te passam. Para este projeto usamos a instalacao self-hosted da Evolution na VPS.

### Endpoints Utilizados (backend -> Evolution)

| Metodo | URL | Finalidade |
|--------|-----|-----------|
| GET | `{base}/instance/connectionState/{instance}` | Estado real em memoria (status) |
| GET | `{base}/instance/fetchInstances` | Lista instancias do banco (fallback de status, checagem no setup) |
| POST | `{base}/instance/create` | Criar instancia (`integration: WHATSAPP-BAILEYS` obrigatorio) |
| GET | `{base}/instance/connect/{instance}` | Obter QR (resposta traz `base64` no nivel raiz) |
| DELETE | `{base}/instance/logout/{instance}` | Desconectar (logout) |
| POST | `{base}/message/sendText/{instance}` | Enviar mensagem de texto |

### Detalhe do status (GET /config/whatsapp)

O backend resolve o estado por empresa em `app/routers/config_router.py:whatsapp_status`:

1. **connectionState** (tempo real, em memoria) — fonte preferida.
2. **fetchInstances** — fallback quando o `connectionState` responde 400/nao 200
   ou quando o estado continua `unknown` (usa `connectionStatus` do banco, que
   pode estar stale).

> **Por que nao so connectionState:** a Evolution mantém o estado em memoria e
> o `fetchInstances` reflete o banco — os dois divergem apos logout manual pelo
> manager. A leitura combinada cobre ambos.

### Detalhe do desconectar (POST /config/whatsapp/disconnect)

`app/routers/config_router.py:whatsapp_disconnect` usa `DELETE /instance/logout/{instance}`.
Tratamentos de respostas ja desconhecidas como sucesso:

- **404** — instancia nao existe na Evolution (ja desconectada/removida).
- **400** com `"not connected"` — instancia existe mas ja esta desconectada.

> **Importante (fato verificado):** `POST` em `/instance/logout` retorna **404**
> e `GET /instance/logout?instanceName=...` nao existe. O unico contrato valido
> e `DELETE /instance/logout/{instance}`.

### Webhook

**URL real do backend:** `POST /webhook/whatsapp/{company_id}` (app/routers/webhook_router.py).

> **Planejado (escala):** configurar esse webhook **automaticamente** no
> `POST /config/whatsapp/setup` (hoje e manual via `POST /webhook/set/{instance}`).
> Com isso, nova empresa escaneia o QR e ja recebe mensagens, sem nenhum passo
> manual. Nao implementado ainda — nao afirmar que existe.

Para configurar na Evolution (v2.3.x), o campo `"enabled": true` e obrigatorio.
Use o nome de instancia da empresa (`inst-<company_id>`) e o `company_id` real na
URL do webhook:

```bash
KEY="$(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"
curl -s -X POST http://127.0.0.1:8080/webhook/set/inst-2 \
  -H "apikey: $KEY" -H 'Content-Type: application/json' \
  -d '{"webhook":{"enabled":true,"url":"http://backend:8000/webhook/whatsapp/2","events":["MESSAGES_UPSERT","QRCODE_UPDATED","CONNECTION_UPDATE"]}}'
```

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
    # Converte mensagens do banco para formato LLM.
    # bot/agent -> "assistant"; customer/user -> "user".
```

## LLM Providers

### Suportados

| Provider | Base URL | Modelos |
|----------|---------|---------|
| Groq | `https://api.groq.com/openai/v1` | openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.6-27b, qwen/qwen3.8-27b |
| OpenAI | `https://api.openai.com/v1` | gpt-4o, gpt-4o-mini, etc. |
| DeepSeek | `https://api.deepseek.com` | deepseek-chat, etc. |
| Mistral | `https://api.mistral.ai/v1` | mistral-large, etc. |
| Ollama | `http://localhost:11434/v1` | llama3, etc. |
| Mock | — | Retorna echo (para testes) |

> **Importante (Groq/2026-09-04):** `mixtral-8x7b-32768` foi **descontinuado**;
> `llama-3.3-70b-versatile` e `llama-3.1-8b-instant` sao enterprise-only. A lista
> acima contem os modelos self-serve vigentes. Se uma empresa tem salvo um modelo
> antigo em `company_configs.ai_model`, o valor do banco **tem prioridade** sobre
> `DEFAULT_AI_MODEL` do `.env` — corrigir o registro ou salvar na pagina `/ai`.

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
