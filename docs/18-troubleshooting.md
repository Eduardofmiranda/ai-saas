# 18 — Troubleshooting

> Abaixo estao problemas **reais encontrados/enfrentados no deploy de 03/09/2026**
> e suas solucoes definitivas. Ver tambem `VPS-SETUP.md` (roteiro E2E).

## Problemas do Deploy Real

### Evolution reinicia em loop com erro do Prisma

**Erro:** `DATABASE_CONNECTION_URI resolved to empty string` ou
`P3005 The database schema is not empty`.

**Causa:** (1) chave `AUTHENTICATION_API_KEY` vazia/no compose com `env_file` que
vazava variaveis erradas; (2) apontar a Evolution para o banco `ai_saas` (que ja
tem as tabelas do app) -> o Prisma da Evolution reclama de schema nao vazio.

**Solucao:**
- `docker-compose.evolution.yml` **nao usa `env_file`**; define tudo explicito.
- `AUTHENTICATION_API_KEY=${EVOLUTION_AUTH_KEY}` (chave propria, no `.env`).
- `DATABASE_ENABLED=false` com `DATABASE_CONNECTION_URI` apontando para um banco
  **separado** `evolution` (`postgresql://postgres:…@postgres:5432/evolution`).

### 401 Unauthorized ao criar instancia / acessar API da Evolution

**Erro:** `{"status":401,"error":"Unauthorized"}`.

**Causa:** a chave do header `apikey` nao bate com o `AUTHENTICATION_API_KEY` do
container (ex.: usada a chave da Groq por engano, ou `EVOLUTION_AUTH_KEY` ja estava
com outra valor quando reiniciou o container).

**Solucao:**
```bash
docker exec evolution sh -c 'echo $AUTHENTICATION_API_KEY'
```
Use exatamente esse valor no header `apikey`. NAO use a chave da Groq.

### "Invalid integration" ao criar instancia

**Erro:** `{"message":["Invalid integration"]}` (400).

**Causa:** a v2.3.7 exige o campo `integration` no `POST /instance/create`.

**Solucao:** `-d '{"instanceName":"flowai","integration":"WHATSAPP-BAILEYS","qrcode":true}'`.

### Webhook da Evolution retorna 400 "webhook requires property enabled"

**Solucao:** incluir `"enabled": true` dentro do objeto `webhook`.

### Backend nao encontra `evolution` (Name or service not known)

**Causa:** a Evolution roda em rede docker separada da do backend.

**Solucao:** conectar a Evolution a `ai-saas_ai-saas-network` (external) no
`docker-compose.evolution.yml`. Validar:
```bash
docker exec ai-saas-backend python -c "import urllib.request; print(urllib.request.urlopen('http://evolution:8080/', timeout=5).status)"
# Esperado 200
```

### QR expira (KeyError 'qrcode' / 404 em outro endpoint)

**Causa:** o QR e valido por ~20-60s; os endpoints `qrcode`/`connect` variam na
v2.3.7 (`GET /instance/connect/{instance}`), e o painel nao fica em `/dashboard`.

**Solucao:** rodar de novo `GET /instance/connect/flowai` (header `apikey`) e
decodificar o `base64` para PNG imediatamente, antes de expirar.

### Containers `unhealthy` mas rodando (celery)

**Causa:** celery-worker/beat herdavam o `HEALTHCHECK` do `Dockerfile.backend`
(checa a porta 8000, inexistente neles). Nao e falha real.

**Solucao:** `healthcheck: disable` no compose p/ celery. Frontend ganhou
healthcheck proprio. Nao e erro.

### Supabase "Network is unreachable" na VPS

**Causa:** a direct connection do Supabase resolve so IPv6; VPS sem rota IPv6
nao conecta.

**Solucao (adotada):** producao **usa o Supabase via pooler IPv4**
(`…@aws-0-<regiao>.pooler.supabase.com:5432/postgres`) para contornar a falta
de rota IPv6 na VPS. O Postgres local do docker e apenas alternativa/fallback.
(Producao = Supabase; ver docs/06.)

### "Nao conecta via IP" de fora

**Causa:** firewall do provedor (ex.: Hostinger) bloqueando as portas.

**Solucao:** liberar 80, 8080 e 22 no firewall do painel do provedor e no firewall
do SO (se ativo). Verificar com `curl http://SEU_IP/`.

## Problemas Comuns

### Backend nao inicia

**Erro:** `ModuleNotFoundError: No module named 'X'`

**Solucao:**
```bash
pip install -r requirements.txt
```

### Erro de conexao com banco

**Erro:** `sqlalchemy.exc.OperationalError: could not connect to server`

**Verificar:**
1. `DATABASE_URL` esta correto?
2. PostgreSQL esta rodando?
3. Firewall nao bloqueia porta 5432?

### Erro de JWT

**Erro:** `jwt.exceptions.DecodeError`

**Verificar:**
1. `SECRET_KEY` e a mesma usada para criar o token?
2. Token nao expirou (24h)?

### Erro de IA

**Erro:** `httpx.HTTPStatusError: 401 Unauthorized`

**Verificar:**
1. `ai_api_key` esta configurada?
2. Chave e valida no provedor?
3. Chave esta criptografada corretamente?

### Erro de WhatsApp

**Erro:** `Evolution API error: instance not found`

**Verificar:**
1. `EVOLUTION_BASE_URL` esta correto?
2. `EVOLUTION_API_KEY` e valido?
3. `EVOLUTION_INSTANCE` existe na Evolution?
4. Webhook esta configurado na Evolution?

### Frontend nao conecta ao backend

**Erro:** `Failed to fetch`

**Verificar:**
1. Backend esta rodando na porta 8000?
2. `VITE_API_BASE` esta correto?
3. CORS esta configurado?

### Docker compose nao sobe

**Erro:** `port is already allocated`

**Solucao:**
```bash
# Verificar o que esta usando a porta
netstat -ano | findstr :8000

# Matar o processo ou mudar a porta no docker-compose.yml
```

### Erro de criptografia

**Erro:** `cryptography.fernet.InvalidToken`

**Verificar:**
1. `SECRET_ENCRYPTION_KEY` e a mesma usada para criptografar?
2. Chave foi alterada depois de salvar dados criptografados? (NAO ALTERAR)

### Testes falham

**Erro:** `sqlite3.OperationalError: no such table`

**Solucao:**
```bash
pytest tests/ -xvs
# Os testes usam SQLite em memoria e criam tabelas automaticamente
```

## Logs

### Ver logs do backend (Docker)
```bash
docker compose logs -f backend
```

### Ver logs do Celery
```bash
docker compose logs -f celery-worker
```

### Ver logs do nginx (frontend)
```bash
docker compose logs -f frontend
```
