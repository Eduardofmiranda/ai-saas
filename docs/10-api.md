# 10 — API REST

Base URL direta do backend em desenvolvimento: `http://localhost:8000`.
Em producao, o frontend usa o prefixo relativo `/api` e o nginx o remove antes
de encaminhar ao backend; portanto uma chamada do navegador e `/api/config/`,
enquanto a rota FastAPI continua `/config/`.

## Endpoints

### Autenticacao

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
| POST | `/companies/` | Cria empresa | JWT |
| GET | `/companies/` | Lista somente a empresa do usuario | JWT |
| GET | `/companies/{id}` | Busca a propria empresa | JWT |
| PATCH | `/companies/{id}` | Atualiza a propria empresa | JWT |

### Config (por empresa)

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/config/` | Busca configuracoes da empresa | JWT |
| PATCH | `/config/` | Atualiza configuracoes | JWT |
| POST | `/config/ai/test` | Testa a config de IA (chama o provedor; nao persiste) | JWT |

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
| GET | `/customers/` | Lista clientes da empresa | JWT |
| GET | `/customers/{id}` | Busca cliente | JWT |


### Conversations

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/conversations/` | Lista conversas da empresa (cliente, ultima mensagem, contagem, ordenado por `updated_at` desc) | JWT |
| GET | `/conversations/filter/?status=open` | Filtra por status (`open`, `pending_agent`, `closed`) | JWT |
| GET | `/conversations/{id}` | Busca conversa (dados enriquecidos) | JWT |
| PATCH | `/conversations/{id}` | Atualiza status da conversa (`{ "status": "closed" }`) | JWT |
| DELETE | `/conversations/{id}` | Exclui conversa | JWT |

**Resposta enriquecida** (`_to_response` em `app/routers/conversation_router.py`):
`id, company_id, customer_id, status, created_at, updated_at, customer`
({id, name, phone}), `last_message`, `last_message_at`, `message_count`,
`transfers` (lista de `ConversationTransferResponse`: id, action, actor_type, user_name, created_at).

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
| GET | `/dashboard/` | Metricas da empresa: companies, customers, conversations (`open_conversations`, `pending_conversations`, `closed_conversations`), messages, workflows, executions | JWT |

### Workflows

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/workflows/` | Lista workflows | JWT |
| POST | `/workflows/` | Cria workflow | JWT |
| GET | `/workflows/{id}` | Busca workflow | JWT |
| PATCH | `/workflows/{id}` | Atualiza workflow | JWT |
| DELETE | `/workflows/{id}` | Deleta workflow | JWT |
| GET | `/workflows/{id}/executions` | Lista execucoes | JWT |
| GET | `/workflows/node-types` | Tipos de nodes disponiveis | JWT |
| POST | `/workflows/{id}/run` | Executa workflow | JWT |

### Executions

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
> **Nao implementado:** nao existe router global `/executions/{id}`. As execucoes
> confirmadas pelo codigo sao listadas por `GET /workflows/{id}/executions`.

### Knowledge

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/knowledge/` | Lista documentos | JWT |
| GET | `/knowledge/{id}` | Busca documento com chunks | JWT |
| POST | `/knowledge/` | Cria e indexa documento | JWT |
| PATCH | `/knowledge/{id}` | Atualiza documento | JWT |
| DELETE | `/knowledge/{id}` | Deleta documento e chunks | JWT |
| POST | `/knowledge/search` | Busca semantica | JWT |

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
