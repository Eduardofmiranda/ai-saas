# FATOS-CHAVE do Projeto — FlowAI

> **Este arquivo fixa as informacoes principais do projeto para nao se perderem.**
> Fonte de verdade = codigo + producao real. Atualize aqui sempre que algo
> importante mudar de producao/arquitetura/credenciais.

---

## 1. Identidade

- Plataforma de **automacao por workflows** (estilo n8n), foco em
  **atendimento WhatsApp com IA**.
- Multi-tenant: cada **empresa** tem config (IA + Evolution) e workflows proprios.
- Em **producao** na VPS: Hostinger, IP `2.25.122.157`.

## 2. BANCO DE PRODUCAO = **SUPABASE** (IMPORTANTE)

- **O banco de producao e o Supabase**, NAO o Postgres local do Docker.
- A `DATABASE_URL` no `.env` da VPS aponta para a connection string do **Supabase**.
- Em VPS sem IPv6, usar o **pooler IPv4**:
  `postgresql://postgres.<ref>:SENHA@aws-0-<regiao>.pooler.supabase.com:5432/postgres`
- O container `postgres` do `docker-compose.yml` e **alternativa/fallback**, NAO
  o banco em uso em producao.
- `docs/06-banco-de-dados.md`, `docs/15-deploy.md`, `.env.production.example`
  devem refletir isso (ja corrigidos).

> ⚠️ **NUNCA documentar producao como "Postgres local"** — isso causou confusao.
> Producao = Supabase.

## 3. Usuario de producao e criado por CADASTRO, NAO por seed

- Em producao, o usuario e criado pelo **cadastro** (`POST /auth/register`).
- O **seed** (`SEED_DEFAULT_USER`, `app/seed.py`) e **exclusivo de dev local**
  e esta **desabilitado em producao**.
- Login de producao usa o email/senha cadastrados manualmente na primeira vez
  (`teste@flowai.local` / antigo, ou outro cadastrado).
- Se der "email ou senha incorretos" em producao, o usuario provavelmente:
  - nao existe no banco (banco resetado), ou
  - voce esta tentando o usuario de dev (`teste@flowai.com`, que so existe no
    SQLite local).

## 4. Stack tecnologica

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.13, FastAPI, SQLAlchemy, uvicorn |
| Frontend | React 19, Vite, React Flow, React Router |
| Banco (producao) | **Supabase** (PostgreSQL) |
| Banco (dev local) | SQLite (`sqlite:///./aissaas.db`) |
| Cache/Filas | Redis 7 + Celery (worker/beat) |
| WhatsAApp | Evolution API (v2.3.7, compose separado, porta 8080) |
| IA | Adapter multi-provedor (groq/openai/deepseek/mistral/ollama/mock) |
| Deploy | Docker + Docker Compose na VPS |

## 5. Autenticacao / Seguranca (Fase 7)

- JWT HS256, expiracao 24h (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- **`SECRET_KEY` obrigatoria** no startup (sem ela o servidor nao inicia).
- `SECRET_KEY` != `SECRET_ENCRYPTION_KEY` (devem ser distintas).
- Todos os routers de dados protegidos com `get_current_user` + isolamento
  por `company_id`.
- Webhook Evolution valida header `evolution-auth` (HMAC).
- Rate limiting (slowapi): 5/min no login e registro.
- CORS via `ALLOWED_ORIGINS` (env).

## 6. Variaveis de ambiente essenciais (producao)

| Variavel | Valor |
|----------|-------|
| `DATABASE_URL` | Supabase (pooler IPv4) |
| `SECRET_KEY` | `openssl rand -hex 32` |
| `SECRET_ENCRYPTION_KEY` | `openssl rand -hex 32` (distinto) |
| `DEFAULT_AI_API_KEY` | chave da Groq |
| `EVOLUTION_BASE_URL` | `http://evolution:8080` |
| `EVOLUTION_API_KEY` | chave da **Evolution** (NAO a Groq) |
| `EVOLUTION_AUTH_KEY` | mesma da Evolution (tambem usada p/ webhook HMAC) |
| `EVOLUTION_INSTANCE` | `flowai` |
| `ALLOWED_ORIGINS` | dominio de producao |

> Referencia completa: `docs/05-variaveis-ambiente.md`.

## 7. Credenciais rotacionadas (Fase 7)

- No `.env` **local**, as chaves foram rotacionadas e geradas novas.
- `DEFAULT_AI_API_KEY` marcada como `CHANGE_ME_IN_GROQ_CONSOLE` (precisa gerar
  nova key no console Groq).
- Na VPS, a rotacao real (Groq, Supabase, Evolution) e **confirmacao de que o
  WhatsApp continua conectado** ainda precisam ser validadas manualmente.

## 8. Fases do roadmap (PROGRESSO.md)

- Fases 0-7: **concluidas** (visao, backend, workflows, frontend, deploy,
  WhatsApp E2E, QR na tela, seguranca).
- Fase 8: funcionalidades core (midia, upload KB, handoff, horarios, etc.) — proxima.
- Fase 9: intelligence & analytics.
- Fase 10: escala & multi-canal.
- Detalhes em `PROGRESSO.md`.

## 9. Atualizacao da VPS (deploy incremental)

```bash
cd /opt/ai-saas
git fetch origin
git switch -C main origin/main
docker compose up -d --build
docker compose -f docker-compose.evolution.yml up -d
docker compose restart
```

- O `.env` da VPS **NAO e tocado** pelo git (gitignored).
- **NAO rode `down -v` a toa** (apaga banco/WhatsApp).
- **NAO rode `./deploy-vps.sh`** se o `.env` ja existe (pode regenerar chaves e
  quebrar descriptografia).

## 10. Comandos uteis (VPS)

```bash
# backend online?
curl http://localhost:8000/          # {"status":"online"}
curl http://localhost:8000/health     # {"status":"healthy"}

# users do banco (producao = Supabase via backend)
docker compose exec backend python -c "
from app.database.database import SessionLocal
from app.models.user import User
db = SessionLocal()
for u in db.query(User).all():
    print(u.id, u.email, u.company_id)
"

# WhatsApp conectado?
curl -s http://127.0.0.1:8080/instance/connectionState/flowai \
  -H "apikey: $(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"
```
