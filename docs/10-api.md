# 10 — API REST

Base URL: `http://localhost:8000`

## Endpoints

### Autenticacao

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| POST | `/auth/register` | Cadastro (cria empresa) | Nao |
| POST | `/auth/login` | Login | Nao |

### Company

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/company/` | Busca empresa do usuario | JWT |
| PATCH | `/company/` | Atualiza empresa | JWT |

### Config (por empresa)

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/config/` | Busca configuracoes da empresa | JWT |
| PATCH | `/config/` | Atualiza configuracoes | JWT |

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
| GET | `/customers/by-phone/{phone}` | Busca por telefone | JWT |

### Conversations

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/conversations/` | Lista conversas (filtro por customer_id) | JWT |
| GET | `/conversations/{id}` | Busca conversa com mensagens | JWT |
| POST | `/conversations/{id}/close` | Fecha conversa | JWT |

### Messages

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/messages/conversation/{id}` | Lista mensagens | JWT |
| POST | `/messages/` | Cria mensagem | JWT |
| GET | `/messages/pending` | Busca mensagens aguardando | JWT |

### Webhook

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| POST | `/webhook/whatsapp/{company_id}` | Webhook da Evolution API | Token de decode |

### Dashboard

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/dashboard/stats` | Estatisticas da empresa | JWT |

### Workflows

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/workflows/` | Lista workflows | JWT |
| POST | `/workflows/` | Cria workflow | JWT |
| GET | `/workflows/{id}` | Busca workflow | JWT |
| PUT | `/workflows/{id}` | Atualiza workflow | JWT |
| DELETE | `/workflows/{id}` | Deleta workflow | JWT |
| GET | `/workflows/{id}/executions` | Lista execucoes | JWT |
| GET | `/workflows/node-types` | Tipos de nodes disponiveis | JWT |
| POST | `/workflows/{id}/run` | Executa workflow | JWT |

### Executions

| Metodo | URL | Descricao | Auth |
|--------|-----|-----------|------|
| GET | `/executions/{id}` | Busca execucao | JWT |

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
