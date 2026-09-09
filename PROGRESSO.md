# Progresso — FlowAI (AI SaaS - Atendimento WhatsApp)

## Atualizacao de dependencias vulneraveis — 08/09/2026

- [x] `pip-audit -r requirements.txt`: **75 vulnerabilidades em 7 pacotes → 0** ("No known vulnerabilities found").
- [x] Upgrades: fastapi 0.115.12→0.141.1, starlette 0.46.2→1.6.0 (pin explicito), python-dotenv 1.1.0→1.2.3,
      python-multipart 0.0.20→0.0.32, cryptography 45.0.4→50.0.1, pypdf 5.1.0→6.18.0, slowapi 0.1.9→0.1.10.
- [x] **Substituicao `python-jose` → `PyJWT`** (2.13.0): remove `ecdsa` (CVE-2024-23342/Minerva, sem fix publicado) e
      `pyasn1` da arvore; JWT continua HS256 (utilitario trocado em `app/services/security.py`).
- [x] Regressao backend: **298 passed** (fastapi 0.141.1 + starlette 1.6.0 + PyJWT + slowapi 0.1.10).
- [x] Docs atualizados: `PROGRESSO.md`, `README.md`, `docs/00-indice-tecnico.md`, `SEGURANCA-2026-09-08-AGENDA.md`.
- [ ] Validar comportamento real na VPS apos deploy (autenticacao/login e upload de PDF) — item manual.

> Use este documento para acompanhar onde estamos. Marque `[x]` quando concluido.
> Documento de trabalho (nao substitui `docs/` tecnico — este e o **roadmap/estado**).

---

## Revisao de seguranca da agenda — 08/09/2026

- [x] Revisados de34e14, 800a142 e 997e2bc; isolamento de clientes nas tools corrigido localmente.
- [x] Regressoes locais: escopo por remetente/empresa, workflow dry-run, erros LLM, CI/Docker.
- [x] Atualizar dependencias Python apontadas pelo pip-audit e repetir validacao (75→0; fatia acima).
- [x] Garantia transacional contra dupla reserva + testes concorrentes Postgres.
      `app/services/agenda.py` (`_serialize_booking`, advisory lock transacional
      `pg_advisory_xact_lock` por company_id+data), migration `0015` (indice
      composto company_id+date) e `tests/test_agenda_concurrency.py` (roda contra
      Postgres descartavel via `TEST_POSTGRES_URL`; no SQLite e no-op).
- [x] Confirmacao server-side para remarcar/cancelar via WhatsApp (08/09/2026):
      pendencias em `pending_appointment_actions` (migration `0016`), pedido enviado
      ao cliente, resposta CONFIRMAR/CANCELAR processada de forma deterministica
      antes da IA; escopo por telefone, expiracao e teste de slot tomado.
      `tests/test_agenda_pending_actions.py` (17 testes). Suite: 317 passed.
- [x] Permissoes granulares dos operadores da agenda (08/09/2026, modelo papel +
      propriedade): ler/criar abertos; alterar/cancelar exigem gestor OU criador;
      WhatsApp-origin so gestao; config gestor-only. 403 sem permissao.
      `tests/test_agenda_permissions.py` (14 testes HTTP).
- [x] Limites de abuso (orcamento por empresa): migration `0017_ai_limits`,
      `app/services/ai_limits.py`, enforcement em `conversation_service` e
      `nodes/context.py`. `tests/test_ai_limits.py` (16 testes).
- [ ] Concluir auditoria ampliada de sessoes, uploads, historico/segredos e infraestrutura.

Detalhes e resultados: [revisao de seguranca](docs/SEGURANCA-2026-09-08-AGENDA.md).
Itens marcados acima sao locais: nao houve commit, push ou deploy nesta revisao.

> Use este documento para acompanhar onde estamos. Marque `[x]` quando concluido.
> Documento de trabalho (nao substitui `docs/` tecnico — este e o **roadmap/estado**).

---

## FASE 0 — Visao geral ✅
- [x] Plataforma de automacao estilo n8n, foco em **atendimento WhatsApp com IA**
- [x] Multi-tenant: cada **empresa** tem sua configuracao (IA + Evolution) e seus workflows
- [x] Em producao na VPS (Hostinger, `2.25.122.157`) com **Postgres local do Docker**

---

## FASE 1 — Fundacao do Backend ✅
- [x] Auth JWT (register/login, bcrypt, PyJWT)
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

### 8.1 — Midia WhatsApp (resposta automatica) ✅
- [x] Webhook detecta `imageMessage`, `audioMessage`, `videoMessage`, `documentMessage`, `stickerMessage`
- [x] Responde automaticamente: "No momento, não é possível processar arquivos. Envie apenas mensagens de texto."
- [x] Não ignora silenciosamente midias mais
- [x] **DECISAO (07/09/2026): NAO implementar download/processamento real de midias.** A resposta automatica
      e a solucao final; removida a entrada de "futuro" e todos os itens de mídia do roadmap.

### 8.2 — Upload de arquivos no Knowledge Base ✅
- [x] Endpoint `POST /knowledge/upload` com `UploadFile`
- [x] Parser de PDF (pypdf)
- [x] Parser de DOCX (python-docx)
- [x] Parser de TXT/CSV/Markdown
- [x] Frontend: area de upload com drag & drop
- [x] Limite de tamanho: 10MB
- [ ] Progresso de upload no frontend (melhoria futura)

### 8.3 — Handoff Humano ✅
- [x] Status de conversa `"pending_agent"` (novo valor no enum)
- [x] Node `transfer_to_agent` no registry
- [x] Notificacao quando conversa precisa de atendimento humano (pill/aba Aguardando no inbox + banner no Dashboard)
- [x] Visualizacao de conversas pendentes no Dashboard
- [x] Botao "Assumir conversa" para agente humano
- [x] Historico de transferencias (quem assumiu, quando) — tabela `conversation_transfers`

### 8.4 — Horario de Atendimento ✅
- [x] Model `BusinessHours` (empresa, timezone, enabled, schedule JSON, mensagem) — tabela `business_hours`
- [x] Config por empresa via `GET/PUT /config/business-hours` (painel > WhatsApp > Horário de atendimento)
- [x] Fora do horario: resposta automatica configuravel (uma vez por conversa; ignora `pending_agent`/`agent`)
- [x] Node `check_business_hours` no workflow engine (saidas true/false) + template "Verificacao de Horario"
- [x] Integracao com o `conversation_service` (gate `closed` em mensagens e workflows)
- [x] Sem config ou desabilitado: 24/7 (atendimento nunca trava)

### 8.5 — Template Messages WhatsApp
- [ ] Endpoint `POST /whatsapp/template` para enviar template oficial
- [ ] Integracao com `/message/sendTemplate/` da Evolution API
- [ ] Upload de midia para template (header image/video)
- [ ] Variaveis dinamicas no template (`{{1}}`, `{{2}}`)
- [ ] Verificar status de envio do template (delivered, read, failed)

### 8.6 — Agenda da Secretaria IA

> Fatia 1 (backend) concluída: models + migration `0013`, serviço `app/services/agenda.py`,
> rotas `/agenda/*`, testes verdes. **Fatia 2 (tools de IA) concluída**: function calling
> em `llm.generate_reply_with_tools` + executor `app/services/agenda_tools.py` ligado ao
> pipeline (`conversation_service`) e ao nó **ai** do Workflow Engine quando a agenda está
> ativa. **Fatia 3 (frontend `/agenda`) concluída**: página com resumo, lista com filtros,
> criação e cancelamento via modal, e configuração (gestor). **Fase 8.6b (confirmação em 2
> passos + lembretes) concluída**: status `awaiting_confirmation`, pedido/processamento de
> confirmação (interceptado no webhook), expiração e lembretes via Celery Beat, migration
> `0014` e novos campos de config. **Fatia 4 concluída**: template de workflow
> "Secretaria IA (Agenda)" + docs/deploy (15, 07, 23, FATOS-CHAVE).

- [x] Criar módulo de Agenda por empresa para gerenciamento de compromissos e agendamentos
- [x] Permitir que a Secretaria IA consulte a agenda da empresa e verifique disponibilidade de datas e horários (tool `consultar_agenda`/`verificar_disponibilidade` + rotas `/agenda/*`)
- [x] Verificar automaticamente conflitos antes de confirmar um agendamento (`has_conflict`; rotas retornam 409; executor da IA nunca confirma slot ocupado)
- [x] Registrar no agendamento: cliente, telefone, data, horário, tipo do compromisso, observações e origem da solicitação (campos `customer_name`/`phone`/`date`/`start_time`/`end_time`/`service`/`notes`/`origin`)
- [x] Identificar que o agendamento foi originado pelo atendimento via WhatsApp (`origin=whatsapp`)
- [x] Permitir configurar mensagem de confirmação de agendamento (`confirmation_message`)
- [x] Permitir configurar horários disponíveis para agendamento (`schedule` por dia)
- [x] Permitir configurar duração padrão dos compromissos (`slot_duration`)
- [x] Permitir configurar antecedência mínima para novos agendamentos (`min_advance`)
- [x] Permitir configurar intervalos/bloqueios de horários (`blocked`)
- [x] Permitir filtros por data, período e status (`GET /agenda/appointments?date_from&date_to&status`)
- [x] Registrar histórico de criação, alteração e cancelamento dos agendamentos (model `appointment_events`)

**Concluído (Fatia 2 — tools de IA + integração conversation_service):**
- [x] Permitir criação de agendamentos pela IA a partir de solicitações recebidas via WhatsApp
- [x] Permitir alteração e cancelamento de agendamentos através da IA
- [x] Quando o horário solicitado estiver ocupado, consultar horários alternativos disponíveis e apresentar opções ao cliente (o executor orienta o modelo a verificar dias seguintes e oferecer alternativas)
- [x] Garantir que a IA nunca confirme um horário sem validar previamente a disponibilidade (slot precisa estar em `build_slots` no momento da criação)
- [x] Criar ferramenta `consultar_agenda` para uso pelos agentes de IA
- [x] Criar ferramenta `verificar_disponibilidade` para uso pelos agentes de IA
- [x] Criar ferramenta `criar_agendamento` para uso pelos agentes de IA
- [x] Criar ferramenta `alterar_agendamento` para uso pelos agentes de IA
- [x] Criar ferramenta `cancelar_agendamento` para uso pelos agentes de IA
- [x] Definir fluxo: WhatsApp -> IA -> identificar solicitação -> consultar agenda -> verificar disponibilidade -> criar agendamento -> confirmar via WhatsApp (confirmação na resposta da IA/pipeline)

**Concluído (Fatia 3 — frontend `/agenda`):**
- [x] Permitir visualização dos agendamentos no painel administrativo (página `/agenda`: resumo, tabela com status/origem, criação e cancelamento via modal)
- [x] Permitir filtros por cliente no painel (busca por cliente/telefone/serviço client-side; filtro por status/data via API)
- [x] Editar a configuração da agenda no painel (gestor): horários por dia, duração, antecedência, datas bloqueadas, mensagem de confirmação e fuso

**Concluído (Fase 8.6b — Confirmação em 2 passos + lembretes):**
- [x] Estado provisório `awaiting_confirmation` — a IA cria **pendente**, nunca confirma antes do cliente confirmar (ocupa o slot)
- [x] Enviar pedido de confirmação ao número do cliente ("Responda CONFIRMAR ou CANCELAR") com `evolution.send_text` (deduplicado por evento `confirmation_requested`)
- [x] Processar a resposta do cliente (interceptada no webhook/pipeline antes da IA) e alterar para `confirmed` ou `canceled`
- [x] Auto-cancelamento por expiração (Celery Beat a cada 30 min, `confirmation_expiry_hours` configurável)
- [x] Vincular o número de WhatsApp utilizado pela Secretaria IA (`whatsapp_number` na config do painel)
- [x] Lembretes automáticos (Celery Beat a cada 15 min) antes do horário (`reminder_hours`, ex.: 24h e 1h) com `evolution.send_text` no número do cliente
- [x] Configurar antecedências e mensagens de lembrete no painel (migration `0014`)
- [x] Enviar a `confirmation_message` real ao cliente após a confirmação do agendamento

**Planejado (Fase 8.6c — Integração com calendários externos Google/Outlook):**
- [ ] OAuth2 do Google (Google Calendar API) por empresa — tela "Conectar conta Google"
- [ ] OAuth2 Microsoft (Microsoft Graph / Outlook) por empresa — tela "Conectar conta"
- [ ] Persistir tokens de acesso/refresh por empresa (criptografados) e renovação automática
- [ ] Sincronizar eventos (`external_event_id` + `sync_token`/delta) via polling e/ou webhooks
- [ ] Decidir fonte de verdade (FlowAI → grava no externo, ou externo → importa) e se eventos externos bloqueiam slots da Secretaria IA
- [ ] Verificação/aplicação de app no Google Cloud e Microsoft Entra (processo + custo de produção)

**Concluído (integração/roadmap):**
- [x] Permitir que a Agenda seja utilizada por diferentes agentes e workflows (o nó **ai** do Workflow Engine ativa as tools de agenda quando a agenda está ativa)
- [x] Integrar a Agenda ao Workflow Engine (nó `ai` usa function calling de agenda da mesma forma que o pipeline de atendimento)

**Concluído (Fatia 4 — template + docs/deploy):**
- [x] Template de workflow "Secretaria IA (Agenda)" em `app/services/templates.py` (trigger message -> nó `ai` -> enviar -> aguardar; as tools de agenda ativam automaticamente com a agenda configurada) + testes de contrato em `tests/test_templates.py`
- [x] Docs: `docs/23` (8.6b implementado / 8.6c planejado), `docs/07-redis-e-filas.md` (tasks beat de expiração e lembretes), `docs/15-deploy.md` (validação da migration `0014` e beat), `docs/10-api.md`, `docs/06-banco-de-dados.md`, `FATOS-CHAVE.md`

### 8.7 — Paginacao e Busca ✅
- [x] Conversations: `skip`/`limit` com paginação server-side
- [x] Messages: `skip`/`limit` com paginação server-side
- [x] Knowledge: `skip`/`limit` com paginação server-side
- [x] Workflows: `skip`/`limit` com paginação server-side
- [x] Users: `skip`/`limit` com paginação server-side
- [x] Frontend: todas as paginas consomem `{total, items}`
- [x] Filtros server-side por nome/palavra (`q`) em customers, knowledge, workflows, users e conversas (`q` + `status`)
- [x] Botoes de paginacao no frontend (componente `Pagination`; paginas: Leads, Fluxos, Conhecimento, Membros, Conversas)

### 8.8 — Senha e Sessao ✅
- [x] Endpoint `POST /auth/change-password` (senha atual + nova senha)
- [x] Endpoint `POST /auth/forgot-password` (envia email com link de reset)
- [x] Endpoint `POST /auth/reset-password` (token + nova senha)
- [x] Endpoint `POST /auth/refresh` (renovar access token com refresh token rotacionado)
- [x] Infraestrutura de email (SMTP: Host/Port/User/Password/From) + token de reset com uso unico

### 8.9 — Gestão de membros: setor + nível de acesso ✅
> **Objetivo (original):** ao criar/editar um funcionário, o administrador define o **setor**
> da pessoa e o **nível de acesso** dela.
>
> **Fato corrigido (implementação, 09/09/2026):** a proposta original era `User.department_id`
> (um único setor por usuário). A implementação foi **m2m**: tabela `user_departments`
> (user_id, department_id, level) permitindo **vários setores** por membro. Aviso: a regra
> §2 (código é a fonte de verdade) se aplica — a forma real é o m2m, não a coluna única.

- [x] Model `UserDepartment` (user_id, department_id, level, UniqueConstraint uq_user_department, FKs ondelete=CASCADE)
- [x] Relação `User.departments` (cascade all, delete-orphan) + export em `app/models/__init__.py`
- [x] Migration Alembic `0019_user_departments`
- [x] `UserCreate`/`UserUpdate`: aceitar lista `departments` `[{department_id, level}]` (level: `view`/`attend`/`manage`); validar setor = mesma empresa (400 se externo) e nível válido (422)
- [x] `UserResponse`: expor `departments` na listagem de membros (batch, sem N+1)
- [x] Service `app/services/access_rules.py`: `has_full_access`, `_user_levels`, `visible_condition`, `can_view`, `can_attend`
- [x] Níveis: `view` (só lê) < `attend` (padrão; lê, responde, assume, altera status) < `manage` (hoje = `attend`; reservado p/ gestão futura). Dono/Admin = acesso irrestrito
- [x] Inbox: atendente **sem setor** vê tudo (compatibilidade); com setores vê conversas dos seus setores + as sem setor (`department_id IS NULL`); `view` lê mas recebe 403 ao responder/alterar/assumir
- [x] Enforce em: `conversation_router` (listagem/detalhe/update/assume/pause) e `message_router` (reply/update/delete mensagens)
- [x] `Conversation` response: `department_id` + `department_name` (badge no inbox)
- [x] Frontend (`Admin.jsx`): painel "vincular setores" (seletor setor+nível, adicionar/remover) no criar membro e no modal "Editar membro" (papel + senha opcional + setores), badges de setor/nível na tabela
- [x] Frontend (`Conversations.jsx`): badge de setor no item e no contexto da conversa
- [x] Testes: `tests/test_user_departments.py` (15 testes: criar/editar/limpar setores, setor externo 400, nível inválido 422, visibilidade por setor, view-only 403, attend responde)
- [x] Docs: `docs/10-api.md`, `docs/06-banco-de-dados.md`, `docs/14-frontend.md`, `docs/16-seguranca.md`, `docs/FATOS-CHAVE.md`

---

## FASE 9 — Intelligence & Analytics ⏳

### 9.0 — Redesenho do Painel + Estudo de Mercado ⏳
- [x] **Estudo de mercado**: analisar paineis/dashboards de plataformas concorrentes e
      de referencia (n8n, Zendesk, Intercom, Manychat, Chatwoot, Tidio, Freshdesk,
      Evolution/manager, HubSpot, Drift, Birdeye etc.) — coletar ideias de UX, layout,
      componentes e fluxos que vale adotar
- [x] Levantar o que essas plataformas mostram no dashboard inicial, como organizam a
      navegacao, quais KPIs destacam e os padroes de listagem/inbox
- [x] Consolidar um documento de ideias/insights (em `docs/`) seguindo a regra de
      documentacao (implementado/parcial/planejado/desconhecido)
      -> `docs/20-estudo-painel-mercado.md`
- [ ] Propor o redesenho do painel atual (hoje muito simples): navegacao, cards, layout
- [x] Implementar a estrutura do inbox (pagina `/conversas`, rota `App.jsx`, item no Header):
      backend `GET /conversations/` enriquecido + `POST /messages/conversation/{id}/reply`
      (`sender_type="agent"`), frontend `Conversations.jsx` 3 paineis + polling.
- [x] Implementar as demais telas/componentes priorizados pelo estudo (historico de
      execucoes por node, filtros+paginacao, KPIs com periodo/tendencia)
- [x] Verificar a configuracao padrao da IA: defaults `DEFAULT_AI_*` do ambiente sao usados
      quando nao ha override valido (`resolve_ai_config` em `config_service.py`),
      conforme "Fatos corrigidos" abaixo — sem configuracao aleatoria. 

### 9.1 — Politica de IA por Usuario (Superadmin) ✅
> **Objetivo:** apenas o superadmin cadastra chaves, provedores e modelos. O superadmin
> define quais IAs cada usuario pode utilizar e qual sera a IA/modelo padrao dele.
> O usuario comum NAO visualiza nem altera chaves, provedor ou modelo livremente.

#### Regra de prioridade (backend)
Prioridade: **politica especifica do usuario** → **politica da empresa** → **padrao global da plataforma**.
Workflows e nodes usam a politica efetiva do usuario no backend; nao confiam em valores enviados pelo frontend.

#### Backend
- [x] Model `UserAIConfig` (user_id, allowed_providers JSON lista, default_provider, default_model, criado_por, timestamps)
- [x] `resolve_ai_config` atualizado: prioridade usuario → empresa → plataforma → .env
- [x] Endpoint `GET /platform-admin/user-ai-config/{user_id}` — ver politica de um usuario
- [x] Endpoint `PUT /platform-admin/user-ai-config/{user_id}` — definir politica (superadmin)
- [x] Endpoint `GET /platform-admin/user-ai-config` — listar politicas de todos os usuarios
- [x] Endpoint `GET /config/ai/effective` — usuario ve apenas sua config efetiva (read-only)
- [x] Endpoint `GET /config/ai/allowed` — usuario consulta quais provedores/modelos tem liberados
- [x] Migration Alembic `0008_user_ai_config`

#### Frontend — Superadmin (`/plataforma`)
- [x] Dropdown "Visão geral" / "Painel de Erros" no header
- [x] Painel de politicas por usuario com edicao
- [x] Modal de edicao: checkbox de provedores + selecao de modelo padrao
- [x] Painel de Erros: tabela com paginacao + limpar erros
- [x] Bloquear edicao de provedor/modelo por usuario comum

#### Frontend — Usuario comum (`/ai`)
- [x] Provedor e modelo somente leitura (cinza)
- [x] System prompt editavel com presets
- [x] Mensagem de credencial quando provedor nao configurado

#### Seguranca
- [ ] Nunca confiar em valores de `ai_provider`/`ai_model` vindos do frontend em nodes/workflows
- [ ] `resolve_ai_config` sempre usa o `user_id` do workflow owner, nao do request
- [ ] Logs de alteracoes de politica (audit trail)
- [ ] Superadmin so altera politica de usuarios da propria plataforma (nao cross-tenant)

### 9.2 — Limitador de IA por empresa ✅
- [x] Model/coluna JSON para limites por empresa (migration `0017_ai_limits`)
- [x] Limite de mensagens (X msgs/dia por empresa)
- [x] Limite de tokens/custo (teto por dia)
- [x] Timeout/retry por chamada de IA
- [x] Fallback quando limite atingido (mensagem configuravel)
- [x] Aplicar limites em `conversation_service` e nodes `ai`/`ai_rag`
- [x] Servico `app/services/ai_limits.py` (check, record, summary)
- [x] Testes: `tests/test_ai_limits.py` (16 testes)
- [ ] Dashboard de uso/consumo (melhoria futura)


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

### 9.4 — Audit Log ✅
- [x] Model `AuditLog` (user, action, entity, entity_id, timestamp, details, ip, user_agent)
- [x] Service `app/services/audit.py` (log_action, get_audit_logs)
- [x] Migration `0018_audit_log`
- [x] Integrado em: auth (register/login/password), config, users, workflows, platform_admin
- [x] Endpoint `GET /audit-logs/` (somente gestores, filtros user/action/entity, paginacao)
- [x] Testes: `tests/test_audit.py` (15 testes)
- [x] Visao no frontend (pagina Admin): tabela com filtros por acao/entidade/usuario + paginacao (somente gestor)

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
| 8 | 🔄 Parcial | Funcionalidades core (8.5 Templates pendente; 8.6 Agenda concluída até 8.6b — faltam 8.6c calendários externos) |
| 9 | 🔄 Parcial | Politica IA (✅), Erros (✅), Auditoria (✅ backend+UI), Dashboard (pendente) |
| 10 | ⏳ Pendente | Escala & multi-canal |

### Gaps Criticos (por prioridade)

1. ~~**Politica de IA por usuario**~~ ✅ concluido
2. ~~**Midia ignorada**~~ ✅ resposta automatica implementada
3. ~~**Knowledge sem upload**~~ ✅ upload de PDF, DOCX, TXT, CSV, MD concluido
4. ~~**Sem handoff humano**~~ ✅ concluido (Fase 8.3)
5. ~~**Filtros e botoes de paginacao no frontend**~~ ✅ concluido (Fase 8.7) — todos os list endpoints tem `q`/`status` e paginacao server-side; paginas com busca, navegacao e componente `Pagination`
6. **Sem HTTPS** — necessario configurar Caddy/nginx/Tunnel
7. ~~**Sem business hours**~~ ✅ concluido (horario de atendimento por empresa, marco 8.4) — atendimento 24h configurável
8. ~~**Sem audit log**~~ ✅ concluido (Fase 9.4) — backend integrarado em 24 endpoints + UI na pagina Admin (filtros e paginacao)
9. **pgvector ausente** — busca vetorial em memoria (O(N))
10. **Sem WebSocket** — sem atualizacao em tempo real
11. **Sem canais extras** — so WhatsApp disponivel
---

## Revisao de prioridade — 04/09/2026

### Fatos corrigidos

- [x] Producao do aplicativo usa Supabase; Postgres do Docker nao e o banco principal de producao.
- [x] Handoff humano esta implementado (Fase 8.3); a lista de gaps acima e historica e deve ser lida com esta correcao.
- [x] Configuracao padrao da IA foi revisada: defaults DEFAULT_AI_* do ambiente sao usados quando nao ha override valido da empresa.
- [x] Webhook Evolution por empresa e fluxo de mensagem unico foram corrigidos e validados no atendimento real.

### Proximo marco recomendado: Funcionalidades Core + Estabilizacao

- [x] **PRIORIDADE** — Politica de IA por usuario: superadmin controla provedores/chaves/modelos por usuario; backend valida; usuario so ve config efetiva
- [x] **PRIORIDADE** — Painel de erros no superadmin (tabela, paginacao, limpar)
- [x] **PRIORIDADE** — Horario de atendimento por empresa (marco 8.4): node `check_business_hours`, gate no conversation_service, template `verificacao_horario`, UI em WhatsApp com dias/fuso/mensagem.
- [x] **PRIORIDADE** — Frontend profissional: pagina **Setores** redesenhadada (stats, busca, tabela, modais de criar/editar/excluir sem confirm nativo) + design system em `index.css` (primitivos `.card`, `.stack`, `.input`, `.table`, `.stat-grid`, `.alert`, `.page-header`), header sticky com avatar/role chip, KPIs com icones, botoes consistentes (`.btn.block`), Account em card.
- [x] **PRIORIDADE** — **Administração da Plataforma** redesenhada: tabs estilizadas, KPIs com icones, grid de provedores com cards, politician chips para provedores, tabela de erros paginada (tema escuro), modal de confirmação para limpar erros, auto-load da aba erros.
- [x] **PRIORIDADE** — **Reset de senha pelo operador**: `POST /platform-admin/users/{id}/reset-password` gera senha provisória (retornada uma única vez), com modal + botão "Copiar" na página Plataforma. Limitacao documentada: sem revogação de sessões ativas (novos logins usam a nova senha).
- [x] **PRIORIDADE** — **Login/Criar conta profissional + copiar senha**: layout hero+card, abas segmented ("Entrar"/"Criar conta"), fallback de clipboard em contexto não seguro (`document.execCommand("copy")`), ResetPassword unificado no novo estilo.
- [x] **DECISAO (07/09/2026)** — **Mídia WhatsApp NÃO será implementada** (sem download/processamento): a solução é a resposta automática da Fase 8.1. Removidos os itens "PROXIMO — Midia WhatsApp" e "Depois da estabilização — Midia WhatsApp".
- [x] **DECISAO (07/09/2026)** — Upload de arquivos no Knowledge Base **já concluido** (Fase 8.2) — item duplicado removido; o upgrade futuro é so processamento assíncrono/limites (mantido em "Depois da estabilizacao").
- [x] **PROXIMO** — Paginacao e filtros em todas as listas: paginação server-side **concluida** (Fase 8.7); falta **filtros e botoes de paginacao no frontend** (mantido como melhoria futura).
- [x] Criar smoke test automatizado: webhook autenticado -> workflow ativo -> execucao -> envio Evolution simulado (`tests/test_webhook_smoke.py`, no suite de 194 testes).
- [x] Criar checklist de deploy verificavel na VPS: ambiente real do container, Supabase, Redis, Evolution e health checks (`docs/21-checklist-deploy-vps.md`).
- [x] Consolidar politica de schema: migrations Alembic obrigatorias para alteracoes estruturais (`alembic/versions/0001..0012`); `create_all` apenas para bootstrap compativel.
- [ ] Adicionar logs estruturados e alertas para falhas de webhook, IA e worker.

### Depois da estabilizacao

- [ ] Paginacao e filtros nas listas de conversas, mensagens, clientes, knowledge, workflows e execucoes.
- [ ] Guardrails de IA por empresa: timeout, retry, limite de uso/custo e fallback para humano.
- [ ] Upload de arquivos no Knowledge Base: **base concluida** (Fase 8.2); upgrade futuro = limites + processamento assíncrono.
- [ ] ~~Mídia WhatsApp~~ — **NAO implementar**: solucao e a resposta automatica (Fase 8.1), decisao 07/09/2026.
- [ ] Padrao de atendimento de IA por empresa: definir tom, escopo, apresentacao inicial e regras de encerramento, sem respostas genericas repetidas a cada mensagem.
- [ ] Contexto conversacional: reconhecer conversas pessoais ou fora do escopo comercial, responder uma unica vez de forma breve e oferecer handoff/encerramento em vez de insistir na mesma mensagem.
- [ ] Fluxo de identificacao de lead: solicitar o primeiro nome no momento adequado, confirmar a informacao e armazenar em `Customer.name` sem sobrescrever um nome ja confirmado.
- [ ] Qualificacao de lead: registrar origem (WhatsApp/workflow), interesse, etapa, tags, ultimo contato e responsavel; encaminhar para humano quando houver intencao comercial ou pedido explicito.
- [ ] Privacidade no lead capture: informar a finalidade quando aplicavel, coletar somente os dados necessarios e permitir correcao/remocao conforme a politica da empresa.
- [ ] Template testavel "Recepcao e captura de lead": saudacao unica -> entender necessidade -> solicitar nome -> qualificar interesse -> responder ou transferir para humano.
- [x] Horario de atendimento por empresa (ver marco 8.4).

> Decisao: nao ampliar dashboard nem redesenhar o frontend antes de concluir o marco de estabilizacao e definir os dados e metricas que ele deve exibir.
### Revisao do editor React Flow e templates

- [ ] Verificar a configuracao completa do React Flow: drag and drop, conexoes, handles, selecao, exclusao, autosave, viewport/minimap e responsividade.
- [ ] Validar o grafo antes de ativar: trigger compativel, nodes orfaos, conexoes invalidas, ciclos e node final sem acao.
- [ ] Revisar os fluxos pre-configurados: cada template deve abrir sem erro, possuir descricao, dados iniciais validos e teste simulavel.
- [ ] Melhorar o fluxo de uso dos templates: preview, campos obrigatorios destacados e duplicacao segura antes de ativar.
- [ ] Criar testes de contrato para templates e para salvar/carregar grafos do editor.
