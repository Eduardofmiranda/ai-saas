# 23 — Agenda: Confirmação, Lembretes e Calendários Externos

> Documento de arquitetura/roadmap da Agenda da Secretaria IA (fase 8.6 do
> PROGRESSO.md). Distingue o que está **Implementado**, o que está **Planejado**
> e o que é **Desconhecido**. Fonte de verdade = código (`app/services/agenda*.py`,
> `app/routers/agenda_router.py`, `app/services/evolution.py`).

## 1. Estado atual (Implementado)

- Models `agenda_config`, `appointments`, `appointment_events` (migration `0013`);
  campos de confirmação/lembretes em `agenda_config` (migration `0014`).
- `app/services/agenda.py`: `build_slots`, `has_conflict` (inclui provisórios),
  `is_blocked`, `within_min_advance`, CRUD com histórico (`appointment_events`),
  `config_payload`. Estados: `scheduled`, `awaiting_confirmation`, `confirmed`,
  `completed`, `canceled`.
- Rotas `/agenda/*` (config, availability, appointments CRUD) — apenas autenticadas
  (`app/routers/agenda_router.py`).
- Function calling da IA no pipeline de atendimento (`conversation_service` +
  `app/services/agenda_tools.py`) e no nó **ai** do Workflow Engine
  (`app/services/nodes/context.py:ask_ai`): as 5 tools são ativadas quando
  `agenda_config.enabled` está ligado.
- Frontend `/agenda`: lista com filtros, criação e cancelamento, configuração
  (gestor) com horários/bloqueios, fuso, confirmação em 2 passos e lembretes.
- Envio de WhatsApp via `evolution.send_text` (`app/services/evolution.py:21`).

### Confirmação em 2 passos (Implementado — fase 8.6b)

- **Criação provisória**: com `confirmation_required` ativo (default), a tool
  `criar_agendamento` cria o compromisso com status `awaiting_confirmation`
  (ocupa o slot). Só vira `confirmed` após resposta do cliente.
- **Pedido de confirmação**: `app/services/agenda_confirmation.py:send_confirmation_request`
  envia `evolution.send_text` com o texto de `confirmation_request_message`
  (placeholders `{nome}`, `{servico}`, `{data}`, `{horario}`) — uma única vez por
  compromisso (deduplicado por evento `confirmation_requested`).
- **Resposta do cliente**: no webhook, `conversation_service` intercepta a
  resposta ANTES da IA/workflow (`process_confirmation_reply`): textos com
  "confirm*"/"sim"/"ok"/"pode" → `confirmed` + envia `confirmation_message`;
  "cancel*"/"desmarcar"/"não quero" → `canceled`. Determinístico, sem custo de LLM.
- **Expiração**: task Celery `expire_unconfirmed_appointments` (a cada 30 min)
  cancela provisórios sem resposta dentro de `confirmation_expiry_hours` (evento
  `confirmation_expired`).

### Lembretes (Implementado — fase 8.6b)

- Task Celery `send_agenda_reminders` (a cada 15 min) consulta compromissos
  `confirmed`/`scheduled` nas janelas de `reminder_hours` (ex.: `[24, 1]`),
  envia `reminder_message` e registra evento `reminder_sent` (um lembrete por
  compromisso). Ativo apenas quando `reminders_enabled` e `enabled` estão ligados.

### Configurações novas (Implementado — fase 8.6b)

- `confirmation_required` (bool), `confirmation_expiry_hours` (int, 0 = nunca),
  `confirmation_request_message` (texto), `reminders_enabled` (bool),
  `reminder_hours` (JSON lista de horas), `reminder_message` (texto),
  `whatsapp_number` (referência do número vinculado à instância).
- Disponíveis em `PUT /agenda/config` e no modal de configuração do `/agenda`.

### O que NÃO existe hoje (confirmado no código)

- **Não há OAuth/sync com Google ou Outlook** (nenhum token externo é persistido).

## 2. Fase 8.6c — Calendários externos (Google/Outlook) (Planejado → Desconhecido)

Maior esforço; depende de decisões de produto antes de código.

### 2.1 Pré-requisitos (fora do código)

- Aplicação OAuth2 no **Google Cloud** (Google Calendar API) e **Microsoft Entra**
  (Microsoft Graph). Verificação de app para produção (processo + custo).
- `client_id`/`client_secret` por provedor em variáveis de ambiente
  (`GOOGLE_OAUTH_*`, `MICROSOFT_OAUTH_*`).

### 2.2 Implementação esperada

1. Rotas OAuth por empresa: "Conectar conta Google/Outlook" (browser redirect +
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

### 2.3 O que NÃO fazer agora (roadmap)

- Não adicionar `external_event_id` por último minuto sem decisão de fonte de
  verdade (evita schema que depois muda).
- Não criar segunda implementação de fila para sync — reutilizar Celery/Redis.
- Não armazenar tokens em texto plano.

## 3. Ordem recomendada

1. **8.6b (concluído)** — confirmação 2 passos + lembretes.
2. **8.6c** (Google/Outlook) — entrega maior, exige OAuth + decisões de fonte de
   verdade; melhor como projeto separado.

## 4. Testes associados

- `tests/test_agenda.py` (23 testes de serviço/rotas).
- `tests/test_agenda_tools.py` (19 testes do executor de tools).
- `tests/test_agenda_pipeline.py` (2 testes de wiring do pipeline).
- `tests/test_agenda_confirmation.py` (32 testes da 8.6b: parsing de resposta,
  envio/deduplicação do pedido, interceptação nos pipelines, expiração e lembretes).
- Suite: 275 passed (08/09/2026).