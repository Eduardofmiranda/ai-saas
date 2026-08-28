# 02 — Arquitetura

## Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────┐
│                      FRONTEND                           │
│  React 19 + React Flow + Vite                           │
│  ┌──────────┐ ┌──────────┐ ┌──────────────────────────┐ │
│  │  Login   │ │   Home   │ │   Editor (React Flow)    │ │
│  └──────────┘ └──────────┘ └──────────────────────────┘ │
│                    │ API (fetch)                         │
└────────────────────┼────────────────────────────────────┘
                     │
┌────────────────────┼────────────────────────────────────┐
│                    ▼        BACKEND (FastAPI)            │
│  ┌─────────────────────────────────────────────────┐    │
│  │  Routers (API REST)                             │    │
│  │  auth | company | config | customer |           │    │
│  │  conversation | message | dashboard |           │    │
│  │  webhook | workflow                             │    │
│  └──────────────────┬──────────────────────────────┘    │
│                     │                                   │
│  ┌──────────────────▼──────────────────────────────┐    │
│  │  Services                                       │    │
│  │  config_service | conversation_service |        │    │
│  │  security | deps | field_crypto | llm |         │    │
│  │  evolution | workflow_engine                    │    │
│  └──────────────────┬──────────────────────────────┘    │
│                     │                                   │
│  ┌──────────────────▼──────────────────────────────┐    │
│  │  Workflow Engine                                │    │
│  │  registry (11 nodes) | context | engine         │    │
│  └──────────────────┬──────────────────────────────┘    │
│                     │                                   │
│  ┌──────────────────▼──────────────────────────────┐    │
│  │  Celery Workers                                 │    │
│  │  workflow_tasks | celery_app                    │    │
│  └─────────────────────────────────────────────────┘    │
│                                                         │
└────────────────────┬────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
   ┌─────────┐ ┌─────────┐ ┌──────────────┐
   │ Postgres│ │  Redis  │ │  Evolution   │
   │   (DB)  │ │(Queue)  │ │  API (WA)    │
   └─────────┘ └─────────┘ └──────────────┘
                                     │
                                     ▼
                              ┌─────────────┐
                              │  WhatsApp   │
                              │  (Clientes) │
                              └─────────────┘
```

## Fluxo de uma Mensagem WhatsApp

```
1. Cliente envia msg no WhatsApp
2. Evolution API envia webhook para POST /webhook/whatsapp/{company_id}
3. webhook_router extrai: phone, text, wa_message_id
4. background_tasks.add_task(_run_pipeline, ...)
5. handle_incoming_workflow():
   a. Deduplica (wa_message_id)
   b. Encontra/cria Customer
   c. Encontra/cria Conversation (open)
   d. Salva Message (customer)
   e. Verifica PendingFlow (fluxo pausado?)
      - SIM: resume_workflow() → continua de onde parou
      - NAO: busca Workflow ativo (trigger_type=message) → execute_workflow()
6. Workflow Engine:
   a. Entra no trigger node
   b. Segue as edges executando nodes
   c. Se encontrar wait_until_message → salva PendingFlow, status=waiting
   d. Se encontrar ai → chama LLM, salva resposta no banco
   e. Se encontrar whatsapp_send → envia msg via Evolution
   f. Quando terminar → status=success
7. Resposta volta ao WhatsApp do cliente
```

## Padroes de Design

- **Service Layer**: logica de negocio em `services/`, nao nos routers
- **Dependency Injection**: FastAPI Depends para DB e autenticacao
- **Repository Pattern**: queries no service layer (sem repository explicito)
- **Fat Model**: models com metodos de dominio (set_password, verify_password)
- **Schema Validation**: Pydantic para validacao de entrada/saida
