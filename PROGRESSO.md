# Progresso — FlowAI (AI SaaS - Atendimento WhatsApp)

> Use este documento para acompanhar onde estamos. Marque `[x]` quando concluido.
> Documento de trabalho (nao substitui `docs/` tecnico — este e o **roadmap/estado**).

---

## FASE 0 — Visao geral ✅
- [x] Plataforma de automacao estilo n8n, foco em **atendimento WhatsApp com IA**
- [x] Multi-tenant: cada **empresa** tem sua configuracao (IA + Evolution) e seus workflows
- [x] Em producao na VPS (Hostinger, `2.25.122.157`) com **Postgres local do Docker**

---

## FASE 1 — Fundacao do Backend ✅
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
- [x] Testado E2E: trigger -> IA -> WhatsApp -> `success` com resposta real

## FASE 3 — Frontend React (editor visual) ✅
- [x] Scaffold Vite + React 19 + React Flow + React Router
- [x] Login / registro (consome /auth/*)
- [x] Painel (lista de workflows, criar, excluir)
- [x] Editor visual (paleta, canvas, conexoes, inspector)
- [x] Salvar (PATCH), Rodar (POST /run), exibir resultado
- [x] CORS backend -> frontend
- [x] Build de producao passa
- [x] Pagina **WhatsApp** com status de conexao + config Evolution por empresa
- [x] Paginas **Conhecimento** (RAG) e **Administracao**
- [x] **Componente `Header`** reutilizado em todas as paginas (elimina duplicacao)
- [x] **Dashboard pos-login** com KPIs por empresa (fluxos, conversas, execucoes)
- [x] **Gerenciador de IA** (`/ai`) — configuracao de provedor, modelo, system prompt com presets
- [x] Estilos CSS completos (kpi-grid, wa-banner, exec-bar, ai-config, role-chip, etc.)

## FASE 3.1 — Modo Gerenciador de IA ✅
- [x] Pagina `/ai` com toggle liga/desliga da IA
- [x] Selecao de provedor (Groq, OpenAI, DeepSeek, Mistral, Ollama)
- [x] Selecao de modelo por provedor
- [x] Editor de system prompt com 4 presets de personalidade:
  - [x] Atendente Amigavel (cordial, humano)
  - [x] Vendedor Consultivo (consultivo, nao pressiona)
  - [x] Suporte Tecnico (preciso, passos numerados)
  - [x] Recepcionista Virtual (acolhe, direciona)
- [x] Salva via `PATCH /config/` (backend existente)
- [x] Build validado (190 modulos, sem erros)

## FASE 4 — Deploy em Producao ✅ (concluido e validado)
- [x] Dockerfile.backend / Dockerfile.frontend (multi-stage)
- [x] docker-compose.yml (postgres, redis, backend, celery-worker, celery-beat, frontend)
- [x] **Supabase** como banco de producao (`DATABASE_URL` = pooler IPv4 do Supabase). Postgres local do Docker = alternativa/fallback, nao o banco em uso.
- [x] Evolution API em **compose separado** (`docker-compose.evolution.yml`), mesma rede do backend, porta 8080
- [x] **create_all automatico no boot** (`lifespan` em `app/main.py`) — nao depende de Alembic/manual
- [x] Celery + Redis para tarefas assincronas
- [x] Deploy validado na VPS: empresa, WhatsApp conectado, **criacao de tabelas automatica no boot**
- [x] Documentacao: `CreateVPS.md`, `VPS-SETUP.md`, `docs/` alinhados ao codigo

## FASE 5 — Integracao WhatsApp PONTA A PONTA ✅
- [x] Numero conectado via Evolution (`flowai`, `state: open`)
- [x] Webhook configurado -> `POST /webhook/whatsapp/1`
- [x] Workflow `Atendimento Basico (IA)` ativo (trigger_message -> ai -> whatsapp_send -> wait)
- [x] Respondendo sozinho com **memoria de conversa** (16+ execucoes `success`)
- [x] Config da empresa com Evolution + fallback para `.env` (Groq)

---

## FASE 6 — UX do consumidor / QR na tela ✅ (concluido)
**Objetivo:** o usuario final conecta o WhatsApp **dentro da aplicacao**, sem precisar do manager `:8080/manager` nem curl.

- [x] Endpoint backend `POST /config/whatsapp/setup` — cria instancia automaticamente na Evolution e retorna QR
- [x] Endpoint backend `POST /config/whatsapp/disconnect`
- [x] Frontend simplificado: **zero configuracao** — so botao "Conectar WhatsApp" + QR
- [x] Usuario nao precisa saber URL, API key nem nome da instancia
- [x] Refresh automatico do status para "Conectado" apos escanear
- [x] Botao "Desconectar WhatsApp"

**Nota de escala:** O modelo atual (1 instancia Evolution por empresa) funciona para MVP (10-50 empresas). Para escala maior (100+), considere migrar para API oficial do WhatsApp Business ou pool de instancias.

---

## FASE 7 — Seguranca Critica ✅ (concluido)

### 7.1 — Credenciais vazadas (URGENTE)
- [x] **ROTACIONAR** Groq key — `DEFAULT_AI_API_KEY` marcar como `CHANGE_ME_IN_GROQ_CONSOLE`
- [x] **ROTACIONAR** senha postgres — nova senha gerada + `.env` atualizado
- [x] **ROTACIONAR** Evolution API key — nova chave gerada + `.env` atualizado
- [x] `SECRET_KEY` != `SECRET_ENCRYPTION_KEY` — chaves distintas geradas
- [ ] Confirmar WhatsApp continua conectado apos rotacao (manual na VPS)

### 7.2 — Autenticacao nos routers desprotegidos
- [x] `Depends(get_current_user)` em `conversation_router.py` (todos os endpoints)
- [x] `Depends(get_current_user)` em `message_router.py` (todos os endpoints)
- [x] `Depends(get_current_user)` em `company_router.py` (todos os endpoints)
- [x] `Depends(get_current_user)` em `customer_router.py` (todos os endpoints)
- [x] Isolamento multi-tenant: filtro `company_id` em todas as queries
- [x] Validacao `company_id` do path vs `current_user.company_id` (403 cross-tenant)

### 7.3 — Webhook seguro
- [x] Validacao HMAC via header `evolution-auth` (`webhook_router.py`)
- [x] `hmac.compare_digest` para previnir timing attacks
- [x] Rejeita POSTs sem autenticacao (401)

### 7.4 — Rate limiting
- [x] `slowapi==0.1.9` adicionado ao `requirements.txt`
- [x] Rate limit no login: 5 tentativas/minuto
- [x] Rate limit no registro: 5 tentativas/minuto
- [x] Handler para 429 com mensagem em portugues

### 7.5 — CORS
- [x] CORS baseado em variavel de ambiente `ALLOWED_ORIGINS`
- [x] Default seguro: `http://localhost:5173,http://127.0.0.1:5173`
- [x] Configuravel via `.env` para producao

### 7.6 — Seguranca JWT
- [x] `SECRET_KEY` obrigatoria no startup (falha com `sys.exit(1)` se nao configurada)
- [x] Removido default `"dev-secret"` — sem chave = app nao inicia
- [x] Tokens assinados com `_SECRET_KEY` (constante, nao re-leita por request)

### 7.7 — Dependencias
- [x] `requirements.txt` com versoes exatas pinadas
- [x] `slowapi` adicionado
- [x] `healthcheck` endpoint adicionado (`GET /health`)

---

## FASE 8 — Funcionalidades Core ⏳

### 8.1 — Midia WhatsApp
- [ ] Webhook processa imagens (`imageMessage`)
- [ ] Webhook processa audio (`audioMessage`)
- [ ] Webhook processa video (`videoMessage`)
- [ ] Webhook processa documentos (`documentMessage`)
- [ ] Webhook processa stickers (`stickerMessage`)
- [ ] Download de midias via Evolution API (`/chat/getMediaMessage`)
- [ ] Nodes de workflow suportam midia (envio/recebimento)
- [ ] Resposta IA com midia (ex.: enviar imagem do catalogo)

### 8.2 — Upload de arquivos no Knowledge Base
- [ ] Endpoint `POST /knowledge/upload` com `UploadFile`
- [ ] Parser de PDF (PyMuPDF ou pdfplumber)
- [ ] Parser de DOCX (python-docx)
- [ ] Parser de TXT/CSV/Markdown
- [ ] Chunking por tamanho de pagina/paragrafo
- [ ] Progresso de upload no frontend
- [ ] Limite de tamanho por arquivo (configuravel)

### 8.3 — Handoff Humano
- [ ] Status de conversa `"pending_agent"` (novo valor no enum)
- [ ] Node `transfer_to_agent` no registry
- [ ] Notificacao quando conversa precisa de atendimento humano
- [ ] Visualizacao de conversas pendentes no Dashboard
- [ ] Botao "Assumir conversa" para agente humano
- [ ] Historico de transferencias (quem assumiu, quando)

### 8.4 — Horario de Atendimento
- [ ] Model `BusinessHours` (empresa, dias, hora_inicio, hora_fim, timezone)
- [ ] Config por empresa (ex.: segunda a sexta, 8h-18h)
- [ ] Fora do horario: responder com mensagem automatica configuravel
- [ ] Node `check_business_hours` no workflow engine
- [ ] Integracao com o `conversation_service`

### 8.5 — Template Messages WhatsApp
- [ ] Endpoint `POST /whatsapp/template` para enviar template oficial
- [ ] Integracao com `/message/sendTemplate/` da Evolution API
- [ ] Upload de midia para template (header image/video)
- [ ] Variaveis dinamicas no template (`{{1}}`, `{{2}}`)
- [ ] Verificar status de envio do template (delivered, read, failed)

### 8.6 — Paginacao e Busca
- [ ] Conversations: `skip`/`limit` + busca por nome/status/data
- [ ] Messages: `skip`/`limit` + busca por conteudo
- [ ] Customers: `skip`/`limit` + busca por nome/telefone/email
- [ ] Workflows: `skip`/`limit` + busca por nome
- [ ] Knowledge: `skip`/`limit` + busca por titulo/conteudo
- [ ] Executions: `skip`/`limit` + filtro por status/data
- [ ] Frontend: componentes de paginacao em todas as listas

### 8.7 — Senha e Sessao
- [ ] Endpoint `POST /auth/change-password` (senha atual + nova senha)
- [ ] Endpoint `POST /auth/forgot-password` (envia email com link de reset)
- [ ] Endpoint `POST /auth/reset-password` (token + nova senha)
- [ ] Endpoint `POST /auth/refresh` (renovar access token)
- [ ] Infraestrutura de email (SendGrid, Resend, ou SMTP)

---

## FASE 9 — Intelligence & Analytics ⏳

### 9.1 — Limitador de IA por empresa
- [ ] Model/coluna JSON para limites por empresa
- [ ] Limite de mensagens (X msgs/dia ou por conversa)
- [ ] Limite de tokens/custo (teto por sessao/dia)
- [ ] Janela de tempo (horario de atendimento)
- [ ] Timeout/retry por chamada de IA
- [ ] Fallback quando limite atingido (mensagem padrao, encerrar, avisar humano)
- [ ] Aplicar limites em `conversation_service` e nodes `ai`/`ai_rag`
- [ ] UI de configuracao dos limites (pagina Admin)
- [ ] Dashboard de uso/consumo

### 9.2 — Dashboard Avancado
- [ ] Graficos de volume de conversas (por dia/semana/mes)
- [ ] Tempo medio de resposta
- [ ] Taxa de resolucao automatica vs humano
- [ ] Uso de IA (tokens consumidos, custo estimado)
- [ ] Conversas por status (abertas, fechadas, pendentes)
- [ ] Top workflows mais executados
- [ ] Erros e falhas por node

### 9.3 — Metricas por Workflow
- [ ] Execucoes totais e por periodo
- [ ] Taxa de sucesso vs erro
- [ ] Tempo medio de execucao
- [ ] Uso por node (quais nodes sao mais chamados)
- [ ] Logs de execucao estruturados

### 9.4 — Audit Log
- [ ] Model `AuditLog` (user, action, entity, entity_id, timestamp, details)
- [ ] Registrar: login, CRUD de workflows, mudanca de config, envio de mensagem
- [ ] Endpoint `GET /audit-logs` com filtros (user, action, data)
- [ ] Visao no frontend (pagina Admin)

### 9.5 — Teste e Simulacao
- [ ] Modo "simular" no editor de workflows (inserir mensagem fake)
- [ ] Preview de resposta IA antes de ativar workflow
- [ ] Validacao visual do grafo (nos orfaos, nos soltos, ciclos)
- [ ] Confirmar exclusao / duplicar fluxo no editor

---

## FASE 10 — Escala & Multi-canal ⏳

### 10.1 — pgvector
- [ ] Instalar extensao pgvector no Postgres
- [ ] Migrar embeddings de JSON para tipo `vector(384)` (ou dimensao do modelo)
- [ ] Criar indice `ivfflat` ou `hnsw` para busca por similaridade
- [ ] Substituir busca em memoria por query SQL `cosine_distance`
- [ ] Benchmark: comparar performance antes/depois

### 10.2 — Canais Extras
- [ ] Telegram: webhook + envio de mensagens
- [ ] Email: integracao SMTP/IMAP
- [ ] Instagram DM: Graph API
- [ ] Interface unificada: todas as conversas em um inbox

### 10.3 — Multi-tenancy Avancado
- [ ] Planos de assinatura (free, basic, pro, enterprise)
- [ ] Quotas por plano (mensagens, workflows, knowledge items)
- [ ] Billing integration (Stripe, Asaas, ou Mercado Pago)
- [ ] Portal do cliente para gerenciar assinatura

### 10.4 — Versionamento de Workflows
- [ ] Historico de versoes (snapshot a cada save)
- [ ] Rollback para versao anterior
- [ ] Diff visual entre versoes
- [ ] Publicacao de versao (producao vs staging)

### 10.5 — Webhooks Outbound
- [ ] Configurar webhook URL por empresa
- [ ] Enviar evento quando conversa inicia, termina, ou workflow executa
- [ ] Retry com backoff exponencial
- [ ] Log de envios e falhas

### 10.6 — API Publica
- [ ] Documentacao OpenAPI/Swagger completa
- [ ] API keys por empresa (nao compartilhar JWT)
- [ ] Rate limiting por API key
- [ ] SDKs para integracao (Python, Node.js)

### 10.7 — WebSocket
- [ ] Endpoint WebSocket para atualizacao em tempo real
- [ ] Push de novas mensagens para o frontend
- [ ] Status de conexao em tempo real
- [ ] Notificacoes push no browser

### 10.8 — Campanhas
- [ ] Enviar mensagens em massa (broadcast)
- [ ] Selecao de destinatarios (por tag, por status)
- [ ] Agendamento de envio
- [ ] Metricas de campanha (enviadas, entregues, lidas)

---

## LEGENDA
- **✅** concluido e testado
- **⏳** proximo (prioridade)
- **⏭️** depois
- **🔄** em andamento

> Atualize este arquivo ao concluir cada passo.

---

## Resumo do Estado Atual

| Fase | Status | Itens |
|------|--------|-------|
| 0 | ✅ Completa | Visao geral |
| 1 | ✅ Completa | Backend, auth, config, IA, Evolution |
| 2 | ✅ Completa | Workflows engine |
| 3 | ✅ Completa | Frontend React |
| 4 | ✅ Completa | Deploy Docker |
| 5 | ✅ Completa | WhatsApp E2E |
| 6 | ✅ Completa | QR na tela |
| 7 | ✅ Completa | Seguranca critica |
| 8 | ⏳ Pendente | Funcionalidades core |
| 9 | ⏳ Pendente | Intelligence & analytics |
| 10 | ⏳ Pendente | Escala & multi-canal |

### Gaps Criticos (por prioridade)

1. **Midia ignorada** — so texto processado, imagens/audio/docs descartados
2. **Knowledge sem upload** — so aceita texto cru, nao arquivos
3. **Sem handoff humano** — conversa travada se IA nao resolve
4. **Sem paginacao** — todas as listas retornam `.all()`
5. **Sem HTTPS** — necessario configurar Caddy/nginx/Tunnel
6. **Sem business hours** — atendimento 24h sem configuracao
7. **Sem audit log** — nao registra quem fez o que
8. **pgvector ausente** — busca vetorial em memoria (O(N))
9. **Sem WebSocket** — sem atualizacao em tempo real
10. **Sem canais extras** — so WhatsApp disponivel
