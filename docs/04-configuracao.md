# 04 — Configuracao

## Arquivos de Configuracao

| Arquivo | Finalidade |
|---------|-----------|
| `.env` | Variaveis de ambiente (nao versionado) |
| `.env.example` | Template de variaveis de ambiente |
| `alembic.ini` | Configuracao do Alembic (migrations) |
| `docker-compose.yml` | Orquestracao dos containers |
| `docker-compose.override.yml` | Overrides para desenvolvimento |
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

O sistema suporta multiplos provedores de IA. A configuracao segue a ordem:

1. Configuracao da empresa (company_configs)
2. Variaveis de ambiente globais (DEFAULT_AI_*)
3. Defaults do codigo

## Configuracao do WhatsApp

A integracao com WhatsApp e feita via **Evolution API**. Configuracao:

1. `EVOLUTION_BASE_URL`: URL da instancia da Evolution
2. `EVOLUTION_API_KEY`: Chave de API da Evolution (em v2.2.x e a senha definida no instal; em 2.4.0+ e o `api_key` da ativacao de licenca)
3. `EVOLUTION_INSTANCE`: Nome da instancia

O webhook deve apontar para: `POST /webhook/whatsapp/{company_id}`
