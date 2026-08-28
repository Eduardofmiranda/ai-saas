# 15 — Deploy

## Opcoes

### Docker Compose (Producao)

```bash
# 1. Configurar .env
cp .env.example .env
# Editar .env com valores de producao

# 2. Subir servicos
docker compose up -d --build

# 3. Rodar migracoes
docker compose exec backend alembic upgrade head
```

**Servicos:**

| Servico | Porta | Descricao |
|---------|-------|-----------|
| frontend | 80 | React (nginx) |
| backend | 8000 | FastAPI (uvicorn) |
| celery-worker | — | Worker Celery |
| celery-beat | — | Agendador Celery |
| postgres | 5432 | PostgreSQL (opcional, usar Supabase) |
| redis | 6379 | Redis |

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
- `DATABASE_URL` (Supabase ou PostgreSQL local)
- `SECRET_KEY`
- `SECRET_ENCRYPTION_KEY`
- `DEFAULT_AI_API_KEY`
- `EVOLUTION_API_KEY`

## Ports

| Porta | Servico |
|-------|---------|
| 80 | Frontend (nginx) |
| 8000 | Backend (FastAPI) |
| 5432 | PostgreSQL |
| 6379 | Redis |

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
