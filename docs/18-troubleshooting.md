# 18 — Troubleshooting

> Abaixo estao problemas **reais encontrados/enfrentados nos deploys de 03/09/2026
> e 04/09/2026** e suas solucoes definitivas. Ver tambem `VPS-SETUP.md` (roteiro E2E)
> e `AGENTS.md` §7 (paridade `.env` x container) e §13 (Evolution).

## Problemas do Deploy Real

### Evolution reinicia em loop com erro do Prisma

**Erro:** `P1000: Authentication failed ... credentials for postgres are not valid`
(04/09/2026), ou `DATABASE_CONNECTION_URI resolved to empty string`, ou
`P3005 The database schema is not empty`.

**Causa (04/09/2026, fato verificado):** o entrypoint oficial da imagem
(`deploy_database.sh`) **exige** `DATABASE_PROVIDER` valido + banco **acessivel**
no startup e da `exit 1` caso contrario — mesmo com `DATABASE_ENABLED=false`.
No caso real, o `.env` tinha `POSTGRES_PASSWORD` novo, mas o hash armazenado no
postgres local era de senha antiga: `psql` local passava (via `trust`/socket) e
`psycopg2`/Prisma via rede Docker falhava. Outras causas: (1) chave
`AUTHENTICATION_API_KEY` vazia/no compose com `env_file` que vazava variaveis
erradas; (2) apontar a Evolution para o banco `ai_saas` (que ja tem as tabelas
do app) -> o Prisma da Evolution reclama de schema nao vazio.

**Solucao:**
- `docker-compose.evolution.yml` **nao usa `env_file`**; define tudo explicito.
- `AUTHENTICATION_API_KEY=${EVOLUTION_AUTH_KEY}` (chave propria, no `.env`).
- **NUNCA remover** `DATABASE_PROVIDER`/`DATABASE_CONNECTION_URI` do compose
  (sem provider → `Error: Database provider invalid` + `exit 1`).
- `DATABASE_ENABLED=false` com `DATABASE_CONNECTION_URI` apontando para um banco
  **separado** `evolution` (`postgresql://postgres:…@postgres:5432/evolution`).
- Se `P1000` com senha aparentemente certa, validar **via rede** (ex.: `psycopg2`
  a partir do backend) e realinhar o hash: `ALTER USER postgres WITH PASSWORD
  '<POSTGRES_PASSWORD do .env>';` + `--force-recreate` (restart NAO reaplica env).

### 401 Unauthorized ao criar instancia / acessar API da Evolution

**Erro:** `{"status":401,"error":"Unauthorized"}`.

**Causa:** a chave do header `apikey` nao bate com o `AUTHENTICATION_API_KEY` do
container. Regra fixa: `EVOLUTION_AUTH_KEY` (container) e `EVOLUTION_API_KEY`
(backend) devem ter o **mesmo valor** no `.env` (04/09/2026: estavam diferentes
e o setup falhava; o status chegava a responder mas o `POST /instance/create`
dava 401). Outras causas: usada a chave da Groq por engano, ou container
recriado com `.env` antigo (`restart` NAO reaplica env).

**Solucao (sem expor secrets — comparar hashes, nunca imprimir chaves):**
```bash
A=$(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-); B=$(grep '^EVOLUTION_API_KEY=' .env | cut -d= -f2-); [ "$A" = "$B" ] && echo "IGUAIS" || echo "DIFERENTES"
docker compose exec backend printenv EVOLUTION_API_KEY | md5sum
docker inspect evolution --format '{{range .Config.Env}}{{println .}}{{end}}' | grep AUTHENTICATION_API_KEY | md5sum
```
Se divergir: iguale no `.env` (mantenha o `AUTH_KEY`, copie p/ `API_KEY`) e
`docker compose up -d --no-deps --force-recreate backend celery-worker`. NAO use a chave da Groq.

### "Invalid integration" ao criar instancia

**Erro:** `{"message":["Invalid integration"]}` (400).

**Causa:** a v2.3.7 exige o campo `integration` no `POST /instance/create`.

**Solucao:** `-d '{"instanceName":"<inst>","integration":"WHATSAPP-BAILEYS","qrcode":true}'`.
O `POST /config/whatsapp/setup` do backend ja envia `integration` automaticamente
e provisiona a instancia por empresa (`inst-<company_id>`) — prefira o setup.

### Webhook da Evolution retorna 400 "webhook requires property enabled"

**Solucao:** incluir `"enabled": true` dentro do objeto `webhook`.

### Backend nao encontra `evolution` (Name or service not known)

**Causa (04/09/2026, fato verificado):** na maioria das vezes o container
`evolution` estava **parado** (`Exited`, sem `restart` policy) — e nao em rede
errada. O compose da Evolution e separado (`docker-compose.evolution.yml`); o
container aparece como "orphan" no compose principal, o que e normal.

**Solucao:** checar `docker ps -a --filter name=evolution` primeiro. Se `Exited`,
`docker compose -f docker-compose.evolution.yml up -d` (volumes preservam a
sessao). A rede deve ser `ai-saas_ai-saas-network` (external) no
`docker-compose.evolution.yml`. Validar:
```bash
docker exec ai-saas-backend python -c "import urllib.request; print(urllib.request.urlopen('http://evolution:8080/', timeout=5).status)"
# Esperado 200
```

### QR expira (KeyError 'qrcode' / 404 em outro endpoint)

**Causa:** o QR e valido por ~20-60s; os endpoints `qrcode`/`connect` variam na
v2.3.7 (`GET /instance/connect/{instance}`), e o painel nao fica em `/dashboard`.

**Solucao:** rodar de novo `POST /config/whatsapp/setup` (gera a instancia
`inst-<company_id>` + QR) ou `GET /instance/connect/<instancia-da-empresa>`
(header `apikey`) e decodificar o `base64` para PNG imediatamente, antes de expirar.

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
