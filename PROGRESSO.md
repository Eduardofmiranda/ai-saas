# 🚦 Progresso — FlowAI (AI SaaS - Atendimento WhatsApp)

> Use este documento para acompanhar onde estamos. Marque `[x]` quando concluído.
> Documento de trabalho (não substitui `docs/` técnico — este é o **roadmap/estado**).

---

## FASE 0 — Visão geral ✅
- [x] Plataforma de automação estilo n8n, foco em **atendimento WhatsApp com IA**
- [x] Multi-tenant: cada **empresa** tem sua configuração (IA + Evolution) e seus workflows
- [x] Em produção na VPS (Hostinger, `2.25.122.157`) com **Postgres local do Docker**

---

## FASE 1 — Fundação do Backend ✅
- [x] Auth JWT (register/login, bcrypt, python-jose)
- [x] Config por empresa (GET/PATCH /config/)
- [x] Adaptador multi-provedor de IA (groq/openai/deepseek/mistral/ollama/mock)
- [x] Evolution API (WhatsApp) + webhook `POST /webhook/whatsapp/{company_id}`
- [x] Pipeline de atendimento (`conversation_service`)

## FASE 2 — Motor de Workflows (backend) ✅
- [x] Models: `workflow`, `execution`
- [x] Node catalog + registry (`app/services/nodes/registry.py`)
- [x] Engine (`app/services/workflow_engine.py`) com trigger, edges, `wait_until_message`, `on_error`
- [x] Router CRUD + run + executions
- [x] Testado E2E: trigger → IA → WhatsApp → `success` com resposta real

## FASE 3 — Frontend React (editor visual) ✅
- [x] Scaffold Vite + React 19 + React Flow + React Router
- [x] Login / registro (consome /auth/*)
- [x] Painel (lista de workflows, criar, excluir)
- [x] Editor visual (paleta, canvas, conexões, inspector)
- [x] Salvar (PATCH), Rodar (POST /run), exibir resultado
- [x] CORS backend → frontend
- [x] Build de produção passa
- [x] Página **WhatsApp** com status de conexão + config Evolution por empresa
- [x] Páginas **Conhecimento** (RAG) e **Administração**
- [x] **Componente `Header`** reutilizado em todas as páginas (elimina duplicação)
- [x] **Dashboard pós-login** com KPIs por empresa (fluxos, conversas, execuções)
- [x] **Gerenciador de IA** (`/ai`) — configuração de provedor, modelo, system prompt com presets
- [x] Estilos CSS completos (kpi-grid, wa-banner, exec-bar, ai-config, role-chip, etc.)

## FASE 3.1 — Modo Gerenciador de IA ✅
- [x] Página `/ai` com toggle liga/desliga da IA
- [x] Seleção de provedor (Groq, OpenAI, DeepSeek, Mistral, Ollama)
- [x] Seleção de modelo por provedor
- [x] Editor de system prompt com 4 presets de personalidade:
  - [x] Atendente Amigável (cordial, humano)
  - [x] Vendedor Consultivo (consultivo, não pressiona)
  - [x] Suporte Técnico (preciso, passos numerados)
  - [x] Recepcionista Virtual (acolhe, direciona)
- [x] Salva via `PATCH /config/` (backend existente)
- [x] Build validado (190 módulos, sem erros)

## FASE 4 — Deploy em Produção ✅ (concluído e validado)
- [x] Dockerfile.backend / Dockerfile.frontend (multi-stage)
- [x] docker-compose.yml (postgres, redis, backend, celery-worker, celery-beat, frontend)
- [x] **Postgres local do Docker** como banco de produção (Supabase abandonado por IPv6)
- [x] Evolution API em **compose separado** (`docker-compose.evolution.yml`), mesma rede do backend, porta 8080
- [x] **create_all automático no boot** (`lifespan` em `app/main.py`) — não depende de Alembic/manual
- [x] Celery + Redis para tarefas assíncronas
- [x] Deploy validado na VPS: empresa, WhatsApp conectado, **criação de tabelas automática no boot**
- [x] Documentação: `CreateVPS.md`, `VPS-SETUP.md`, `docs/` alinhados ao código

## FASE 5 — Integração WhatsApp PONTA A PONTA ✅
- [x] Número conectado via Evolution (`flowai`, `state: open`)
- [x] Webhook configurado → `POST /webhook/whatsapp/1`
- [x] Workflow `Atendimento Basico (IA)` ativo (trigger_message → ai → whatsapp_send → wait)
- [x] Respondendo sozinho com **memória de conversa** (16+ execuções `success`)
- [x] Config da empresa com Evolution + fallback para `.env` (Groq)

---

## FASE 6 — UX do consumidor / QR na tela ⏳ (PRÓXIMA — prioridade)
**Objetivo:** o usuário final conecta o WhatsApp **dentro da aplicação**, sem precisar do manager `:8080/manager` nem curl.

- [ ] Endpoint backend `POST /config/whatsapp/connect` — busca o QR via Evolution (base64) **sem expor a API key no browser**
- [ ] Endpoint backend `POST /config/whatsapp/disconnect` (opcional)
- [ ] UI na página WhatsApp: botão **"Conectar WhatsApp"**
- [ ] Renderização do **QR Code** (imagem base64) na tela
- [ ] **Auto-renovação do QR** (expira em ~20–60s) com polling/refresh
- [ ] Refresh automático do status para "Conectado" após escanear

## FASE 7 — Limitador de IA por empresa/WhatsApp ⏳ (NOVA IDEIA — configurável)
**Objetivo:** tornar o atendimento com IA **completamente configurável para cada ramo/empresa** (e por WhatsApp/número conectado), com **limites de uso** para controlar custo/comportamento.

- [ ] Modelo de dados p/ limites por empresa (ex.: coluna JSON/Tabela `ai_limits`)
- [ ] Limites configuráveis por empresa/WhatsApp:
  - [ ] **Limite de mensagens** (ex.: X mensagens/dia ou por conversa)
  - [ ] **Limite de custo/tokens** (ex.: teto de tokens/sessão, custo máximo)
  - [ ] **Período/janela** (ex.: horário de atendimento, dia da semana)
  - [ ] **Timeout/retry** por chamada de IA
  - [ ] **Fallback** quando o limite é atingido (ex.: mensagem padrão, encerrar, avisar humano)
- [ ] Aplicar limites no pipeline (`conversation_service`/`context.ask_ai`) e nos nodes `ai`/`ai_rag`
- [ ] Configura por **ramo/empresa** e por **WhatsApp conectado**
- [ ] UI de configuração dos limites (página Admin/Configuração)
- [ ] Expor status de uso/consumo (dashboard)

> **Definição**: cada empresa/ramo tem parâmetros próprios de atendimento. Ex. uma
> loja pode querer limite de 50 msgs/dia com horário 8h–18h; outra, atendimento 24h
> com teto de tokens. Isto deverá ser configurável pela UI, sem código.

---

## FASE 8 — Produção madura / Segurança ⏳
- [ ] **ROTACIONAR credenciais vazadas** (Groq `gsk_tx1...`, senha postgres, Evolution key; `SECRET_KEY` ≠ `SECRET_ENCRYPTION_KEY`) — URGENTE
- [ ] HTTPS/SSL (sem domínio → IP; via Caddy/nginx ou Cloudflare Tunnel)
- [ ] Rate limiting (login, webhook)
- [ ] Logs estruturados (JSON) + healthcheck `/health`
- [ ] Timeout/retry por nó no motor
- [ ] Backup automatizado do volume `postgres_data`
- [ ] Observabilidade mínima (logs centralizados)
- [ ] CORS restrito em produção

## FASE 9 — Extras (quando precisar)
- [ ] Dashboard/analytics mais completo (uso IA, conversas, limites)
- [ ] Integração com outros canais (Telegram, Email)
- [ ] Multi-tenancy avançado (planos, quotas — complementa o limitador de IA)
- [ ] Nó de teste (mensagem simulada customizável)
- [ ] Validação visual do grafo (nós órfãos, nós soltos)
- [ ] Confirmar exclusão / duplicar fluxo no editor

---

## 🔑 CREDENCIAIS VAZADAS (URGENTE — ainda pendente)
> A chave Groq, a senha do postgres (`yangeme`) e a chave da Evolution foram
> expostas em conversas anteriores. **Rotacione antes de considerar produção segura.**

- [ ] Groq: novo key em console.groq.com → API Keys → revogar a antiga
- [ ] Postgres local: trocar `POSTGRES_PASSWORD` (via SQL `ALTER USER`) + `.env`
- [ ] Evolution: gerar nova chave (`EVOLUTION_AUTH_KEY`/`EVOLUTION_API_KEY`)
- [ ] `SECRET_KEY` ≠ `SECRET_ENCRYPTION_KEY` (hoje iguais; devem ser distintas)
- [ ] Confirmar WhatsApp continua conectado após rotação

---

## 💡 LEGENDA
- **✅** concluído e testado
- **⏳** próximo (prioridade)
- **⏭️** depois
- **🔄** em andamento

> Atualize este arquivo ao concluir cada passo.
