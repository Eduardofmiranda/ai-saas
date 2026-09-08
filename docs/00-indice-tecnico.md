# 00 — Indice Tecnico

> ⭐ **Comece por `docs/FATOS-CHAVE.md`** — fixa os fatos principais do projeto
> (banco de producao = Supabase, usuario por cadastro, credenciais, etc.).
>
> 📊 **Estudo de UX:** `docs/20-estudo-painel-mercado.md` — analise de plataformas
> de referencia e proposta de redesenho do painel (Fase 9.0).
>
> 🛠️ **Operacao:** docs/21-checklist-deploy-vps.md — verificacao segura apos deploy na VPS.
> 🔌 **Roadmap de nodes:** `docs/22-catalogo-nodes-roadmap.md` — catálogo planejado, prioridades e critérios de segurança.
> 📅 **Agenda avancada:** `docs/23-agenda-confirmacao-lembretes.md` — confirmacao em 2 passos,
> lembretes e integracao com calendarios externos (Google/Outlook).

## Resumo do Projeto

**Nome:** FlowAI (AI SaaS - Atendimento WhatsApp)
**Inspiracao:** n8n (workflow automation)
**Objetivo:** Plataforma de automacao de atendimento ao cliente via WhatsApp com IA, configuravel por empresa (multi-tenant).

## Stack Tecnologica

| Camada | Tecnologia | Versao |
|--------|-----------|--------|
| Frontend | React | 19.2.8 |
| Editor visual | @xyflow/react (React Flow) | 12.11.5 |
| Roteamento frontend | react-router-dom | 7.18.2 |
| Bundler | Vite | 8.2.2 |
| Backend | FastAPI (Python) | — |
| Servidor | Uvicorn | — |
| ORM | SQLAlchemy | — |
| Banco de dados | **Supabase** (PostgreSQL, producao) / SQLite (dev) | 16 |
| Cache/Filas | Redis | 7 |
| Workers | Celery | — |
| Agendador Celery | RedBeat | — |
| Migrations | Alembic | — |
| Autenticacao | JWT (PyJWT) + bcrypt | — |
| Criptografia | cryptography (Fernet/AES) | — |
| HTTP Client | httpx | — |
| Containerizacao | Docker + Docker Compose | — |
| Frontend server | nginx (producao) | alpine |

## Estrutura de Diretorios

```
ai-saas/
├── app/                          # Backend (FastAPI)
│   ├── main.py                   # Entry point da API
│   ├── config.py                 # Leitura de variaveis de ambiente
│   ├── create_tables.py          # Cria tabelas via Base.metadata.create_all
│   ├── database/                 # Conexao com o banco
│   │   ├── database.py           # Engine, SessionLocal, Base
│   │   └── session.py            # Dependency get_db
│   ├── models/                   # Models SQLAlchemy
│   │   ├── __init__.py
│   │   ├── agenda_config.py
│   │   ├── appointment.py
│   │   ├── appointment_event.py
│   │   ├── business_hours.py
│   │   ├── company.py
│   │   ├── company_config.py
│   │   ├── conversation.py
│   │   ├── conversation_transfer.py
│   │   ├── customer.py
│   │   ├── department.py
│   │   ├── execution.py
│   │   ├── knowledge.py
│   │   ├── knowledge_chunk.py
│   │   ├── message.py
│   │   ├── password_reset_token.py
│   │   ├── pending_appointment_action.py
│   │   ├── pending_flow.py
│   │   ├── platform_ai_provider.py
│   │   ├── user.py
│   │   ├── user_ai_config.py
│   │   └── workflow.py
│   ├── schemas/                  # Schemas Pydantic
│   │   ├── auth_schema.py
│   │   ├── company_schema.py
│   │   ├── config_schema.py
│   │   ├── conversation_schema.py
│   │   ├── conversation_transfer_schema.py
│   │   ├── customer_schema.py
│   │   ├── dashboard_schema.py
│   │   ├── execution_schema.py
│   │   ├── knowledge_schema.py
│   │   ├── message_schema.py
│   │   ├── user_schema.py
│   │   └── workflow_schema.py
│   ├── routers/                  # Endpoints da API (~91 endpoints)
│   │   ├── agenda_router.py      # /agenda/*
│   │   ├── auth_router.py        # /auth/*
│   │   ├── company_router.py     # /companies/*
│   │   ├── config_router.py      # /config/* (incl. whatsapp, business-hours, ai)
│   │   ├── conversation_router.py# /conversations/*
│   │   ├── customer_router.py    # /customers/*
│   │   ├── dashboard_router.py   # /dashboard/*
│   │   ├── department_router.py  # /departments/*
│   │   ├── knowledge_router.py   # /knowledge/*
│   │   ├── message_router.py     # /messages/*
│   │   ├── platform_admin_router.py # /platform-admin/*
│   │   ├── template_router.py    # /templates/*
│   │   ├── users_router.py       # /users/*
│   │   ├── webhook_router.py     # /webhook/*
│   │   └── workflow_router.py    # /workflows/*
│   ├── services/                 # Logica de negocio
│   │   ├── agenda.py             # Servico de agenda (CRUD + slots + advisory lock)
│   │   ├── agenda_confirmation.py# Confirmacao 2 passos + lembretes
│   │   ├── agenda_tools.py       # Tools de function calling para IA
│   │   ├── business_hours.py     # Horario de atendimento
│   │   ├── config_service.py
│   │   ├── conversation_service.py
│   │   ├── deps.py
│   │   ├── email_service.py
│   │   ├── embedding.py
│   │   ├── evolution.py
│   │   ├── field_crypto.py
│   │   ├── llm.py
│   │   ├── platform_access.py
│   │   ├── platform_bootstrap.py
│   │   ├── platform_ai_provider_service.py
│   │   ├── rate_limit.py
│   │   ├── security.py           # JWT (PyJWT) + bcrypt
│   │   ├── templates.py          # Templates de workflow
│   │   ├── vector_store.py       # pgvector + fallback JSON
│   │   ├── workflow_engine.py
│   │   ├── workflow_validation.py
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── context.py
│   │       ├── rag_node.py
│   │       └── registry.py
│   └── tasks/                    # Celery workers
│       ├── __init__.py
│       ├── agenda_tasks.py       # Expiracao + lembretes da agenda
│       ├── celery_app.py
│       └── workflow_tasks.py
├── tests/                        # Testes automatizados (300+)
│   ├── conftest.py
│   ├── test_agenda.py
│   ├── test_agenda_confirmation.py
│   ├── test_agenda_concurrency.py
│   ├── test_agenda_pending_actions.py
│   ├── test_agenda_security.py
│   ├── test_agenda_tools.py
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_crypto.py
│   ├── test_evolution.py
│   ├── test_handoff.py
│   ├── test_inbox.py
│   ├── test_knowledge.py
│   ├── test_nodes_registry.py
│   ├── test_password.py
│   ├── test_security_commit.py
│   ├── test_sprint3_nodes.py
│   ├── test_users.py
│   └── test_workflow_engine.py
├── frontend/                     # Frontend (React)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api.js
│   │   ├── index.css
│   │   ├── components/
│   │   │   └── Header.jsx
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   └── pages/
│   │       ├── Account.jsx
│   │       ├── Admin.jsx
│   │       ├── Agenda.jsx
│   │       ├── AI.jsx
│   │       ├── Conversations.jsx
│   │       ├── Dashboard.jsx
│   │       ├── Departments.jsx
│   │       ├── Editor.jsx
│   │       ├── Home.jsx
│   │       ├── Knowledge.jsx
│   │       ├── Leads.jsx
│   │       ├── Login.jsx
│   │       ├── PlatformAdmin.jsx
│   │       ├── ResetPassword.jsx
│   │       └── WhatsApp.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── index.html
├── alembic/                      # Migrations (adicionais/idempotentes; ver 06-banco-de-dados.md)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0001_initial_schema.py
│       ├── 0002_pending_flows.py
│       ├── 0003_knowledge.py
│       ├── 0004_conversation_transfers.py
│       ├── 0005_password_reset_tokens.py
│       ├── 0006_pgvector_knowledge.py
│       ├── 0007_platform_admin.py
│       ├── 0008_user_ai_config.py
│       ├── 0009_workflow_user_id.py
│       ├── 0010_departments.py
│       ├── 0011_customer_lead_fields.py
│       ├── 0012_business_hours.py
│       ├── 0013_agenda.py
│       ├── 0014_agenda_confirmation.py
│       ├── 0015_agenda_slot_index.py
│       └── 0016_pending_appointment_actions.py
├── docker-compose.yml
├── docker-compose.dev.yml
├── docker-compose.evolution.yml
├── Dockerfile.backend
├── Dockerfile.frontend
├── requirements.txt
├── alembic.ini
├── .env.example
└── deploy-vps.sh
```

## Contagem de Arquivos

| Categoria | Quantidade |
|-----------|-----------|
| Arquivos Python (backend, app/) | ~60 |
| Arquivos de teste (tests/) | ~20 |
| Arquivos JSX/JS (frontend) | ~15 |
| Arquivos de configuracao | ~10 |
| Arquivos Docker | 5 |
| Arquivos de documentacao (docs/ + raiz) | ~30 |
| Migrations (alembic/versions/) | 15 |
| **Total aproximado** | **~150** |
