# 23 — Agenda: Confirmação, Lembretes e Calendários Externos

> Documento de arquitetura/roadmap da Agenda da Secretaria IA (fase 8.6 do
> PROGRESSO.md). Distingue o que está **Implementado**, o que está **Planejado**
> e o que é **Desconhecido**. Fonte de verdade = código (`app/services/agenda*.py`,
> `app/routers/agenda_router.py`, `app/services/evolution.py`).

## 1. Estado atual (Implementado)

- Models `agenda_config`, `appointments`, `appointment_events` (migration `0013`).
- `app/services/agenda.py`: `build_slots`, `has_conflict`, `is_blocked`,
  `within_min_advance`, CRUD com histórico (`appointment_events`), `config_payload`.
- Rotas `/agenda/*` (config, availability, appointments CRUD) — apenas autenticadas.
- Function calling da IA no pipeline de atendimento (`conversation_service` +
  `app/services/agenda_tools.py`): as 5 tools (consultar, disponibilidade, criar,
  alterar, cancelar) são ativadas quando `agenda_config.enabled` está ligado.
- Frontend `/agenda`: lista com filtros, criação e cancelamento, configuração
  (gestor) com horários/bloqueios/mensagem de confirmação e fuso.
- Envio de WhatsApp existe e é usado pelo pipeline: `evolution.send_text`
  (`app/services/evolution.py:21`) e `context.send_whatsapp`.

### O que NÃO existe hoje (confirmado no código)

- `confirmation_message` é **apenas armazenado** na config (`agenda_router.py:119`);
  nenhum código envia esse texto.
- **Não há estado "aguardando confirmação"**: a IA cria o compromisso direto com
  status `scheduled` (`agenda.py:437`). Não há fluxo "cliente responde e só então
  vira `confirmed`".
- **Não há lembretes/notificações**: a única tarefa agendada do Celery Beat é a
  limpeza de execuções às 03:00 (`tasks/celery_app.py:28`).
- **Não há OAuth/sync com Google ou Outlook** (nenhum token externo é persistido).

## 2. Fase 8.6b — Confirmação em 2 passos + lembretes (Planejado)

Objetivo: cumprir o fluxo real do cliente (“só agendo depois que o cliente
confirmar”) apoiado nas infras já existentes (webhook, filas, Evolution API).

### 2.1 Confirmação em 2 passos

1. **Criar agendamento provisório**: tool `criar_agendamento` passa a criar com
   novo status `awaiting_confirmation` (ou `pending`) quando `origin=whatsapp`.
   A agenda ocupa o slot (conflito continua bloqueando), mas o negócio não fechou.
2. **Enviar pedido de confirmação**: ao criar, disparar `evolution.send_text`
   para o número do cliente com o texto configurado (ex.: “Posso confirmar
   dia X às 10:00? Responda CONFIRMAR ou CANCELAR”). Reaproveita o
   `confirmation_message` (hoje apenas armazenado).
3. **Receber resposta**: o webhook `POST /webhook/whatsapp/{company_id}` já
   processa as mensagens do cliente; identificar a resposta de confirmação e
   alterar o status para `confirmed` (ou `canceled`).
4. **Expiração**: tarefa periódica (Celery Beat) que cancela compromissos
   `awaiting_confirmation` sem resposta dentro de X horas (configurável).

### 2.2 Lembretes

- Tarefa Celery Beat (ex.: a cada 15/30 min) que consulta compromissos
  `confirmed` (e `scheduled`) que começam em X horas (ex.: 24h e 1h).
- Envia `evolution.send_text` para o número do cliente (ou o número configurado
  da empresa) com o texto de lembrete.
- Configuração no painel: antecedências e mensagens (estilo `agenda_config`).

### 2.3 Configurações novas (Planejado)

- Número de WhatsApp usado pela Secretaria IA (hoje o envio usa a instância
  `inst-<company_id>`; falta a config do número).
- JSON/colunas de lembretes (antecedências + mensagens).
- Prazo de expiração da confirmação.

### 2.4 Risco/atenção

- **Multi-instância/paridade**: o envio deve usar a instância da empresa
  (`inst-<company_id>`), nunca uma instância compartilhada.
- **Custo**: cada lembrete é mais uma porção no WhatsApp agendando volume.
- **Erros de envio**: tratar falha do `send_text` sem deixar o compromisso órfão.

## 3. Fase 8.6c — Calendários externos (Google/Outlook) (Planejado → Desconhecido)

Maior esforço; depende de decisões de produto antes de código.

### 3.1 Pré-requisitos (fora do código)

- Aplicação OAuth2 no **Google Cloud** (Google Calendar API) e **Microsoft Entra**
  (Microsoft Graph). Verificação de app para produção (processo + custo).
- `client_id`/`client_secret` por provedor em variáveis de ambiente
  (`GOOGLE_OAUTH_*`, `MICROSOFT_OAUTH_*`).

### 3.2 Implementação esperada

1. Rotas OAuth por empresa: “Conectar conta Google/Outlook” (browser redirect +
   callback), persistindo **token de acesso/refresh criptografado** por empresa
   (a criptografia Fernet já existe em `field_crypto.py`).
2. Sincronização:
   - Campos no model `appointments`: `external_provider`, `external_event_id`,
     `sync_token` (ou delta da Microsoft).
   - Background task (Celery) para push (evento FlowAI → calendário externo) e
     pull (evento externo → FlowAI), usando GitHub-style reconciliation.
3. Decisões de arquitetura a definir:
   - **Fonte de verdade**: FlowAI → grava no externo (ideal para operação) vs.
     externo → importa para o FlowAI (caso o cliente já viva no Google).
   - **Conflito**: eventos externos **devem bloquear slots** do `build_slots`?
     (provavelmente sim, senão a IA agenda em horário já ocupado no Google).
   - **Registro de eventos de calendários que não sejam da empresa** (privados vs.
     ocupado/livre).

### 3.3 O que NÃO fazer agora (roadmap)

- Não adicionar `external_event_id` por último minuto sem decisão de fonte de
  verdade (evita schema que depois muda).
- Não criar segunda implementação de fila para sync — reutilizar Celery/Redis.
- Não armazenar tokens em texto plano.

## 4. Ordem recomendada

1. **8.6b** (confirmação 2 passos + lembretes) — depende de infra já existente
   (webhook, Evolution, Celery Beat) e é o que fecha o fluxo de atendimento.
2. **8.6c** (Google/Outlook) — entrega maior, exige OAuth + decisões de fonte de
   verdade; melhor como projeto separado.

## 5. Testes associados (existente)

- `tests/test_agenda.py` (23 testes de serviço/rotas).
- `tests/test_agenda_tools.py` (19 testes do executor de tools).
- `tests/test_agenda_pipeline.py` (2 testes de wiring do pipeline).
- Suite: 243 passed (08/09/2026).