# 06 — Banco de Dados

## Tecnologia

- **Producao**: PostgreSQL 16 (**local no Docker** — container `ai-saas-postgres`)
- **Desenvolvimento**: SQLite (automatico quando `DATABASE_URL` nao configurado)
- **ORM**: SQLAlchemy
- **Criacao do schema**: **SQLAlchemy `Base.metadata.create_all`** (mecanismo principal)

> **Como o schema e criado de fato (confirmado em 03/09/2026):**
>
> 1. As **tabelas base** (`companies`, `users`, `workflows`, `executions`, etc.)
>    sao criadas por **`Base.metadata.create_all`** via `app/create_tables.py`.
>    O `alembic upgrade head` **NAO** cria essas tabelas.
> 2. Existem migrations Alembic **adicionais e idempotentes** em
>    `alembic/versions/`:
>    - `0002_pending_flows.py` — adiciona `pending_flows` (so cria se nao existir)
>    - `0003_knowledge.py` — adiciona `knowledge` e `knowledge_chunks`
>
>    Elas **assumem que as tabelas base ja existem** e apenas garantem que as
>    tabelas `pending_flows`/`knowledge`/`knowledge_chunks` existam (checando com
>    `inspect` e retornando sem erro se ja existirem). Na pratica sao
>    **supérfluas** quando o `create_all` e usado, pois ele ja cria tudo.
>
> **Procedimento recomendado apos subir o docker (cria todas as tabelas):**
> ```bash
> docker compose exec backend python -c "from app.create_tables import *"
> ```
> (Opcional e inofensivo, roda tambem o `alembic upgrade head` depois.)
>
> **Historico do deploy real (03/09/2026):** na VPS, `alembic upgrade head`
> criou apenas a tabela `alembic_version` e **nao** as tabelas base — por isso o
> `create_all` e o caminho que de fato cria as tabelas. As tabelas foram
> confirmadas criadas apos rodar o `create_all`.
>
> **Supabase:** abandonado como banco principal devido ao problema de IPv6
> (a direct connection resolve so IPv6 e VPS sem rede IPv6 nao conecta). O
> deploy padrao usa **Postgres local**.

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
| status | String | default "open" |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

### messages
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| conversation_id | Integer | FK -> conversations.id, NOT NULL |
| sender_type | String | NOT NULL ("customer" ou "bot") |
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

> Ver nota no topo: a criacao do schema e via `create_all`, nao Alembic.
> Os passos abaixo de Alembic existem na infraestrutura, mas NAO sao usados
> para gerar o schema atual.

```bash
# Rodar migracoes (NAO cria as tabelas deste projeto - schema vazio)
alembic upgrade head

# Criar nova migracao
alembic revision --autogenerate -m "descricao"
```

## Criacao Manual (Dev / Producao) — O CAMINHO DE FATO

```bash
python -c "from app.create_tables import *"
```

Confirmar tabelas:
```bash
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

Tabelas esperadas: `companies, company_configs, users, customers, conversations,
messages, workflows, executions, pending_flows, knowledge, knowledge_chunks`
(mais possivelmente `alembic_version`, inofensivo).
