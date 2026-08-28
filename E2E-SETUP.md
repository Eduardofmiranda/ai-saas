# Setup E2E - Teste Ponta a Ponta

> **Sobre a Evolution API:** e um projeto **open-source e self-hosted** e **gratuito**. Voce instala via Docker e conecta no seu **proprio numero de WhatsApp** escaneando um QR Code. Na versao fixada no projeto (`v2.2.3`), a `apikey` dos exemplos abaixo e a senha que VOCE define no `.env` (param `AUTHENTICATION_API_KEY`). Em versoes **2.4.0+** a instancia exige a **ativacao de licenca gratuita** e o `api_key` vem do servidor de licencas da Evolution — veja `docs/12-integracoes.md`.

## 1. Subir Evolution API (Docker)

```bash
# Na pasta do projeto:
docker compose -f docker-compose.evolution.yml up -d
```

A Evolution API estara disponivel em: `http://localhost:8080`

## 2. Criar Instancia no WhatsApp

```bash
# Criar instancia "flowai"
curl -X POST http://localhost:8080/instance/createFlowAi \
  -H "Content-Type: application/json" \
  -H "apikey: meu-secret-key-123" \
  -d '{
    "instanceName": "flowai",
    "integration": "WHATSAPP-BAILEYS",
    "qrcode": true
  }'
```

## 3. Conectar WhatsApp

1. Apos criar a instancia, voce recebera um QR Code
2. Abra o WhatsApp no celular
3. Va em **Aparelhos conectados** > **Conectar aparelho**
4. Escaneie o QR Code

## 4. Configurar Webhook

```bash
# Configurar webhook para receber mensagens
curl -X POST http://localhost:8080/webhook/setFlowai \
  -H "Content-Type: application/json" \
  -H "apikey: meu-secret-key-123" \
  -d '{
    "enabled": true,
    "url": "http://host.docker.internal:8000/webhook/whatsapp/1",
    "events": ["messages.upsert"]
  }'
```

**IMPORTANTE:** O URL do webhook deve apontar para o backend. Se estiver rodando localmente:
- Docker para localhost: use `http://host.docker.internal:8000`
- Se nao usar Docker para o backend: use `http://localhost:8000`

## 5. Atualizar .env

```env
EVOLUTION_BASE_URL=http://localhost:8080
EVOLUTION_API_KEY=meu-secret-key-123
EVOLUTION_INSTANCE=flowai
```

## 6. Rodar o Backend

```bash
# Instalar dependencias (se ainda nao fez)
pip install -r requirements.txt

# Rodar o backend
uvicorn app.main:app --reload --port 8000
```

## 7. Criar Workflow de Teste

1. Acesse `http://localhost:5173`
2. Faca login
3. Clique em "Templates"
4. Escolha "Atendimento Basico (IA)"
5. Ative o workflow

## 8. Testar

1. Envie uma mensagem para o numero do WhatsApp conectado
2. O workflow deve:
   - Receber a mensagem via webhook
   - Processar com IA (Groq)
   - Enviar a resposta automaticamente

## Troubleshooting

### Webhook nao recebe mensagens
- Verifique se a Evolution API esta rodando: `docker ps`
- Verifique os logs: `docker logs evolution`
- Teste o webhook manualmente com curl

### IA nao responde
- Verifique se a chave Groq e valida
- Verifique os logs do backend: `uvicorn app.main:app --reload`

### Erro de conexao com banco
- Verifique se o Supabase esta acessivel
- Teste a conexao: `psql "postgresql://postgres:Du297845%40%40%40@db.iedkugumqyweawhcepgt.supabase.co:5432/postgres"`
