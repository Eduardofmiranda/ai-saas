# Deploy para Railway - Guia Rápido

## 1. Preparação (uma vez)

### Crie conta e projeto
```bash
# Instale CLI
npm install -g @railway/cli

# Login
railway login

# Crie projeto
railway init

# Adicione Postgres + Redis gerenciados
railway add postgresql
railway add redis
```

### Configure variáveis no Dashboard Railway
Vá em **Settings → Variables** e adicione:

| Variable | Valor |
|----------|-------|
| `DATABASE_URL` | `postgresql://...` (fornecido pelo Railway Postgres) |
| `REDIS_URL` | `redis://...` (fornecido pelo Railway Redis) |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `DEFAULT_AI_PROVIDER` | `groq` |
| `DEFAULT_AI_MODEL` | `qwen/qwen3.8-27b` |
| `DEFAULT_AI_API_KEY` | `gsk_xxx` (sua key Groq real) |
| `EVOLUTION_BASE_URL` | `https://evolution.seudominio.com` |
| `EVOLUTION_API_KEY` | `sua-chave-evolution` |
| `EVOLUTION_INSTANCE` | `prod` |

### Configure GitHub Secrets
No repositório: **Settings → Secrets and variables → Actions**

| Secret | Valor |
|--------|-------|
| `RAILWAY_TOKEN` | `railway login --token` (gere em railway.app/account/tokens) |
| `RAILWAY_PROJECT_ID` | ID do projeto (no URL do dashboard) |

## 2. Deploy Automático (CI/CD)

Push na `main` → GitHub Actions roda:
1. ✅ Testes (Postgres + Redis services)
2. 📦 Build Docker images → GHCR
3. 🚀 Deploy Railway (backend + frontend)
4. 🔄 Migrations (alembic upgrade head)

## 3. Deploy Manual (se precisar)

```bash
# Torne executável
chmod +x deploy-railway.sh

# Rode
./deploy-railway.sh
```

## 4. Domínio Customizado

No Dashboard Railway → **Settings → Domains** → `Add Domain`
- `api.seudominio.com` → serviço `backend`
- `app.seudominio.com` → serviço `frontend`

Configure DNS:
```
CNAME api.seudominio.com   → backend.up.railway.app
CNAME app.seudominio.com   → frontend.up.railway.app
```

## 5. Evolution API Webhook

Configure na Evolution API:
```
Webhook URL: https://api.seudominio.com/webhook/whatsapp/{company_id}
```

## 6. Verificar saúde

```bash
# Logs
railway logs --service backend
railway logs --service frontend

# Status
railway status

# Shell no container
railway shell --service backend
```

---

## Troubleshooting

| Problema | Solução |
|----------|---------|
| Build falha | `railway logs --service backend` |
| Migration erro | `railway run --service backend alembic upgrade head` |
| Frontend 404 | Verifique `nginx.conf` proxy `/api` |
| CORS erro | Confira `ALLOWED_ORIGINS` no backend |
| DB connection | Verifique `DATABASE_URL` no dashboard |