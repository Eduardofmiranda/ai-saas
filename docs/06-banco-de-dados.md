# 06 — Banco de Dados

## Tecnologia

- **Producao (VPS):** **Supabase PostgreSQL**, definido por `DATABASE_URL`.
- **Desenvolvimento/testes locais:** SQLite, normalmente `sqlite:///./aissaas.db`
  ou banco em memoria nas suites de teste.
- **ORM:** SQLAlchemy.
- **Schema de producao:** Alembic. O container `backend` executa `alembic upgrade head`
  antes de iniciar Uvicorn; workers aguardam o health check do backend.

### Ciclo de schema

**Implementado:** a migration `0001_initial_schema` descreve o schema base de
forma idempotente; `0002` a `0006` evoluem as tabelas. Bancos existentes que
ja estavam em `0005_password_reset_tokens` avancam normalmente para `0006` sem
recriar nem apagar tabelas.

**Local:** SQLite pode criar o schema inicial no lifespan para facilitar testes.
Ao reutilizar um banco local, execute `alembic upgrade head` antes de iniciar o
backend para receber novas colunas/tabelas. `Base.metadata.create_all` nao e a
fonte de verdade de alteracoes estruturais.

**Producao:** nao execute `create_all` nem altere o Supabase manualmente. O
procedimento aprovado e atualizar o codigo, revisar `.env`, recriar backend e
worker e deixar Alembic aplicar a revisao pendente. Antes e depois, confirme a
paridade real:

```bash
# VPS: nunca confie apenas no .env em disco
docker compose exec backend printenv DATABASE_URL
docker compose exec backend alembic current
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import text; print(dict(engine.connect().execute(text('select current_database(), inet_server_addr()')).mappings().first()))"
```

### pgvector para Knowledge

**Implementado condicionalmente:** `0006_pgvector_knowledge` e executada no
PostgreSQL apenas quando `ENABLE_PGVECTOR=true`. Ela habilita a extensao
`vector`, preserva a coluna JSON legada, adiciona metadados de modelo/dimensao,
converte vetores existentes e cria indice HNSW parcial para
`DEFAULT_EMBEDDING_DIMENSIONS` (1536 por padrao). SQLite continua no fallback
JSON para os testes locais.

Se a extensao nao puder ser habilitada no Supabase, a migration falha de forma
explícita. Nesse caso, mantenha `ENABLE_PGVECTOR=false`, investigue permissao/
extensao no Supabase e nao marque a revisao como aplicada manualmente.
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
| email | String | `0011_customer_lead_fields` |
| company | String | idem |
| city | String | idem |
| notes | Text | idem |

Os campos `email`, `company`, `city` e `notes` sao preenchidos pelo node
`capture_lead` (ver 09-nodes.md). Colunas adicionadas na migration
`0011_customer_lead_fields`.

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
| embedding | JSON | fallback local e compatibilidade com dados legados |
| embedding_model | String | modelo que gerou o vetor |
| embedding_dimensions | Integer | dimensao do vetor |
| embedding_vector | vector | somente PostgreSQL/Supabase com `ENABLE_PGVECTOR=true` |
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

**Implementado:** Alembic controla todo schema de producao. Em bancos novos,
`0001_initial_schema` cria a base; `0002` a `0006` aplicam as evolucoes. As
migrations sao idempotentes para permitir adocao de bancos legados que antes
foram criados pelo ORM.

```bash
# Local: aplicar evolucoes num banco existente
alembic upgrade head

# VPS: o backend aplica automaticamente antes do Uvicorn
docker compose exec backend alembic current
```

Nao use `alembic revision --autogenerate` sem revisar manualmente o resultado,
especialmente nas tabelas JSON, vetores, FKs e indices.
