# 00 — Indice Tecnico

> ⭐ **Comece por `docs/FATOS-CHAVE.md`** — fixa os fatos principais do projeto
> (banco de producao = Supabase, usuario por cadastro, credenciais, etc.).
>
> 📊 **Estudo de UX:** `docs/20-estudo-painel-mercado.md` — analise de plataformas
> de referencia e proposta de redesenho do painel (Fase 9.0).

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
| Autenticacao | JWT (python-jose) + bcrypt | — |
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
│   │   ├── company.py
│   │   ├── company_config.py
│   │   ├── conversation.py
│   │   ├── customer.py
│   │   ├── execution.py
│   │   ├── knowledge.py
│   │   ├── message.py
│   │   ├── pending_flow.py
│   │   ├── user.py
│   │   └── workflow.py
│   ├── schemas/                  # Schemas Pydantic
│   │   ├── auth_schema.py
│   │   ├── company_schema.py
│   │   ├── config_schema.py
│   │   ├── conversation_schema.py
│   │   ├── customer_schema.py
│   │   ├── dashboard_schema.py
│   │   ├── execution_schema.py
│   │   ├── knowledge_schema.py
│   │   ├── message_schema.py
│   │   ├── user_schema.py
│   │   └── workflow_schema.py
│   ├── routers/                  # Endpoints da API
│   │   ├── auth_router.py
│   │   ├── company_router.py
│   │   ├── config_router.py
│   │   ├── conversation_router.py
│   │   ├── customer_router.py
│   │   ├── dashboard_router.py
│   │   ├── knowledge_router.py
│   │   ├── message_router.py
│   │   ├── template_router.py
│   │   ├── users_router.py
│   │   ├── webhook_router.py
│   │   └── workflow_router.py
│   ├── services/                 # Logica de negocio
│   │   ├── config_service.py
│   │   ├── conversation_service.py
│   │   ├── deps.py
│   │   ├── embedding.py
│   │   ├── evolution.py
│   │   ├── field_crypto.py
│   │   ├── llm.py
│   │   ├── security.py
│   │   ├── templates.py
│   │   ├── vector_store.py
│   │   ├── workflow_engine.py
│   │   └── nodes/
│   │       ├── __init__.py
│   │       ├── context.py
│   │       ├── rag_node.py
│   │       └── registry.py
│   └── tasks/                    # Celery workers
│       ├── __init__.py
│       ├── celery_app.py
│       └── workflow_tasks.py
├── tests/                        # Testes automatizados
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_crypto.py
│   ├── test_evolution.py
│   ├── test_knowledge.py
│   ├── test_nodes_registry.py
│   ├── test_sprint3_nodes.py
│   ├── test_users.py
│   └── test_workflow_engine.py
├── frontend/                     # Frontend (React)
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api.js
│   │   ├── index.css
│   │   ├── context/
│   │   │   └── AuthContext.jsx
│   │   └── pages/
│   │       ├── Admin.jsx
│   │       ├── AI.jsx
│   │       ├── Dashboard.jsx
│   │       ├── Editor.jsx
│   │       ├── Home.jsx
│   │       ├── Knowledge.jsx
│   │       ├── Login.jsx
│   │       └── WhatsApp.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── index.html
├── alembic/                      # Migrations (adicionais/idempotentes; ver 06-banco-de-dados.md)
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 0002_pending_flows.py
│       └── 0003_knowledge.py
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
| Arquivos Python (backend, app/) | ~50 |
| Arquivos de teste (tests/) | 10 |
| Arquivos JSX/JS (frontend) | ~10 |
| Arquivos de configuracao | ~10 |
| Arquivos Docker | 5 |
| Arquivos de documentacao (docs/ + raiz) | >20 |
| **Total aproximado** | **~100** |
