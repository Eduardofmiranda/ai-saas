# 15 — Deploy

> **Status: validado em producao (03/09/2026).** O roteiro completo E2E esta em
> `VPS-SETUP.md`. Aqui esta o resumo das decisoes reais.

## Opcoes

### Docker Compose (Producao)

```bash
# 1. Configurar .env (use o template de producao)
cp .env.production.example .env
# Editar .env com valores de producao

# 2. Subir servicos (levanta postgres LOCAL + redis + backend + celery + frontend)
docker compose up -d --build

# 3. Criar as tabelas (NAO e alembic - ver docs/06)
docker compose exec backend python -c "from app.create_tables import *"
```

> **Banco:** o deploy usa **Postgres local** (servico `postgres` do compose,
> volume `postgres_data`). Nao usa Supabase (ver docs/06).

**Servicos:**

| Servico | Porta | Descricao |
|---------|-------|-----------|
| frontend | 80 | React (nginx) |
| backend | 8000 | FastAPI (uvicorn) |
| celery-worker | — | Worker Celery |
| celery-beat | — | Agendador Celery |
| postgres | 5432 (interna) | PostgreSQL LOCAL (volume `postgres_data`) |
| redis | 6379 (interna) | Redis |

> **Evolution API** (WhatsApp) roda em **compose separado**
> (`docker-compose.evolution.yml`), porta **8080** — ver docs/12 e VPS-SETUP.md.

### VPS (Script)

```bash
# 1. Copiar script para VPS
scp deploy-vps.sh usuario@servidor:/opt/ai-saas/

# 2. Executar setup (primeira vez)
ssh usuario@servidor
chmod +x deploy-vps.sh
./deploy-vps.sh setup

# 3. Copiar codigo
rsync -avz --exclude '.git' . usuario@servidor:/opt/ai-saas/

# 4. Executar deploy
./deploy-vps.sh deploy
```

**Script `deploy-vps.sh`:**
- `setup`: Instala Docker, cria diretorios, gera SECRET_KEY + SECRET_ENCRYPTION_KEY
- `deploy`: Copia codigo, roda migrations, reinicia containers

## Variaveis de Ambiente (Producao)

Obrigatórias:
- `DATABASE_URL` (PostgreSQL local: `postgresql://postgres:SENHA@postgres:5432/ai_saas`)
- `POSTGRES_PASSWORD` (mesma senha do `DATABASE_URL`)
- `SECRET_KEY`
- `SECRET_ENCRYPTION_KEY` (distinto de `SECRET_KEY`)
- `DEFAULT_AI_API_KEY` (Groq)
- `EVOLUTION_AUTH_KEY` / `EVOLUTION_API_KEY` (chave da Evolution, NAO a Groq)

## Ports

| Porta | Servico |
|-------|---------|
| 80 | Frontend (nginx) |
| 8000 | Backend (FastAPI) |
| 8080 | Evolution API (WhatsApp) — liberar no firewall |
| 5432 | PostgreSQL (interna) |
| 6379 | Redis (interna) |

## Firewall (VPS com painel, ex.: Hostinger)

Liberar no firewall do provedor: **80, 8080, 22**. Sem a 8080, o QR da
Evolution nao abre fora da VPS.

## Webhook (WhatsApp)

O backend recebe mensagens em **`POST /webhook/whatsapp/{company_id}`**
(app/routers/webhook_router.py). Configure a Evolution com essa URL (usando o
`company_id` real, ex. `1` para a primeira empresa). **NAO existe**
`/webhook/evolution` no codigo.

## Nginx (Frontend)

```nginx
location /api/ {
    proxy_pass http://backend:8000;
}

location /webhook/ {
    proxy_pass http://backend:8000;
}
```

## SSL/TLS

Nao implementado ainda. Recomendado: usar Cloudflare ou nginx com Let's Encrypt.
