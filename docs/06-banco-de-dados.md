# 06 — Banco de Dados

## Tecnologia

- **Producao**: **Supabase** (PostgreSQL hospedado, connection string via `DATABASE_URL`)
- **Desenvolvimento local**: SQLite (automatico quando `DATABASE_URL` aponta para `sqlite:///`)
- **ORM**: SQLAlchemy
- **Criacao do schema**: **SQLAlchemy `Base.metadata.create_all`** (mecanismo principal)

> **Como as tabelas sao criadas de fato (confirmado em 03/09/2026):**
>
> 1. As **tabelas base** (`companies`, `users`, `workflows`, `executions`, etc.)
>    sao criadas por **`Base.metadata.create_all`**, que roda **automaticamente no
>    boot do backend** (o `lifespan` em `app/main.py`). Nao e preciso rodar
>    `create_all` manualmente. O `alembic upgrade head` **NAO** cria essas tabelas.
> 2. Existem migrations Alembic **adicionais e idempotentes** em
>    `alembic/versions/`:
>    - `0002_pending_flows.py` — adiciona `pending_flows` (so cria se nao existir)
>    - `0003_knowledge.py` — adiciona `knowledge` e `knowledge_chunks`
>    - `0004_conversation_transfers.py` — adiciona `conversation_transfers`
>    - `0005_password_reset_tokens.py` — adiciona `password_reset_tokens`
>
>    Elas **assumem que as tabelas base ja existem** e apenas garantem que as
>    tabelas `pending_flows`/`knowledge`/`knowledge_chunks` existam (checando com
>    `inspect` e retornando sem erro se ja existirem). Como o `create_all` do boot
>    ja cria tudo (incluindo essas tabelas), elas sao **supérfluas** na pratica.
>
> **Para conferir as tabelas apos o boot (nao e necessario criar manualmente):**
> ```bash
> docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
> ```
>
> **Historico do deploy real (03/09/2026):** na VPS, `alembic upgrade head`
> criou apenas a tabela `alembic_version` e **nao** as tabelas base — por isso o
> `create_all` e o caminho que de fato cria as tabelas. A mudanca para o boot
> automatico (lifespan) elimina a necessidade do passo manual de `create_all`.
>
> **Supabase (banco de producao):** o deploy em producao (VPS) usa o **Supabase**
> como banco principal. A connection string do Supabase vai em `DATABASE_URL`:
>
> - **Pooler IPv4** (recomendado em VPS sem IPv6):
>   `postgresql://postgres.<ref>:SENHA@aws-0-<regiao>.pooler.supabase.com:5432/postgres`
> - **Direct**: `postgresql://postgres:<senha>@db.<ref>.supabase.co:5432/postgres`
>
> Para conectar com o pooler IPv4, defina a env var
> `SUPABASE_DISABLE_IPV6=1` (ou use apenas a URL do pooler). Consulte
> `docs/15-deploy.md` e `.env.production.example`.
>
> > **Nota historica:** em determinado momento o Supabase foi testado como banco
> > e houve a consideracao de usar Postgres local do Docker por causa de IPv6 na
> > direct connection. **Decisao final (fonte de verdade = producao real):**
> > producao USA o **Supabase**. O Postgres local do Docker (`docker-compose`,
> > servico `postgres`) e apenas uma alternativa/fallback, **nao** o banco em uso
> > em producao.

## Tabelas

### companies
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| name | String | NOT NULL |

### users
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL |
| name | String | NOT NULL |
| email | String | UNIQUE, NOT NULL, index |
| password_hash | String | NOT NULL |
| role | String | NOT NULL, default "agent" |

### company_configs
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, UNIQUE, NOT NULL |
| ai_provider | String | default "" |
| ai_model | String | default "" |
| ai_api_key | String | (criptografado com Fernet) |
| ai_base_url | String | default "" |
| system_prompt | Text | default textlong |
| evolution_base_url | String | default "" |
| evolution_api_key | String | (criptografado com Fernet) |
| evolution_instance | String | default "" |
| ai_on | Boolean | default True |

### customers
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL |
| name | String | |
| phone | String | NOT NULL |

### conversations
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL |
| customer_id | Integer | FK -> customers.id, NOT NULL |
| status | String | default "open"; valores: `open` (ativa), `pending_agent` (aguardando humano, handoff), `closed` (fechada) |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

### conversation_transfers
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| conversation_id | Integer | FK -> conversations.id, NOT NULL, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| actor_type | String | `workflow` (node transfer_to_agent) ou `user` (atendente) |
| user_id | Integer | nullable |
| user_name | String | snapshot do nome do atendente |
| action | String | `transfer_requested` / `assumed` / `closed` / `reopened` |
| created_at | DateTime(timezone) | |

### password_reset_tokens
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| user_id | Integer | FK -> users.id, NOT NULL, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| token_hash | String | SHA-256 do token aleatorio (nunca o raw), NOT NULL, index |
| expires_at | DateTime(timezone) | NOT NULL |
| used_at | DateTime(timezone) | nullable (uso unico) |
| created_at | DateTime(timezone) | |

### messages
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| conversation_id | Integer | FK -> conversations.id, NOT NULL |
| sender_type | String | NOT NULL ("customer", "bot" ou "agent") |
| content | Text | NOT NULL |
| wa_message_id | String | default "", index |
| created_at | DateTime(timezone) | |

### workflows
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| name | String | NOT NULL |
| description | Text | default "" |
| data | JSON | (grafo: nodes + edges) |
| trigger_type | String | default "message" |
| trigger_config | JSON | default {} |
| active | Boolean | default False |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

### executions
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| workflow_id | Integer | FK -> workflows.id, NOT NULL, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| status | String | NOT NULL, default "pending" |
| context | JSON | (trigger payload + logs) |
| node_results | JSON | (dados acumulados dos nodes) |
| error | Text | default "" |
| started_at | DateTime(timezone) | nullable |
| finished_at | DateTime(timezone) | nullable |
| created_at | DateTime(timezone) | |

### pending_flows
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| workflow_id | Integer | FK -> workflows.id, NOT NULL, index |
| execution_id | Integer | FK -> executions.id, NOT NULL, index |
| phone | String | NOT NULL, index |
| snapshot | JSON | (data + next_node_id) |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

### knowledge
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| name | String | NOT NULL |
| description | Text | default "" |
| source_type | String | default "text" |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

### knowledge_chunks
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| knowledge_id | Integer | FK -> knowledge.id, ON DELETE CASCADE, NOT NULL, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| chunk_index | Integer | default 0 |
| content | Text | NOT NULL |
| embedding | JSON | (array de floats para busca semantica) |
| tokens | Integer | default 0 |
| created_at | DateTime(timezone) | |

## Relacionamentos

```
Company 1──N User
Company 1──1 CompanyConfig
Company 1──N Customer
Company 1──N Workflow
Company 1──N Conversation
Company 1──N Execution
Company 1──N PendingFlow

Customer 1──N Conversation
Conversation 1──N Message
Workflow 1──N Execution
Execution 1──N PendingFlow
```

## Migrations

> Ver nota no topo: a criacao do schema base e via `create_all` automatico no
> boot do backend. As migrations Alembic existem na infraestrutura, mas NAO sao
> usadas para gerar o schema base.

```bash
# Alembic NAO cria as tabelas base deste projeto (schema vazio de base)
alembic upgrade head

# (raro) Gerar nova migracao Alembic adicional/idempotente
alembic revision --autogenerate -m "descricao"
```

## Criacao das tabelas (automatica no boot — nao e necessario rodar manual)

O `lifespan` em `app/main.py` chama `Base.metadata.create_all` ao iniciar o
backend (dev e producao). **Na primeira subida, o banco sobe com todas as
tabelas.** Para conferir (opcional):

```bash
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

Tabelas esperadas: `companies, company_configs, users, customers, conversations,
conversation_transfers, messages, workflows, executions, pending_flows, knowledge, knowledge_chunks`
(mais possivelmente `alembic_version`, inofensivo). `password_reset_tokens` passa a
existir automaticamente no boot seguinte ao deploy (o `create_all` do `lifespan` em
`app/main.py` cria somente as tabelas ainda inexistentes).
