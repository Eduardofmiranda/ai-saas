# 00 — Indice Tecnico

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
| Banco de dados | PostgreSQL (producao) / SQLite (dev) | 16 |
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
│   ├── create_tables.py          # Criacao manual de tabelas
│   ├── database/                 # Conexao com o banco
│   │   ├── database.py           # Engine, SessionLocal, Base
│   │   └── session.py            # Dependency get_db
│   ├── models/                   # Models SQLAlchemy
│   │   ├── company.py
│   │   ├── company_config.py
│   │   ├── user.py
│   │   ├── customer.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── workflow.py
│   │   ├── execution.py
│   │   └── pending_flow.py
│   ├── schemas/                  # Schemas Pydantic
│   │   ├── auth_schema.py
│   │   ├── company_schema.py
│   │   ├── config_schema.py
│   │   ├── conversation_schema.py
│   │   ├── customer_schema.py
│   │   ├── dashboard_schema.py
│   │   ├── execution_schema.py
│   │   ├── message_schema.py
│   │   └── workflow_schema.py
│   ├── routers/                  # Endpoints da API
│   │   ├── auth_router.py
│   │   ├── company_router.py
│   │   ├── config_router.py
│   │   ├── conversation_router.py
│   │   ├── customer_router.py
│   │   ├── dashboard_router.py
│   │   ├── message_router.py
│   │   ├── webhook_router.py
│   │   └── workflow_router.py
│   ├── services/                 # Logica de negocio
│   │   ├── config_service.py
│   │   ├── conversation_service.py
│   │   ├── deps.py
│   │   ├── evolution.py
│   │   ├── field_crypto.py
│   │   ├── llm.py
│   │   ├── security.py
│   │   ├── workflow_engine.py
│   │   └── nodes/
│   │       ├── context.py
│   │       └── registry.py
│   └── tasks/                    # Celery workers
│       ├── celery_app.py
│       └── workflow_tasks.py
├── tests/                        # Testes automatizados
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_config.py
│   ├── test_crypto.py
│   ├── test_nodes_registry.py
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
│   │       ├── Login.jsx
│   │       ├── Home.jsx
│   │       └── Editor.jsx
│   ├── package.json
│   ├── vite.config.js
│   ├── nginx.conf
│   └── index.html
├── alembic/                      # Migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0002_pending_flows.py
├── docker-compose.yml
├── docker-compose.override.yml
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
| Arquivos Python (backend) | ~30 |
| Arquivos JSX/JS (frontend) | ~8 |
| Arquivos de configuracao | ~10 |
| Arquivos Docker | 4 |
| Arquivos de teste | 6 |
| Arquivos de documentacao | 20 |
| **Total aproximado** | **~75** |
