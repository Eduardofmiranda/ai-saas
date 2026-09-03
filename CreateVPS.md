# CreateVPS — Criação da VPS do Zero (FluxoIA)

> Guia para **criar/reinstalar o servidor de produção do zero**, incluindo o
> **reset completo** (apagar tudo) e o refazer passo a passo.
>
> Baseado no deploy real (03/09/2026, Hostinger, IP `2.25.122.157`).
> Tudo aqui é **IMPLEMENTADO** (validado na prática).

---

## Parte 0 — Reset completo (apagar tudo)

> ⚠️ **Antes de apagar**, confirme que anotou o `.env` e as chaves em local seguro.
> Este procedimento apaga **banco de dados, volumes, WhatsApp conectado e toda a
> instalação**. Nada retorna depois.

### 0.1 Apagar containers, volumes e redes

Na VPS (`cd /opt/ai-saas`):

```bash
cd /opt/ai-saas

# Para todos os containers e remove VOLUMES (banco, WhatsApp) e redes
docker compose -f docker-compose.evolution.yml down -v
docker compose down -v

# Confirma que nada sobrou
docker ps -a
```

### 0.2 Apagar os volumes órfãos (opcional, força limpeza)

```bash
# Remove volumes que tenham ficado órfãos (postgres_data, evolution_*)
docker volume prune -f
```

### 0.3 Apagar a pasta do projeto e as imagens (limpeza total)

```bash
# Remove o diretório do projeto (todo o código + .env)
rm -rf /opt/ai-saas

# (Opcional) remove imagens para começar 100% do zero
docker system prune -a -f
```

---

## Parte 1 — Pré-requisitos

### 1.1 Configuração recomendada

| Recurso | Mínimo | Recomendado |
|---------|--------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disco | 20 GB SSD | 40 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

Provedor usado no deploy real: **Hostinger**. (DigitalOcean / Vultr / Hetzner equivalentes.)

### 1.2 Firewall do provedor

Libere no painel do provedor (ex.: Hostinger > Security > Firewall):

| Porta | Serviço |
|-------|---------|
| **22** | SSH |
| **80** | Frontend (nginx) |
| **8080** | Evolution API (WhatsApp/QR) |

> Sem a **8080** a Evolution funciona para o backend, mas o **QR não abre fora**
> da VPS. Sem a **22**, você não consegue entrar.

### 1.3 Acessar a VPS

```bash
ssh root@SEU_IP
```

> **Dica:** gere uma chave SSH local e copie para evitar digitar a senha:
> `ssh-keygen` (local) + `ssh-copy-id root@SEU_IP`.

---

## Parte 2 — Instalação da base

### 2.1 Atualizar o sistema

```bash
apt update && apt upgrade -y
```

### 2.2 Instalar Docker + Docker Compose v2

```bash
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker

# Confere versões
docker --version
docker compose version
```

### 2.3 Instalar Git

```bash
apt install git -y
```

---

## Parte 3 — Baixar o código

```bash
cd /opt
git clone https://github.com/Eduardofmiranda/ai-saas.git
cd ai-saas

# IMPORTANTE: ficar no branch main acompanhando upstream (evita detached HEAD)
git fetch origin
git switch -C main origin/main
```

---

## Parte 4 — Criar o `.env`

```bash
cp .env.production.example .env
nano .env
```

### Valores essenciais

| Variável | Valor correto | De onde vem |
|----------|---------------|-------------|
| `DATABASE_URL` | `postgresql://postgres:SUA_SENHA@postgres:5432/ai_saas` | Postgres LOCAL (host `postgres`) |
| `POSTGRES_PASSWORD` | mesma senha do `DATABASE_URL` | você define |
| `REDIS_URL` | `redis://redis:6379/0` | Redis interno — **MANTENHA** |
| `SECRET_KEY` | `openssl rand -hex 32` | gerado na VPS |
| `SECRET_ENCRYPTION_KEY` | `openssl rand -hex 32` | gerado na VPS (DIFERENTE do SECRET_KEY) |
| `DEFAULT_AI_API_KEY` | chave da Groq | console.groq.com |
| `EVOLUTION_BASE_URL` | `http://evolution:8080` | Evolution interna |
| `EVOLUTION_API_KEY` | chave **da Evolution** (NÃO a Groq) | você define/gera |
| `EVOLUTION_AUTH_KEY` | mesma da Evolution | você define/gera |
| `EVOLUTION_INSTANCE` | `flowai` (ou o nome que criar) | você define |

### Gerar as chaves (na VPS)

```bash
openssl rand -hex 32   # SECRET_KEY
openssl rand -hex 32   # SECRET_ENCRYPTION_KEY
openssl rand -hex 32   # EVOLUTION_AUTH_KEY / EVOLUTION_API_KEY (uma chave própria)
```

> **⚠️ Regras de segurança (aprendidas no deploy real):**
> - `SECRET_KEY` **≠** `SECRET_ENCRYPTION_KEY` (valores distintos).
> - **NUNCA** use a chave da Groq como `EVOLUTION_API_KEY`. A Groq fica **somente**
>   em `DEFAULT_AI_API_KEY`. A Evolution tem a **própria** chave.
> - `SECRET_KEY`/`SECRET_ENCRYPTION_KEY` **não podem mudar** depois de salvar
>   dados criptografados (quebra a descriptografia). Defina correto de primeira.

> **Nota sobre `EVOLUTION_SERVER_URL` / `EVOLUTION_DATABASE_URI`:** estas variáveis
> no template **não são lidas pelo código** (o compose usa `SERVER_URL` e
> `DATABASE_CONNECTION_URI` hardcoded). Pode deixar como estiver — não afetam.

---

## Parte 5 — Subir a stack principal

```bash
cd /opt/ai-saas
docker compose up -d --build
docker compose ps
```

### Serviços esperados

| Container | Health | Porta |
|-----------|--------|-------|
| ai-saas-postgres | healthy | 5432 (interna) |
| ai-saas-redis | healthy | 6379 (interna) |
| ai-saas-backend | healthy | 8000 |
| ai-saas-frontend | healthy | 80 |
| ai-saas-celery-worker | Up (healthcheck desabilitado) | — |
| ai-saas-celery-beat | Up (healthcheck desabilitado) | — |

> **Banco:** o deploy usa **Postgres local** (serviço `postgres`, volume
> `postgres_data`). **NÃO usa Supabase** (ver `docs/06-banco-de-dados.md`).

> **As tabelas são criadas automaticamente no boot** (o backend roda
> `Base.metadata.create_all` no startup via `lifespan` em `app/main.py`).
> **Não é preciso rodar `create_all` manualmente.**

Confirme as tabelas criadas:

```bash
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

Esperado: `companies, company_configs, users, customers, conversations,
messages, workflows, executions, pending_flows, knowledge, knowledge_chunks`
(e talvez `alembic_version`, inofensivo).

---

## Parte 6 — Subir a Evolution API (WhatsApp)

> A Evolution usa **compose separado** (`docker-compose.evolution.yml`).
> Pontos cruciais (aprendidos no deploy real):

1. **NÃO usa `env_file: .env`** — variáveis definidas explicitamente no compose
   (evita vazar as chaves do app, ex.: Groq) e conflitar com `AUTHENTICATION_API_KEY`.
2. Usa **`EVOLUTION_AUTH_KEY`** (do `.env`) como `AUTHENTICATION_API_KEY`.
3. **Conecta na MESMA rede do backend** (`ai-saas_ai-saas-network`, external) —
   sem isso o backend não alcança `http://evolution:8080` (principal bug real).
4. `DATABASE_ENABLED=false` com `DATABASE_CONNECTION_URI` apontando para um banco
   **separado** `evolution` (a Evolution roda Prisma e precisa de schema vazio —
   se apontar para `ai_saas`, falha com P3005 "schema not empty").

```bash
docker compose -f docker-compose.evolution.yml up -d
docker ps | grep evolution   # deve estar Up
```

Teste de conectividade backend → Evolution:

```bash
docker exec ai-saas-backend python -c "import urllib.request; print(urllib.request.urlopen('http://evolution:8080/', timeout=5).status)"
# Esperado: 200
```

---

## Parte 7 — Configurar instância e QR (WhatsApp)

> A Evolution v2.3.7 (`evoapicloud/evolution-api:v2.3.7`) usa `EVOLUTION_AUTH_KEY`
> como chave (`apikey`). **NÃO** requer ativação de licença (isso é v2.4.0+).

### 7.1 Conferir a chave no container

```bash
docker exec evolution sh -c 'echo $AUTHENTICATION_API_KEY'   # não pode estar vazia
```

### 7.2 Criar a instância

```bash
KEY="$(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"
curl -s -X POST http://127.0.0.1:8080/instance/create \
  -H "apikey: $KEY" -H 'Content-Type: application/json' \
  -d '{"instanceName":"flowai","qrcode":true,"integration":"WHATSAPP-BAILEYS"}'
```

> **`integration: "WHATSAPP-BAILEYS"` é OBRIGATÓRIO** na v2.3.7 — sem ele retorna
> "Invalid integration".

### 7.3 Obter o QR (expira em ~1 min)

```bash
cd /opt/ai-saas
KEY="$(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8080/instance/connect/flowai" -H "apikey: $KEY" \
  | python3 -c "import sys,json,base64; d=json.load(sys.stdin); b=d['qrcode']['base64'].split(',',1)[1]; open('/opt/ai-saas/qrcode.png','wb').write(base64.b64decode(b)); print('QR salvo')"
```

Baixe local e escaneie:

```bash
# na sua máquina local
scp root@SEU_IP:/opt/ai-saas/qrcode.png .
```

> **Se o QR expirar** (KeyError 'qrcode'), rode o `connect` novamente — expira
> em ~20–60s. **Apague `qrcode.png`** após escanear (é sensível).

### 7.4 Escanear

1. WhatsApp no celular → **Aparelhos conectados > Conectar aparelho**.
2. Escaneie o QR.

### 7.5 Configurar o webhook

```bash
KEY="$(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"
curl -s -X POST http://127.0.0.1:8080/webhook/set/flowai \
  -H "apikey: $KEY" -H 'Content-Type: application/json' \
  -d '{"webhook":{"enabled":true,"url":"http://backend:8000/webhook/whatsapp/1","events":["MESSAGES_UPSERT","QRCODE_UPDATED","CONNECTION_UPDATE"]}}'
```

> **`"enabled": true` é OBRIGATÓRIO** — sem ele retorna 400 `webhook requires
> property "enabled"`.
>
> **URL real do backend:** `POST /webhook/whatsapp/{company_id}` (ex.: `1` =
> primeira empresa). `/webhook/evolution` **NÃO existe** no código.

---

## Parte 8 — Acessar e validar

1. Acesse `http://SEU_IP`.
2. Faça **cadastro** (cria a empresa automaticamente).
3. Em **Configurações**, confirme a Evolution (URL `http://evolution:8080`, chave
   da Evolution, instância `flowai`) e a IA (Groq).
4. Crie/ative um workflow.
5. Envie mensagem no WhatsApp conectado → deve responder.

Checagens rápidas:

```bash
curl http://localhost:8000/              # {"status":"online"}
curl -s http://localhost:8080/instance/connectionState/flowai -H "apikey: $(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"   # state:"open"
```

---

## Parte 9 — Atualizações futuras (deploy incremental)

```bash
cd /opt/ai-saas
git fetch origin
git switch -C main origin/main
docker compose up -d --build
docker compose -f docker-compose.evolution.yml up -d
```

### O que sobrevive a cada atualização

| Camada | Sobrevive? | Motivo |
|--------|------------|--------|
| `.env` | Sim | gitignored; `git switch` não toca o arquivo |
| Banco Postgres local | Sim | volume `postgres_data` |
| WhatsApp conectado (instância) | Sim | volumes `evolution_instances`/`evolution_store` |
| Tabelas da Evolution (banco `evolution`) | Sim | mesmo volume do postgres |

### Regras de ouro

1. **NÃO rode `./deploy-vps.sh`** se o `.env` já existe — ele regenera
   `SECRET_KEY`/`SECRET_ENCRYPTION_KEY` se ausentes, o que **quebraria a
   descriptografia** das chaves salvas. Use os comandos manuais acima.
2. **NÃO delete o `.env`** nem os volumes da Evolution.
3. `docker compose down` (sem `-v`) apaga containers mas **mantém** o volume
   `postgres_data` / dados.

### Rollback

```bash
cd /opt/ai-saas
git log --oneline -5
git checkout <hash_do_ultimo_bom>
docker compose up -d --build
```

---

## Troubleshooting (o que quebrou no deploy real)

### Evolution em loop / erro de Prisma
- `DATABASE_CONNECTION_URI resolved to empty string` → falta `EVOLUTION_AUTH_KEY`
  no `.env`, ou o compose usou `env_file` com variáveis erradas.
- `P3005 database schema is not empty` → apontou para o banco `ai_saas` (com
  tabelas). Apontar para o banco separado `evolution` (passo 6).

### 401 Unauthorized ao criar instância
A `apikey` não bate com o `AUTHENTICATION_API_KEY` do container. Confira com
`docker exec evolution sh -c 'echo $AUTHENTICATION_API_KEY'`. NÃO use a Groq.

### Backend não acha `evolution`
`http://evolution:8080` → "Name or service not known" = não está na mesma rede
(`ai-saas_ai-saas-network`). Verifique o compose.

### QR expira
Rode `connect` de novo (expira em ~20–60s).

### Não conecta via IP
Libere as portas 80/8080/22 no firewall do provedor (passo 1.2).

---

## Referência — comandos úteis

```bash
docker compose logs -f backend
docker compose logs -f celery-worker
docker compose exec redis redis-cli ping
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import text; print(engine.connect().execute(text('SELECT 1')).scalar())"
curl http://localhost:8000/
curl http://localhost:8080/
```
