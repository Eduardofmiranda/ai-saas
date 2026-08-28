# Teste E2E sem WhatsApp real (Mock Evolution)

Antes de conectar um número de WhatsApp real (e correr risco de banimento),
use o **mock da Evolution API**. Ele simula tanto o recebimento quanto o
envio de mensagens, permitindo testar todo o fluxo do backend localmente.

## O que o mock faz

- **Captura** as mensagens que o backend tenta enviar (para inspecao).
- **Simula** um cliente enviando mensagem, disparando o webhook do backend.
- **0 risco** de banimento e **0 custo** - nao precisa de numero real.

## Como usar

### 1. Suba o backend apontando para o mock

```bash
# Windows (PowerShell) na pasta do projeto:
$env:EVOLUTION_BASE_URL = "http://localhost:8090"
$env:EVOLUTION_API_KEY = "mock"
$env:EVOLUTION_INSTANCE = "flowai"
uvicorn app.main:app --reload --port 8000
```

### 2. Suba o mock em outro terminal

```bash
python mock_evolution_server.py
# Mock rodando em http://localhost:8090
```

### 3. Crie um workflow e ative-o

- Acesse `http://localhost:5173` (frontend) ou use a API.
- Use um template (ex: "Atendimento Basico").
- **Configure a IA como `mock`** para nao gastar tokens:
  - Na config da empresa: `ai_provider = mock` (retorna resposta de demonstracao).
  - Ou deixe com Groq real para testar a IA de verdade.

### 4. Simule o cliente enviando uma mensagem

```bash
curl -X POST http://localhost:8090/simulate_message ^
  -H "Content-Type: application/json" ^
  -d "{\"company_id\": 1, \"phone\": \"5511999999999\", \"text\": \"ola, quero ajuda\"}"
```

### 5. Veja a resposta "enviada" pelo backend

Abra no navegador:

```bash
# Mensagens que o backend tentou enviar:
curl http://localhost:8090/sent_messages
```

Ou consuma via API:

```bash
curl http://localhost:8090/sent_messages | python -m json.tool
```

## Resultado esperado

```
1. /simulate_message  ->  chama POST /webhook/whatsapp/1 do backend
2. backend processa o workflow
3. no "ai" gera resposta (mock ou Groq)
4. no "whatsapp_send" chama  POST /message/sendText/flowai (capturado pelo mock)
5. GET /sent_messages  ->  mostra a resposta enviada
```

## Configuracoes do mock (variaveis de ambiente)

| Variavel | Padrao | Descricao |
|----------|--------|-----------|
| `MOCK_EVOLUTION_PORT` | `8090` | Porta do mock |
| `MOCK_BACKEND_URL` | `http://localhost:8000` | URL do backend para o webhook |

Se rodar dentro do Docker, use `MOCK_BACKEND_URL=http://backend:8000`.
