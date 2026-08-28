# AI SaaS — Atendimento IA no WhatsApp

API FastAPI multi-tenant: cada cliente (empresa) configura o próprio provedor de IA
e a própria Evolution API (WhatsApp). Troca de IA sem tocar em código (adapter OpenAI-compatível).

## Stack
- **Backend:** FastAPI + Uvicorn + SQLAlchemy + Pydantic v2
- **Frontend:** Vite + React 19 + React Flow (@xyflow/react) + React Router
- Autenticação JWT (bcrypt + python-jose)
- Provedores de IA: groq (padrão) | openai | deepseek | mistral | ollama | mock
- WhatsApp via Evolution API
- **Motor de workflows visual (estilo n8n):** grafo JSON `{nodes, edges}` no campo `data`; execução assíncrona registrada em `executions`.

## Como rodar (local)

### Backend
```powershell
# 1) criar as tabelas
venv\Scripts\python.exe app\create_tables.py

# 2) subir a API
venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000

# Swagger interativo: http://localhost:8000/docs
```

### Frontend
```powershell
cd frontend
npm install
npm run dev
# abra http://localhost:5173  (login/registro -> painel -> editor visual)
```
Necessário criar pelo menos uma conta pelo `/auth/register` (ou pela tela "Criar conta").

### Teste rápido sem servidor (1 comando)
```powershell
venv\Scripts\python.exe run_test.py
```
Cria uma empresa, dispara o pipeline e mostra a resposta da IA salva.
Também há `http_test.py` (testa pela API HTTP real, sobe o uvicorn antes).

## Como acionar a IA real (Groq — barata, tem free tier)
1. Crie uma chave gratuita em https://console.groq.com/keys
2. Antes de rodar acima:
   ```powershell
   $env:TEST_AI_KEY="sua-chave-groq"
   $env:TEST_AI_PROVIDER="groq"
   $env:TEST_AI_MODEL="llama-3.3-70b-versatile"
   ```
   Ou edite `.env` e preencha `DEFAULT_AI_PROVIDER`, `DEFAULT_AI_MODEL`, `DEFAULT_AI_API_KEY`.

## Como enviar de verdade no WhatsApp (Evolution API)
1. Tenha uma Evolution API rodando (http://IP:8080) e uma instância conectada.
2. Preencha no `.env`:
   ```
   EVOLUTION_BASE_URL=http://SEU_IP_EVOLUTION:8080
   EVOLUTION_API_KEY=chave-da-evolution
   EVOLUTION_INSTANCE=nome-da-instancia
   ```
3. Configure o webhook da instância na Evolution para:
   `POST http://SEU_SERVIDOR:8000/webhook/whatsapp/{company_id}` (o id da sua empresa).
4. Cada empresa pode ter dados próprios via `PATCH /config/` (endpoint protegido por JWT).

## Fluxo
```
WhatsApp → Evolution webhook → POST /webhook/whatsapp/{company_id}
        → deduplica/registra mensagem → busca/cria cliente e conversa
        → LLM gera resposta (provider configurado) → Evolution envia → salva tudo
```

## Endpoints principais
| Método | Rota | Descrição |
|---|---|---|
| POST | /auth/register | Cria empresa + usuário admin |
| POST | /auth/login | Retorna JWT |
| GET/PATCH | /config/ | Config de IA + Evolution da empresa (protegido) |
| POST | /webhook/whatsapp/{company_id} | Webhook Evolution |
| GET | /conversations/ | Conversas |
| GET | /messages/conversation/{id} | Mensagens |
| GET | /dashboard/ | Contadores |
| GET | /workflows/node-types | Lista os tipos de nó disponíveis (paleta do editor) |
| GET/POST | /workflows/ | Lista / cria fluxos |
| GET/PATCH/DELETE | /workflows/{id} | Lê / edita / exclui fluxo |
| POST | /workflows/{id}/run | Executa o fluxo com payload de teste (retorna a execução) |
| GET | /workflows/{id}/executions | Histórico de execuções |

## Motor de workflows (editor visual)
- O grafo é salvo em `workflow.data` como `{"nodes": [...], "edges": [...]}`.
- **Nós:** `trigger_message`, `trigger_webhook`, `ai`, `set`, `condition`, `delay`, `http`, `whatsapp_send`, `filter`, `log`.
- **Condição:** o nó `condition` tem 2 saídas — as edges usam `sourceHandle: "true"` e `"false"`.
- **Variáveis/expressões:** use `{{ data.campo }}` em prompts/valores (ex: `{{ data.message.text }}`).
- Cada empresa herda os defaults do `.env` (`DEFAULT_AI_*`); campos vazios no `/config/` usam esses defaults.

## Arquivos-chave
- `app/services/llm.py` — provedores de IA (adicione novos aqui)
- `app/services/evolution.py` — cliente Evolution + parser do webhook
- `app/services/workflow_engine.py` — executor do grafo
- `app/services/nodes/registry.py` — catálogo de nós (metadata + lógica)
- `app/services/conversation_service.py` — pipeline de atendimento (legado)
- `app/models/workflow.py` / `execution.py` — modelos do motor
- `app/routers/workflow_router.py` — API CRUD + run + execuções
- `frontend/` — aplicação React (login, painel, editor React Flow)
- `app/models/company_config.py` — config por empresa
- `.env` — defaults globais (IA + Evolution + banco)
