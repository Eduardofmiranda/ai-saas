# 🚦 Progresso — AI SaaS (Plataforma estilo n8n)

> Use este documento para acompanhar onde estamos. Marque `[x]` quando concluído.

---

## FASE 1 — Fundação do Backend ✅
- [x] Auth JWT (register/login, bcrypt, python-jose)
- [x] Config por empresa (GET/PATCH /config/)
- [x] Adapter multi-provedor de IA (groq/openai/deepseek/mistral/ollama/mock)
- [x] Evolution API (WhatsApp) + webhook `/webhook/whatsapp/{company_id}`
- [x] Pipeline de atendimento (conversation_service)
- [x] Tabelas no Supabase: users, companies, configs, conversations, messages

## FASE 2 — Motor de Workflows (backend) ✅
- [x] Models: `workflow`, `execution`
- [x] Node catalog + registry (`app/services/nodes/registry.py`) — 10 tipos
- [x] Engine (`app/services/workflow_engine.py`)
- [x] Router CRUD + run + executions (`app/routers/workflow_router.py`)
- [x] Testado E2E: trigger→condição→IA→WhatsApp → `success` com resposta real da IA

## FASE 3 — Frontend React (editor visual) ✅
- [x] Scaffold Vite + React 19 + React Flow + React Router
- [x] Login / registro (consome /auth/*)
- [x] Painel (lista de workflows, criar, excluir)
- [x] Editor visual (paleta, canvas, conexões, inspector de campos)
- [x] Salvar (PATCH), Rodar (POST /run), exibir resultado
- [x] CORS backend → frontend
- [x] Build de produção passa
- [x] Contrato achatado corrigido (node.data.key) — E2E validado

## FASE 4 — Produção / Deploy 🔄 (EM ANDAMENTO)
- [ ] Dockerfile.backend (multi-stage) — ✅ criado, aguarda teste
- [ ] Dockerfile.frontend (multi-stage + nginx) — ✅ criado, aguarda teste
- [ ] docker-compose.yml (postgres, redis, backend, worker, beat, frontend) — ✅ criado
- [ ] Alembic (migrations versionadas) — ✅ criado
- [ ] Celery + Redis (tasks assíncronas) — ✅ criado
- [ ] Testar `docker compose up` local (requer Docker Desktop)
- [ ] Deploy em VPS (passos abaixo)
- [ ] ROTACIONAR credenciais vazadas (Supabase, Groq, Evolution)

## FASE 5 — Melhorias Frontend ⏳ (PRÓXIMA)
- [x] Feedback de loading ao salvar/rodar
- [x] Tratamento de sessão expirada (redirect login)
- [ ] Validação visual do grafo (nós órfãos, nós soltos
- [ ] Confirmar exclusão de nó
- [x] Renomear fluxo no editor
- [ ] Duplicar fluxo
- [ ] Nó de teste (mensagem simulada customizável)
- [x] Exibir logs da execução de forma legível

## FASE 6 — Backend em Produção ⏳
- [ ] Logs estruturados (JSON)
- [ ] Healthcheck `/health` dedicado
- [ ] Rate limiting (login, webhook)
- [ ] Timeout/retry por nó no motor
- [ ] Validação de chave IA/Evolution ao salvar config
- [ ] Backup automatizado do banco

## FASE 7 — Extras (quando precisar)
- [ ] Agendamento (Celery beat + redbeat)
- [ ] Dashboard/analytics mais completo
- [ ] Integração com outros canais (Telegram, Email)
- [ ] Multi-tenancy avançado (planos, quotas)

---

## 🚀 DEPLOY EM VPS — Passo a passo (próximos passos)

### Parte A — Preparar a máquina (uma vez)
- [ ] Comprar/setar VPS (ex: DigitalOcean $4-6/mês, Vultr, Hetzner)
- [ ] Instalar Docker + Docker Compose:
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo systemctl enable --now docker
  # Docker Compose v2 já vem junto no get.docker.com
  ```
- [ ] Instalar git: `sudo apt install git -y`
- [ ] Criar usuário não-root: `sudo adduser deploy && sudo usermod -aG docker deploy`

### Parte B — Configurar o servidor (uma vez)
- [ ] Clonar repositório na VPS:
  ```bash
  su - deploy
  git clone https://github.com/SEU_USUARIO/ai-saas.git
  cd ai-saas
  ```
- [ ] Criar `.env` real na VPS (copiar do projeto + segredos):
  ```bash
  cp .env.example .env
  nano .env   # preencher DATABASE_URL, REDIS_URL, SECRET_KEY, Groq key, Evolution
  ```
- [ ] Configurar domínio + SSL (nginx/Caddy na VPS ou Cloudflare Tunnel)

### Parte C — Deploy (a cada atualização)
- [ ] Rodar o build e subir:
  ```bash
  docker compose up -d --build
  docker compose ps      # verificar todos healthy
  docker compose logs -f backend
  ```
- [ ] Rodar migrações:
  ```bash
  docker compose exec backend alembic upgrade head
  ```

---

## 🔑 CREDENCIAIS VAZADAS (URGENTE)
> A senha do Supabase, a chave Groq e as chaves Supabase foram expostas em conversas anteriores. **Antes de colocar em produção, rotacione todas.**

- [ ] Supabase: mudar senha do banco (Dashboard → Settings → Database → Reset password)
- [ ] Regenerar `sb_secret_*` e `sb_publishable_*` (Dashboard → Settings → API)
- [ ] Groq: gerar nova key em console.groq.com → API Keys → Revoke antiga
- [ ] Evolution: gerar nova chave

---

## 💡 COMO SE LOCALIZAR NESTE DOC
- **✅** concluído e testado
- **🔄** em andamento
- **⏳** próximo
- **⏭️** depois

> Atualize este arquivo ao concluir cada passo.
