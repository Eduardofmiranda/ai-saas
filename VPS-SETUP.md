# Setup VPS Completo - E2E

> **Status: VALIDADO em producao (deploy real em 03/09/2026, Hostinger).**
> Este roteiro reflete o que de fato funciona, apos o primeiro deploy completo.
> Passos legitimados na pratica; nada aqui e "planejado" sem confirmacao.

## Configuracao Recomendada

| Recurso | Minimo | Recomendado |
|---------|--------|-------------|
| CPU | 1 vCPU | 2 vCPU |
| RAM | 1 GB | 2 GB |
| Disco | 20 GB SSD | 40 GB SSD |
| OS | Ubuntu 22.04 LTS | Ubuntu 24.04 LTS |

**Provedores:
- Hostinger (usado no deploy real)
- DigitalOcean / Vultr / Hetzner (similares)

> **Firewall:** nas VPS com firewall de painel (ex.: Hostinger Security >
> Firewall), libere as portas **80**, **8080** e **22**. A porta **8080** e a da
> Evolution API (necessaria para o QR e para acessar a API de fora). Se nao
> liberar, a Evolution ainda funciona para o backend, mas o QR nao abre fora.

---

## Visao arquitetural (o que de fato se instala)

| Componente | Como roda |
|------------|-----------|
| Frontend (React) | Nginx dentro de container `ai-saas-frontend` (porta 80) |
| Backend (FastAPI/uvicorn) | Container `ai-saas-backend` (porta 8000) |
| Postgres | **LOCAL** no Docker (container `ai-saas-postgres`, porta 5432 interna) |
| Redis | Container `ai-saas-redis` (porta 6379 interna) |
| Celery worker/beat | Containers `ai-saas-celery-worker` / `ai-saas-celery-beat` |
| Evolution API (WhatsApp) | Container `evolution` (porta 8080), compose separado |

> **Banco de dados:** o deploy usa **Postgres local do Docker** (padrao atual).
> O Supabase foi abandonado por causa do problema de IPv6 (a "direct connection"
> do Supabase resolve so IPv6 e VPS sem rede IPv6 nao conecta). A evolucao
> correta esta documentada em `docs/06-banco-de-dados.md`.

---

## Passo 1: Acessar a VPS

```bash
ssh root@SEU_IP
```

## Passo 2-7: Base do sistema

```bash
# Atualizar sistema
apt update && apt upgrade -y

# Instalar Docker (e Docker Compose v2 junto)
curl -fsSL https://get.docker.com | sh
systemctl enable --now docker
docker --version
docker compose version

# Instalar Git
apt install git -y

# Clonar (usa o mesmo diretorio da VPS real)
cd /opt
git clone https://github.com/Eduardofmiranda/ai-saas.git
cd ai-saas

# IMPORTANTE: garantir que esta no branch main acompanhando o upstream
# (a VPS pode ficar em detached HEAD apos clone/checkout - corrigir):
git fetch origin
git switch -C main origin/main
```

> **Dica (evita digitas senha toda vez):** gere uma chave SSH local e copie
> para a VPS (`ssh-keygen` local + `ssh-copy-id root@SEU_IP`). Usado no deploy real.

## Passo 8: Criar o .env

Use o template de producao:

```bash
cp .env.production.example .env
nano .env
```

### Valores essenciais (o que de fato importa)

| Variavel | Valor correto | De onde vem |
|----------|---------------|-------------|
| `DATABASE_URL` | `postgresql://postgres:SUA_SENHA@postgres:5432/ai_saas` | Postgres LOCAL (host `postgres`) |
| `POSTGRES_PASSWORD` | mesma senha do `DATABASE_URL` | voce define |
| `REDIS_URL` | `redis://redis:6379/0` | Redis interno (MANTENHA) |
| `SECRET_KEY` | `openssl rand -hex 32` | gerado na VPS |
| `SECRET_ENCRYPTION_KEY` | `openssl rand -hex 32` | gerado na VPS |
| `DEFAULT_AI_API_KEY` | chave da Groq | console.groq.com |
| `EVOLUTION_BASE_URL` | `http://evolution:8080` | Evolution interna |
| `EVOLUTION_API_KEY` | a **chave da Evolution** (NAO a da Groq) | voce define/genera |
| `EVOLUTION_AUTH_KEY` | a mesma da Evolution | voce define/genera |
| `EVOLUTION_INSTANCE` | `flowai` (ou o nome que criar) | voce define |

> **Nao use `EVOLUTION_SERVER_URL` nem `EVOLUTION_DATABASE_URI`** — sao variaveis
> mortas (nao lidas por codigo; ver docs/05). O compose da Evolution define
> `SERVER_URL`/`DATABASE_CONNECTION_URI` hardcoded.

### GERAR chaves URGENTEMENTE (importante)

```bash
openssl rand -hex 32   # SECRET_KEY
openssl rand -hex 32   # SECRET_ENCRYPTION_KEY
openssl rand -hex 32   # EVOLUTION_AUTH_KEY / EVOLUTION_API_KEY (uma chave propria)
```

> **⚠️ Regra de seguranca:** NUNCA use a chave da Groq como `EVOLUTION_API_KEY`
> (erro comum que ocorreu no deploy real). A Groq fica so em `DEFAULT_AI_API_KEY`.
> A Evolution tem a propria chave (`EVOLUTION_AUTH_KEY`/`EVOLUTION_API_KEY`).

> **⚠️ `SECRET_KEY` e `SECRET_ENCRYPTION_KEY` NAO podem ser iguais e NAO podem
> mudar apos salvar dados criptografados.** No deploy real ficaram iguais
> (erro a corrigir). Gere duas chaves distintas.

## Passo 9-10: Subir a stack principal

```bash
docker compose up -d --build
docker compose ps
```

Servicos esperados (todos `Up`/`healthy`):

| Container | Health | Porta |
|-----------|--------|-------|
| ai-saas-postgres | healthy | 5432 (interna) |
| ai-saas-redis | healthy | 6379 (interna) |
| ai-saas-backend | healthy | 8000 |
| ai-saas-frontend | healthy | 80 |
| ai-saas-celery-worker | Up (healthcheck desabilitado) | — |
| ai-saas-celery-beat | Up (healthcheck desabilitado) | — |

> **Sobre os healthchecks `unhealthy`:** em versoes anteriores, celery-worker e
> celery-beat herdavam o `HEALTHCHECK` do `Dockerfile.backend` (que checa a porta
> 8000, inexistente neles) e ficavam `unhealthy` **mas rodando normalmente**.
> Isso foi corrigido no compose com `healthcheck: disable`. Nao e erro real.

## Passo 11: Confirmar tabelas do banco (criadado automaticamente no boot)

> **As tabelas sao criadas automaticamente no boot do backend** (o `lifespan` em
> `app/main.py` chama `Base.metadata.create_all`). **NAO e preciso rodar
> `create_all` manualmente.** Este projeto NAO usa Alembic para criar o schema base
> (`alembic/versions` tem so migrations adicionais/idempotentes). Veja docs/06.

Apenas confira as tabelas (opcional):

```bash
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

Deve listar: `companies, company_configs, users, customers, conversations,
messages, workflows, executions, pending_flows, knowledge, knowledge_chunks`
(e possivelmente `alembic_version`, que e inofensivo).

## Passo 12: Subir a Evolution API (WhatsApp)

A Evolution usa **compose separado** (`docker-compose.evolution.yml`). Pontos
cruciais aprendidos no deploy real:

1. **NAO usa `env_file: .env`** — todas as variaveis sao definidas
   explicitamente no compose. Isso evita vazar as chaves do app (ex.: Groq)
   para dentro da Evolution e conflitar com o `AUTHENTICATION_API_KEY`.
2. **Usa `EVOLUTION_AUTH_KEY`** (do `.env`) como `AUTHENTICATION_API_KEY`.
3. **Conecta na MESMA rede do backend** (`ai-saas_ai-saas-network`, external)
   para que o backend alcance `http://evolution:8080`. Sem isso o WhatsApp
   nunca conecta (foi o principal bug).
4. `DATABASE_ENABLED=false` com `DATABASE_CONNECTION_URI` apontando para um
   banco **separado** `evolution` (a Evolution roda o Prisma e precisa de um
   schema vazio — se apontar para `ai_saas` que ja tem tabelas, falha com
   P3005 "schema not empty").

Subir:

```bash
docker compose -f docker-compose.evolution.yml up -d
docker ps | grep evolution   # deve estar Up
```

Teste de conectividade backend -> Evolution:

```bash
docker exec ai-saas-backend python -c "import urllib.request; print(urllib.request.urlopen('http://evolution:8080/', timeout=5).status)"
# Esperado: 200
```

## Passo 13: Configurar a instancia e o QR

> A Evolution v2.3.7 (imagem `evoapicloud/evolution-api:v2.3.7`) usa a chave que
> voce definiu como `EVOLUTION_AUTH_KEY` para autenticar (`apikey`). NAO requer
> ativacao de licenca (isso e so v2.4.0+).

### 1) Conferir a chave da Evolution no container

```bash
docker exec evolution sh -c 'echo $AUTHENTICATION_API_KEY'
# Deve imprimir a chave (NAO vazia)
```

### 2) Criar a instancia

```bash
KEY="$(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"
curl -s -X POST http://127.0.0.1:8080/instance/create \
  -H "apikey: $KEY" -H 'Content-Type: application/json' \
  -d '{"instanceName":"flowai","qrcode":true,"integration":"WHATSAPP-BAILEYS"}'
```

> **`integration` e obrigatorio** na v2.3.7 — sem ele retorna
> "Invalid integration".

### 3) Obter o QR (expira em ~1 min)

```bash
curl -s "http://127.0.0.1:8080/instance/connect/flowai" -H "apikey: $KEY" \
  | python3 -m json.tool   # base64 -> imagem PNG do QR
```

Para salvar o PNG e abrir localmente:

```bash
cd /opt/ai-saas
KEY="$(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"
curl -s "http://127.0.0.1:8080/instance/connect/flowai" -H "apikey: $KEY" \
  | python3 -c "import sys,json,base64; d=json.load(sys.stdin); b=d['qrcode']['base64'].split(',',1)[1]; open('/opt/ai-saas/qrcode.png','wb').write(base64.b64decode(b)); print('salvo')"
```

Baixe para a maquina local (`scp root@SEU_IP:/opt/ai-saas/qrcode.png .`) e
escaneie com o celular.

> **Se o QR expirar** (KeyError 'qrcode' no JSON), rode o comando `connect`
> novamente para gerar um novo. Ele expira em ~20-60s.

### 4) Escanear

1. Abra o **WhatsApp** no celular
2. **Aparelhos conectados > Conectar aparelho**
3. Escaneie o QR (imagem PNG)

### 5) Configurar o webhook (para o backend receber mensagens)

```bash
KEY="$(grep '^EVOLUTION_AUTH_KEY=' .env | cut -d= -f2-)"
curl -s -X POST http://127.0.0.1:8080/webhook/set/flowai \
  -H "apikey: $KEY" -H 'Content-Type: application/json' \
  -d '{"webhook":{"enabled":true,"url":"http://backend:8000/webhook/whatsapp/1","events":["MESSAGES_UPSERT","QRCODE_UPDATED","CONNECTION_UPDATE"]}}'
```

> **`"enabled": true` e obrigatorio** — sem ele retorna 400
> 'webhook requires property "enabled"'.

> **URL do webhook:** o endpoint real do backend e
> **`POST /webhook/whatsapp/{company_id}`** (o `company_id` da plataforma, ex.:
> 1 = primeira empresa). `/webhook/evolution` NAO existe no codigo.

## Passo 14: Acessar o sistema

1. Acesse `http://SEU_IP`
2. Faca cadastro (cria empresa automaticamente)
3. Em **Configuracoes**, confirme a Evolution (URL `http://evolution:8080`,
   chave da Evolution, instancia `flowai`) e a IA (Groq)
4. Crie/ative um workflow
5. Envie mensagem no WhatsApp conectado

## Passo 15: Atualizar a VPS (apos novas alteracoes no codigo)

> Apenas o setup acima e uma vez. Para trazer mudancas novas:

```bash
cd /opt/ai-saas
git fetch origin
git switch -C main origin/main   # evita detached HEAD
docker compose up -d --build
docker compose -f docker-compose.evolution.yml up -d
docker compose restart
```

### O que permanece intacto a cada atualizacao

| Camada | Sobrevive? | Motivo |
|--------|------------|--------|
| `.env` | Sim | gitignored; `git switch` nao toca no arquivo |
| Banco Postgres local (usuarios, workflows, configs) | Sim | volume `postgres_data` |
| Instancia/WhatsApp conectado na Evolution | Sim | volumes `evolution_instances`/`evolution_store` |
| Tabelas da Evolution (banco `evolution`) | Sim | mesmo volume do postgres |

### Regras de ouro

1. **NAO rode `./deploy-vps.sh`** se o `.env` ja existe: ele regenera
   `SECRET_KEY`/`SECRET_ENCRYPTION_KEY` se ausentes, o que **quebraria a
   descriptografia** das chaves ja salvas no banco. (Prefira os comandos
   manuais de update acima.)
2. **NAO delete o `.env`** nem os volumes da Evolution
   (`down -v` apaga a instancia/usuario).
3. `docker compose down` (sem `-v`) apaga os **containers** mas NAO o
   **volume** `postgres_data` — os dados sobrevivem.
4. Se o `git switch`/`pull` falhar por conflito local, resolva antes do build.

### Rollback

```bash
cd /opt/ai-saas
git log --oneline -5
git checkout <hash_do_ultimo_bom>
docker compose up -d --build
```

## Troubleshooting (o que quebrou no deploy real)

### Evolution reinicia em loop com erro de Prisma
- `DATABASE_CONNECTION_URI resolved to empty string` → falta `EVOLUTION_AUTH_KEY`
  no `.env` ou o compose usava `env_file` com variaveis erradas. Garanta a chave.
- `P3005 database schema is not empty` → apontou para o banco `ai_saas` (ja tem
  tabelas). Apontar para um banco **separado** `evolution` (veja passo 12).

### 401 Unauthorized ao criar instancia / API
A chave no header `apikey` nao bate com o `AUTHENTICATION_API_KEY` do container.
Confira com `docker exec evolution sh -c 'echo $AUTHENTICATION_API_KEY'` e use a
mesma. NAO use a chave da Groq.

### Backend nao acha `evolution`
Se `http://evolution:8080` der "Name or service not known", a Evolution nao esta
na mesma rede do backend (`ai-saas_ai-saas-network`). Verifique o compose.

### QR expira (KeyError 'qrcode')
Rode `connect` de novo. Expira em ~20-60s.

### Firewall / "nao conecta via IP"
Libere as portas 80/8080/22 no firewall do provedor (ex.: Hostinger) e no
firewall do SO se ativo.

---

## Referencia - comandos uteis

```bash
docker compose logs -f backend
docker compose logs -f celery-worker
docker compose exec redis redis-cli ping
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import text; print(engine.connect().execute(text('SELECT 1')).scalar())"
curl http://localhost:8000/
curl http://localhost:8080/
```
