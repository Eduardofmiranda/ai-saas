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
forma idempotente; `0002` a `0016` evoluem as tabelas. Bancos existentes que
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
| is_platform_admin | Boolean | default False — acesso ao painel `/plataforma` |

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

### business_hours
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL, unique, index |
| timezone | String | default "America/Sao_Paulo" |
| enabled | Boolean | default False |
| schedule | Text | JSON `{"mon": ["09:00","18:00"], ...}`; dia sem janela = fechado |
| message | Text | mensagem automatica fora do horario |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

**Implementado (migration `0012_business_hours`).** Sem registro ou com
`enabled` desligado → aberto 24/7. Config incompleta (nenhum dia com janela
valida) → aberto. Janela que cruza a meia-noite (ex.: `["18:00","02:00"]`) e
suportada (chave do dia = dia em que o turno comeca).

### agenda_config
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL, unique, index |
| enabled | Boolean | default False — liga janela de horarios da agenda |
| timezone | String | default "America/Sao_Paulo" |
| schedule | Text | JSON `{"mon": ["08:00","12:00"], ...}`; dia sem janela = fechado |
| slot_duration | Integer | minutos (default 30) |
| min_advance | Integer | minutos minimos antes do inicio (default 60) |
| blocked | Text | JSON `[{"date":"YYYY-MM-DD","start":"09:00","end":"10:00"}]` — periodos bloqueados |
| confirmation_message | Text | mensagem enviada apos a confirmacao do cliente |
| confirmation_required | Boolean | default True — criacao provisoria (2 passos) pela IA |
| confirmation_expiry_hours | Integer | horas para expirar provisorio sem resposta (default 24; 0 = nunca) |
| confirmation_request_message | Text | pedido de confirmacao (placeholders `{nome}`/`{servico}`/`{data}`/`{horario}`) |
| reminders_enabled | Boolean | default False — envia lembretes automaticos |
| reminder_hours | Text | JSON `[24, 1]` — horas de antecedencia dos lembretes |
| reminder_message | Text | texto do lembrete (placeholders iguais) |
| whatsapp_number | String | numero do WhatsApp vinculado a instancia da Secretaria IA |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

**Implementado (migration `0013_agenda`); campos de confirmação/lembretes na
migration `0014_agenda_confirmation`.** Sem registro ou com `enabled`
desligado → nao gera horarios. Conflito/bloqueio/fora-de-janela/minimo de
antecedencia são validados no servico `agenda_service` (`app/services/agenda.py`)
antes de gravar.

### appointments
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| customer_id | Integer | FK -> customers.id, nullable, index |
| customer_name | String | nome livre (ex.: via WhatsApp sem customer) |
| phone | String | NOT NULL |
| status | String | `scheduled` / `awaiting_confirmation` / `confirmed` / `completed` / `canceled` (default scheduled, index) |
| date | String | `YYYY-MM-DD` (fuso da empresa), index |
| start_time | String | `HH:MM`, NOT NULL |
| end_time | String | `HH:MM`, NOT NULL |
| service | String | tipo do compromisso |
| notes | Text | observacoes |
| origin | String | `manual` / `whatsapp` / `workflow` (default manual) |
| created_by_user_id | Integer | FK -> users.id, nullable |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

**Implementado (migration `0013_agenda`).** Valores de `date`/`start_time`/
`end_time` são gravados como string no fuso da empresa (a IA da Fase 8.6
converte datas relativas para o fuso antes de chamar o servico).

### appointment_events
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| appointment_id | Integer | FK -> appointments.id, NOT NULL, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| action | String | `created` / `updated` / `rescheduled` / `canceled` |
| actor_type | String | `user` / `system` / `workflow` (default user) |
| user_id | Integer | nullable |
| user_name | String | nullable |
| details | Text | JSON com resumo da mudanca |
| created_at | DateTime(timezone) | |

**Implementado (migration `0013_agenda`).** Historico de auditoria de cada
compromisso; cada criacao/alteracao/cancelamento gera um registro.

### pending_appointment_actions
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL, index |
| appointment_id | Integer | FK -> appointments.id, NOT NULL, index |
| phone | String | NOT NULL, index — telefone do dono do compromisso |
| action | String | `reschedule` / `cancel` |
| payload | Text | JSON — campos da remarcacao (`fields`) ou `{"reason": ...}` |
| notified | Integer | default 0 — 1 depois que o pedido foi enviado via WhatsApp |
| created_at | DateTime(timezone) | |

**Implementado (migration `0016_pending_appointment_actions`).** Com
`confirmation_required` ativo, remarcar/cancelar via tools da IA ficam pendentes
do consentimento do cliente: o compromisso original permanece inalterado ate o
cliente responder CONFIRMAR (efetiva) ou CANCELAR (descarta). Pendencias
expiram em `confirmation_expiry_hours` (tarefa `expire_unconfirmed_appointments`).

### departments
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| company_id | Integer | FK -> companies.id, NOT NULL |
| name | String | NOT NULL |
| description | Text | default "" |
| is_active | Boolean | default True |
| created_at | DateTime(timezone) | |
| updated_at | DateTime(timezone) | |

**Implementado (migration `0010_departments`).** Setores da empresa para
encaminhamento de conversas.

### platform_ai_providers
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| provider | String | UNIQUE (ex.: groq, openai, deepseek) |
| model | String | modelo padrao |
| api_key | String | criptografado com Fernet |
| base_url | String | URL base do provedor |
| enabled | Boolean | default True |

**Implementado (migration `0007_platform_admin`).** Credenciais globais de IA
gerenciadas pelo operador da plataforma.

### user_ai_configs
| Coluna | Tipo | Constraints |
|--------|------|------------|
| id | Integer | PK, index |
| user_id | Integer | FK -> users.id, UNIQUE |
| allowed_providers | Text | JSON com provedores permitidos |
| default_provider | String | provedor padrao do usuario |
| default_model | String | modelo padrao do usuario |
| created_by | Integer | FK -> users.id (quem criou a politica) |

**Implementado (migration `0008_user_ai_config`).** Politica de IA por usuario.
Resolucao: usuario -> empresa -> plataforma -> .env.

## Relacionamentos

```
Company 1──N User
Company 1──1 CompanyConfig
Company 1──1 BusinessHours
Company 1──1 AgendaConfig
Company 1──N Customer
Company 1──N Department
Company 1──N Workflow
Company 1──N Conversation
Company 1──N Execution
Company 1──N PendingFlow
Company 1──N Appointment
Company 1──N PendingAppointmentAction

Customer 1──N Conversation
Conversation 1──N Message
Workflow 1──N Execution
Execution 1──N PendingFlow
Appointment 1──N AppointmentEvent
Appointment 1──N PendingAppointmentAction
User 1──1 UserAIConfig
```

## Migrations

**Implementado:** Alembic controla todo schema de producao. Em bancos novos,
`0001_initial_schema` cria a base; `0002` a `0016` aplicam as evolucoes. As
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
