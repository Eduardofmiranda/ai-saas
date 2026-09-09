# 15 — Deploy na VPS

## Estado implementado

A VPS executa Docker Compose. O banco principal da aplicacao e sempre o
**Supabase**, referenciado por `DATABASE_URL`; o Postgres do Compose e apenas
um fallback/local e tambem e usado pela Evolution como banco operacional.

O `backend` executa `alembic upgrade head` antes do Uvicorn. `celery-worker` e
`celery-beat` aguardam o backend saudavel, logo nao processam tarefas contra um
schema antigo.

## Preparar a VPS

1. Atualize o codigo no diretorio do projeto.
2. Preserve o `.env` da VPS: ele e fora do Git e contem os segredos reais.
3. Compare o `.env` com `.env.production.example`; para esta versao, preencha:
   - `DEFAULT_EMBEDDING_PROVIDER`, `DEFAULT_EMBEDDING_MODEL`,
     `DEFAULT_EMBEDDING_API_KEY`, `DEFAULT_EMBEDDING_BASE_URL`;
   - `DEFAULT_EMBEDDING_DIMENSIONS=1536`;
   - `ENABLE_PGVECTOR=true`, depois de confirmar que pgvector esta disponivel
     no projeto Supabase.
4. Nunca use `down -v`, `reset` ou exclusao de volumes durante uma atualizacao.

## Implantar

```bash
cd /opt/ai-saas
git fetch origin
git switch -C main origin/main

# Recria processos que recebem env ou imagem nova.
docker compose up -d --build --no-deps --force-recreate backend
# Worker e beat passam a depender do backend migrado e saudavel.
docker compose up -d --build --no-deps --force-recreate celery-worker celery-beat
docker compose up -d --build --no-deps --force-recreate frontend

# Evolution permanece em compose separado.
docker compose -f docker-compose.evolution.yml up -d
```

`docker compose restart` sozinho **nao reaplica** variaveis do `.env` no
backend/worker. Use `--force-recreate` quando houver mudanca de env.

## Validacao obrigatoria na VPS

```bash
# Confirma banco real e revisao aplicada (sem expor a URL no log)
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import text; print(dict(engine.connect().execute(text('select current_database(), inet_server_addr()')).mappings().first()))"
docker compose exec backend alembic current

# Saude do processo e dependencias
curl -fsS http://127.0.0.1:8000/health
curl -fsS http://127.0.0.1:8000/health/db
curl -fsS http://127.0.0.1:8000/health/redis
curl -fsS http://127.0.0.1:8000/health/llm
curl -fsS http://127.0.0.1:8000/health/evolution

# Confirma que os containers receberam as configuracoes esperadas.
docker compose exec backend printenv DEFAULT_EMBEDDING_MODEL
docker compose exec backend printenv ENABLE_PGVECTOR
```

Para `ENABLE_PGVECTOR=true`, `alembic current` deve mostrar
`0006_pgvector_knowledge`. Se a migration informar indisponibilidade da
extensao, nao force o deploy: habilite `vector` no Supabase ou volte a
`ENABLE_PGVECTOR=false` antes de recriar o backend.

### Agenda 8.6b — validacao extra apos atualizar

A Agenda 8.6b (confirmação 2 passos + lembretes) introduz a migration
`0014_agenda_confirmation` (aplicada pelo `alembic upgrade head` do backend) e
duas tarefas periodicas novas.

```bash
# O alembic current deve estar em 0019_user_departments (head) apos o deploy
docker compose exec backend alembic current

# Colunas novas existentes (confirma + lembrete)
docker compose exec backend python -c "
from app.database.database import engine
from sqlalchemy import text
sql = \"select column_name from information_schema.columns where table_name='agenda_config' and column_name in ('confirmation_required','reminders_enabled','whatsapp_number')\"
print([r[0] for r in engine.connect().execute(text(sql)).all()])"

# beat com as novas tarefas? (listar o schedule no container beat)
docker compose exec celery-beat celery -A app.tasks.celery_app inspect registered 2>/dev/null | Select-String 'agenda'
```

Se o beat nao registrar as tarefas, recrie o container: `docker compose up -d
--no-deps --force-recreate celery-beat` (restart nao reaplica o schedule).

### Migration 0015 — indice composto da agenda

A migration `0015_agenda_slot_index` adiciona o indice composto
`ix_appointments_company_date` em `(company_id, date)` para performance da
checagem de conflito. O `alembic upgrade head` do backend aplica automaticamente.

### Migration 0016 — acoes pendentes de remarcar/cancelar

A migration `0016_pending_appointment_actions` cria a tabela de consentimento
server-side da Secretaria IA: remarcacoes/cancelamentos via WhatsApp ficam
pendentes ate o cliente responder CONFIRMAR (ver `docs/16-seguranca.md` e
`docs/23-agenda-confirmacao-lembretes.md`). Aplicada automaticamente no startup.

### Migration 0017 — limites de abuso de IA

A migration `0017_ai_limits` adiciona colunas de limites em `company_configs`
(ai_daily_message_limit, ai_daily_token_limit, ai_timeout_seconds,
ai_max_retries, ai_fallback_message) e cria a tabela `company_ai_usage`
(company_id, usage_date, message_count, token_count).

### Migration 0018 — audit log

A migration `0018_audit_log` cria a tabela `audit_logs` (company_id, user_id,
action, entity, entity_id, details, ip_address, user_agent, created_at).
Registra acoes criticas: auth, CRUD de users/workflows, config, platform_admin.

### Migration 0019 — membros x setores com nivel de acesso

A migration `0019_user_departments` cria a tabela `user_departments` (user_id,
department_id, level, UniqueConstraint uq_user_department). Associa membros a
setores com nível (`view`/`attend`/`manage`) e habilita o filtro de conversas
por setor no inbox. Aplicada automaticamente no startup do backend.

## Portas

| Porta | Servico |
|---|---|
| 80 | Frontend nginx; encaminha a API pelo prefixo `/api` |
| 8000 | Backend FastAPI (uso interno/operacional) |
| 8080 | Evolution API |
| 5432 | Postgres local interno; **nao** e o banco principal de producao |
| 6379 | Redis interno |

## Riscos conhecidos

- `DEFAULT_EMBEDDING_MODEL` alterado sem reindexar Knowledge torna os vetores
  anteriores incompatíveis. Reindexe os documentos após trocar modelo/dimensao.
- `SECRET_ENCRYPTION_KEY` nao pode mudar: ela protege as chaves gravadas no
  banco.
- A VPS nao e ambiente de teste: execute `pytest` e o E2E mock local antes da
  implantacao.