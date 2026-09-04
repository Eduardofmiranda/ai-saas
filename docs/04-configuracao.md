# 04 — Configuracao

## Arquivos de Configuracao

| Arquivo | Finalidade |
|---------|-----------|
| `.env` | Variaveis de ambiente (nao versionado) |
| `.env.example` | Template de variaveis de ambiente |
| `alembic.ini` | Configuracao do Alembic (migrations) |
| `docker-compose.yml` | Orquestracao dos containers |
| `docker-compose.dev.yml` | Overrides para desenvolvimento (usar `-f` explicitamente) |
| `frontend/vite.config.js` | Configuracao do Vite (build) |
| `frontend/nginx.conf` | Configuracao do nginx (producao) |

## Configuracao por Empresa

A configuracao de IA e WhatsApp e feita por empresa via API `PATCH /config/`:

```json
{
  "ai_provider": "groq",
  "ai_model": "qwen/qwen3.8-27b",
  "ai_api_key": "sua-chave-aqui",
  "system_prompt": "Voce e um assistente de atendimento.",
  "evolution_base_url": "http://evolution:8080",
  "evolution_api_key": "sua-chave-evolution",
  "evolution_instance": "minha-instancia",
  "ai_on": true
}
```

## Configuracao da IA

O sistema suporta multiplos provedores. A resolucao e unica para conversa,
workflows/nodes, RAG, Knowledge e o teste de conectividade:

1. Override nao vazio da empresa em `company_configs`
2. Variaveis globais `DEFAULT_AI_*` do `.env` realmente carregado pelo backend
3. Defaults seguros do adapter (provider, modelo e base URL quando nao houver env)

Uma configuracao nova e criada com `ai_provider`, `ai_model`, `ai_api_key` e
`ai_base_url` vazios. Isso e intencional: campos vazios usam o `.env` e nao
criam um valor aleatorio no banco. A resposta de `GET /config/` conserva esses
campos brutos e inclui `resolved_ai_provider`/`resolved_ai_model` apenas para a
interface mostrar o valor efetivo, sem expor a chave.

Na tela `/ai`, salvar prompt ou status nao persiste provider/modelo. Provider e
modelo so viram override quando o operador os altera; **Usar padroes do .env**
limpa os dois overrides ao salvar.

## Configuracao do WhatsApp

A integracao com WhatsApp e feita via **Evolution API**. Configuracao:

1. `EVOLUTION_BASE_URL`: URL da instancia da Evolution
2. `EVOLUTION_API_KEY`: Chave de API da Evolution (em v2.2.x e a senha definida no instal; em 2.4.0+ e o `api_key` da ativacao de licenca)
3. `EVOLUTION_INSTANCE`: Nome da instancia

O webhook deve apontar para: `POST /webhook/whatsapp/{company_id}`
