# 10 — API REST

> Seguranca da agenda (08/09/2026, alteracao local): tools de atendimento recebem
> o telefone do remetente pelo servidor, nao pelo argumento do LLM. Consultas e
> mutacoes restringem empresa + telefone; consultas omitem notas e identificadores
> internos de cliente/empresa. Workflows em dry-run nao executam tools de agenda.
> POST /agenda/appointments rejeita customer_id de outra empresa com 404.
> CRUD HTTP continua disponivel a operadores autenticados da empresa; configuracao
> continua restrita a gestores. Veja [revisao e pendencias](SEGURANCA-2026-09-08-AGENDA.md).

Base URL direta do backend em desenvolvimento: `http://localhost:8000`.
Em producao, o frontend usa o prefixo relativo `/api` e o nginx o remove antes
de encaminhar ao backend; portanto uma chamada do navegador e `/api/config/`,
enquanto a rota FastAPI continua `/config/`.

## Endpoints

#### Health (operacional, sem JWT)

| Metodo | URL | Descricao |
|--------|-----|-----------|
| GET | `/health` | Liveness do processo HTTP |
| GET | `/health/db` | Readiness do banco configurado |
| GET | `/health/redis` | Readiness do Redis |
| GET | `/health/evolution` | Alcance/autenticacao da Evolution |
| GET | `/health/llm` | Coerencia da configuracao global do LLM, sem chamar o modelo |

Os checks de dependencia retornam `503` quando indisponiveis e nunca expõem
segredos. Pelo nginx de producao, use o prefixo `/api`, por exemplo
`/api/health/db`.

## Autenticacao

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| POST | `/auth/register` | Cadastro (cria empresa) | Nao |
| POST | `/auth/login` | Login (`form-urlencoded`; retorna access + refresh) | Nao |
| POST | `/auth/refresh` | Renova access token com refresh token (rotacionado) | Nao |
| POST | `/auth/change-password` | Altera a propria senha (senha atual + nova) | JWT |
| POST | `/auth/forgot-password` | Envia link de reset por email (503 sem SMTP; 10/min) | Nao |
| POST | `/auth/reset-password` | Redefine senha com token (uso unico) | Nao |

### Companies

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| POST | `/companies/` | **Depreciado:** responde 409 para evitar empresa sem usuario; use `/auth/register` | JWT |
| GET | `/companies/` | Lista somente a empresa do usuario | JWT |
| GET | `/companies/{id}` | Busca a propria empresa | JWT |
| PATCH | `/companies/{id}` | Atualiza a propria empresa | JWT |

### Config (por empresa)

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/config/` | Busca configuracoes da empresa | JWT |
| PATCH | `/config/` | Atualiza configuracoes (inclui limites de IA) | JWT |
| POST | `/config/ai/test` | Testa a config de IA (chama o provedor; nao persiste) | JWT |
| GET | `/config/business-hours` | Horario de atendimento da empresa | JWT |
| PUT | `/config/business-hours` | Cria/atualiza horario de atendimento | JWT (gestor+) |

**Limites de abuso (campos em PATCH /config/):**
- `ai_daily_message_limit` (0 = ilimitado)
- `ai_daily_token_limit` (0 = ilimitado)
- `ai_timeout_seconds` (timeout por chamada)
- `ai_max_retries` (retries em falha)
- `ai_fallback_message` (mensagem quando limite atingido)

### Agenda da Secretaria IA

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/agenda/config` | Configuração de agenda da empresa | JWT |
| PUT | `/agenda/config` | Cria/atualiza configuração | JWT gestor |
| GET | `/agenda/availability?date=` | Slots livres para a data | JWT |
| GET | `/agenda/appointments` | Lista compromissos | JWT |
| POST | `/agenda/appointments` | Cria compromisso | JWT |
| GET/PATCH/DELETE | `/agenda/appointments/{id}` | Detalhe/altera/cancela compromisso | JWT |

### WhatsApp (por empresa)

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/config/whatsapp` | Estado da conexao WhatsApp/Evolution | JWT |
| POST | `/config/whatsapp/setup` | Cria instancia (se preciso) e retorna QR base64 | JWT |
| POST | `/config/whatsapp/connect` | Gera QR para uma instancia existente | JWT |
| POST | `/config/whatsapp/disconnect` | Desconecta (logout) a instancia | JWT |
| POST | `/config/whatsapp/test` | Testa alcance/credenciais da Evolution | JWT |

### Customers

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| POST | `/customers/` | Cria cliente (lead) | JWT |
| GET | `/customers/` | Lista clientes com paginacao, contagem de conversas e busca (`q`, `limit`, `offset`) | JWT |
| GET | `/customers/export` | Exporta leads como JSON | JWT |
| GET | `/customers/export/xlsx` | Exporta leads como planilha Excel (.xlsx) | JWT |
| POST | `/customers/bulk-message` | Envia mensagem WhatsApp em massa para leads | JWT |
| GET | `/customers/{id}` | Busca cliente | JWT |
| DELETE | `/customers/{id}` | Exclui cliente + conversas + mensagens | JWT |


### Conversations

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| POST | `/conversations/` | Cria conversa para um cliente da mesma empresa (`{ "customer_id": 1 }`) | JWT |
| GET | `/conversations/` | Lista conversas da empresa (cliente, ultima mensagem, contagem, ordenado por `updated_at` desc). Filtros: `status` (`open`, `pending_agent`, `agent`, `closed`), `q` (nome/telefone do cliente), `limit`, `offset` | JWT |
| GET | `/conversations/filter/?status=open` | Filtra por status (`open`, `pending_agent`, `closed`) | JWT |
| GET | `/conversations/{id}` | Busca conversa (dados enriquecidos) | JWT |
| PATCH | `/conversations/{id}` | Atualiza status da conversa (`{ "status": "closed" }`) | JWT |
| DELETE | `/conversations/{id}` | Exclui conversa | JWT |
| POST | `/conversations/{id}/assume` | Assume atendimento manual (desabilita IA na conversa) | JWT |
| POST | `/conversations/{id}/pause-workflow` | Cancela PendingFlow ativo da conversa | JWT |

**Resposta enriquecida** (`_to_response` em `app/routers/conversation_router.py`):
`id, company_id, customer_id, status, created_at, updated_at, customer`
({id, name, phone}), `last_message`, `last_message_at`, `message_count`,
`transfers` (lista de `ConversationTransferResponse`: id, action, actor_type, user_name, created_at).

A criacao retorna **404** se o cliente nao existir ou pertencer a outra empresa.

Status possiveis: `open` (ativa), `pending_agent` (aguardando humano — handoff),
`closed` (fechada).

A atualizacao de status (`PATCH`) registra automaticamente um `ConversationTransfer`
(qundo aplicavel): `pending_agent→open` = **assumed**, `open/pending_agent→closed` =
**closed**, `closed→open` = **reopened**.

### Messages

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/messages/conversation/{id}` | Lista mensagens de uma conversa | JWT |
| POST | `/messages/` | Cria mensagem | JWT |
| POST | `/messages/conversation/{id}/reply` | Resposta **manual** do atendente: envia pelo WhatsApp (Evolution) e registra como `sender_type="agent"` | JWT |
| GET | `/messages/{id}` | Busca mensagem | JWT |
| PATCH | `/messages/{id}` | Atualiza conteudo | JWT |
| DELETE | `/messages/{id}` | Exclui mensagem | JWT |

### Webhook

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| POST | `/webhook/whatsapp/{company_id}` | Webhook da Evolution API | Token de decode |

### Dashboard

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/dashboard/` | Metricas da empresa: companies, customers, conversations (`open_conversations`, `pending_conversations`, `agent_conversations`, `closed_conversations`), messages, workflows, executions + series dos ultimos 7 dias: `messages_last_7_days` (`[{date, count}]`), `executions_last_7_days` (`[{date, success, error}]`) | JWT |

### Workflows

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/workflows/` | Lista workflows (busca por nome `q`, `limit`, `offset`) | JWT |
| POST | `/workflows/` | Cria workflow | JWT |
| GET | `/workflows/{id}` | Busca workflow | JWT |
| PATCH | `/workflows/{id}` | Atualiza workflow | JWT |
| DELETE | `/workflows/{id}` | Deleta workflow | JWT |
| GET | `/workflows/{id}/executions` | Lista execucoes | JWT |
| GET | `/workflows/node-types` | Tipos de nodes disponiveis | JWT |
| POST | `/workflows/{id}/run` | Executa teste de workflow (seguro por padrao) | JWT |

#### Teste de workflow

```json
{
  "payload": {
    "message": { "text": "Ola! Preciso de ajuda com os planos." },
    "customer": "5511999999999",
    "phone": "5511999999999"
  },
  "dry_run": true
}
```

`dry_run` é `true` por padrao. Nesse modo, o motor gera a resposta, mas simula
WhatsApp, espera e handoff. Enviar `dry_run: false` e uma opt-in explicita para
clientes autenticados e permite os efeitos normais do workflow.

### Executions

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
> **Nao implementado:** nao existe router global `/executions/{id}`. As execucoes
> confirmadas pelo codigo sao listadas por `GET /workflows/{id}/executions`.

### Knowledge

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/knowledge/` | Lista documentos (busca por nome/descricao `q`, `limit`, `offset`) | JWT |
| GET | `/knowledge/{id}` | Busca documento com chunks | JWT |
| POST | `/knowledge/` | Cria e indexa documento | JWT |
| POST | `/knowledge/upload` | Upload de arquivo (PDF, DOCX, TXT, CSV, MD, etc.) para knowledge | JWT |
| PATCH | `/knowledge/{id}` | Atualiza documento (+ re-embed se conteudo mudar) | JWT |
| DELETE | `/knowledge/{id}` | Deleta documento e chunks | JWT |
| POST | `/knowledge/search` | Busca semantica | JWT |

### Templates de Workflow

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/templates/` | Lista templates disponiveis | Nao |
| GET | `/templates/{id}` | Detalhe do template | Nao |
| POST | `/templates/{id}/use` | Cria workflow a partir do template | JWT |

### Users (gestao de equipe)

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/users/` | Lista membros da equipe (busca `q`, `limit`, `offset`) | JWT |
| POST | `/users/` | Cria membro da equipe | JWT (gestor+) |
| PATCH | `/users/{id}` | Atualiza papel/senha | JWT (gestor+) |
| DELETE | `/users/{id}` | Remove membro da equipe | JWT (gestor+) |

### Departments (setores)

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/departments/` | Lista setores da empresa | JWT |
| POST | `/departments/` | Cria setor | JWT |
| PATCH | `/departments/{id}` | Atualiza setor | JWT |
| DELETE | `/departments/{id}` | Exclui setor | JWT |

### Config AI (resolucao por usuario)

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/config/ai/allowed` | Provedores de IA permitidos para o usuario | JWT |
| GET | `/config/ai/effective` | Config efetiva de IA do usuario (resolucao user->company->platform->.env) | JWT |

### Agenda da Secretaria IA

Permissoes (papel + propriedade): ler e criar sao abertos a qualquer papel
autenticado da empresa; **alterar/cancelar** exigem gestor (owner/admin) OU ser
o criador do compromisso; compromissos de WhatsApp (sem criador) so a gestao
altera/cancela. `PUT /agenda/config` e exclusivo de gestores. Sem permissao: 403.

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/agenda/config` | Configuração de agenda da empresa (default se não criada) | JWT |
| PUT | `/agenda/config` | Cria/atualiza configuração (gestor) | JWT gestor |
| GET | `/agenda/availability?date=YYYY-MM-DD` | Slots livres para a data | JWT |
| GET | `/agenda/appointments` | Lista compromissos (filtros `date_from`/`date_to`/`status`, `skip`/`limit`) | JWT |
| POST | `/agenda/appointments` | Cria compromisso (operador; cria manual mesmo sem agenda ativa) | JWT |
| GET | `/agenda/appointments/{id}` | Detalhe do compromisso | JWT |
| PATCH | `/agenda/appointments/{id}` | Altera compromisso (data/horario/status/etc.) | JWT gestor ou criador |
| DELETE | `/agenda/appointments/{id}` | Cancela (soft delete) e registra historico | JWT gestor ou criador |

- **Config:** `enabled`, `timezone`, `schedule` (`{"mon":["08:00","12:00"]}`),
  `slot_duration` (min), `min_advance` (min), `blocked`
  (`[{"date":"YYYY-MM-DD","start":"HH:MM","end":"HH:MM"}]`),
  `confirmation_message`, e (8.6b) `confirmation_required` (bool),
  `confirmation_expiry_hours` (int; 0 = nunca), `confirmation_request_message`
  (com `{nome}`/`{servico}`/`{data}`/`{horario}`), `reminders_enabled` (bool),
  `reminder_hours` (lista de horas), `reminder_message`, `whatsapp_number`.
  `PUT` valida fuso, janelas, duracao, antecedencia e bloqueios antes de gravar.
- **Disponibilidade:** respeita janela do dia, bloqueios, conflitos com
  compromissos ativos (`scheduled`/`confirmed`/`awaiting_confirmation`) e
  `min_advance`.
- **Status:** `scheduled` / `awaiting_confirmation` / `confirmed` / `completed` /
  `canceled`. `scheduled`, `awaiting_confirmation` e `confirmed` sao considerados
  ativos para conflito. `origin`: `manual` / `whatsapp` / `workflow`
  (identifica agendamento via WhatsApp).
- **Criacao/alteração via rota** ignora `min_advance` (operador). A IA (tools da
  Fase 8.6) chama o servico com `skip_min_advance=False`.

### IA — function calling da Agenda (pipeline de atendimento)

Quando a empresa tem `agenda_config.enabled` ativo, o pipeline de atendimento
(`conversation_service`) e o nó **ai** do Workflow Engine
(`app/services/nodes/context.py:ask_ai`) enviam as tools abaixo ao provedor de IA
(`llm.generate_reply_with_tools`, OpenAI-compativel). O executor é
`app/services/agenda_tools.py`.

Com `confirmation_required` ativo (default), `criar_agendamento` cria com status
`awaiting_confirmation`; `alterar_agendamento` (mudanca de data/horario) e
`cancelar_agendamento` criam pendencia em `pending_appointment_actions`. Em todos
os casos o sistema envia um pedido de confirmacao ao cliente e intercepta a
resposta (`CONFIRMAR`/`CANCELAR`) no webhook antes da IA
(`app/services/agenda_confirmation.py`): a acao so e efetivada com o consentimento
real do cliente; mudancas apenas de `service`/`notes` sao aplicadas direto.

| Tool | Quando usar |
|------|-------------|
| `verificar_disponibilidade` | Listar horários livres de uma data (validar antes de criar/remarcar) |
| `consultar_agenda` | Listar compromissos (filtro por período/status) |
| `criar_agendamento` | Criar um compromisso (`origin=whatsapp`, `actor_type=system`; provisorio ate confirmar) |
| `alterar_agendamento` | Remarcar data/horario (pendente de confirmacao) ou ajustar servico/notas |
| `cancelar_agendamento` | Cancelar um compromisso (pendente de confirmacao) |

- A IA **nunca confirma** um horário sem ele estar em `build_slots` no momento
  da criacao (fim-a-fim: disponibilidade -> criacao).
- Se o provedor rejeitar `tools` (400/404/422), cai em `generate_reply` normal
  (sem tools), preservando o atendimento.
- Sem agenda ativa, nenhuma tool e enviada (comportamento identico ao anterior).

### Health (operacional, sem JWT)

| Metodo | URL | Descricao |
|--------|-----|-----------|
| GET | `/health` | Liveness do processo HTTP |
| GET | `/health/db` | Readiness do banco configurado |
| GET | `/health/redis` | Readiness do Redis |
| GET | `/health/evolution` | Alcance/autenticacao da Evolution |
| GET | `/health/llm` | Coerencia da configuracao global do LLM, sem chamar o modelo |

Os checks de dependencia retornam `503` quando indisponiveis e nunca expõem
segredos. Pelo nginx de producao, use o prefixo `/api`, por exemplo
`/api/health/db`.

### Audit Logs

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/audit-logs/` | Lista registros de auditoria (filtros: user_id, action, entity; paginacao limit/offset) | JWT gestor |

Acoes registradas: auth.register, auth.login, auth.change_password, auth.forgot_password,
auth.reset_password, user.create/update/delete, config.update, config.update_business_hours,
workflow.create/update/delete/run, platform.clear_errors, platform.reset_password,
platform.update_provider, platform.update_user_ai_config.

## Autenticacao

Todos os endpoints protegidos exigem header:
```
Authorization: Bearer <token>
```

## Formato de Resposta

### Sucesso
```json
{
  "id": 1,
  "name": "Meu Workflow",
  "status": "success"
}
```

### Erro
```json
{
  "detail": "Mensagem de erro"
}
```

## Tamanho Maximo

- `MAX_MESSAGE_LENGTH = 4096` caracteres

## Administração da plataforma

Todos os endpoints abaixo exigem JWT de um operador global e não devolvem
chaves, prompts ou conteúdo de conversas.

| Método | Rota | Finalidade |
|--------|------|------------|
| GET | `/platform-admin/overview` | Totais globais e estado público das credenciais |
| GET | `/platform-admin/users` | Usuários cadastrados e empresa vinculada |
| GET | `/platform-admin/providers` | Estado público de cada provedor suportado |
| PUT | `/platform-admin/providers/{provider}` | Cadastra/atualiza modelo, URL, chave cifrada e disponibilidade |
| POST | `/platform-admin/providers/deepseek/balance` | Consulta saldo oficial do DeepSeek, sem expor a chave |
| GET | `/platform-admin/user-ai-config` | Lista políticas de IA de todos os usuários |
| GET | `/platform-admin/user-ai-config/{user_id}` | Política de IA de um usuário específico |
| PUT | `/platform-admin/user-ai-config/{user_id}` | Cria/atualiza a política de IA de um usuário |
| GET | `/platform-admin/errors` | Execuções com erro (paginado; filtros `company_id`/`workflow_id`) |
| DELETE | `/platform-admin/errors` | Remove todas as execuções com erro |
| POST | `/platform-admin/users/{user_id}/reset-password` | Gera senha provisória do usuário (retornada **uma única vez**) |

### Reset de senha pelo operador

- `POST /platform-admin/users/{user_id}/reset-password` (JWT de operador global).
- Gera uma senha provisória com `secrets.token_urlsafe(12)`, define o hash no
  `users.password_hash` e **retorna nessa única resposta**: `{ user_id, name, message, temporary_password }`.
- A senha não é enviada por email nem gravada em log. O operador deve repassá-la
  ao usuário, que troca no `/conta`.
- Sem revogação de sessões ativas (o sistema não versiona tokens); o efeito é
  imediato apenas para **novos logins**.
