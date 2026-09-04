# 05 — Variaveis de Ambiente

## Obrigatórias

| Variavel | Finalidade | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | URL de conexao com o banco | Producao: `postgresql://postgres:senha@postgres:5432/ai_saas` (host `postgres` = servico do docker-compose). Dev local: `sqlite:///./aissaas.db` |
| `SECRET_KEY` | Chave secreta para JWT e derivacao de criptografia | `openssl rand -hex 32` |

> **Importante:** `SECRET_KEY` e **obrigatoria** no startup. Sem ela, o servidor
> nao inicia (exibe erro e encerra). Nao existe mais valor fallback.

## Opcionais (com defaults)

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `POSTGRES_PASSWORD` | `changeme` | Senha do PostgreSQL local (usado no docker-compose) |
| `REDIS_URL` | `redis://redis:6379/0` | URL do Redis (Celery broker) — MANTENHA o Redis interno do docker |
| `SECRET_ENCRYPTION_KEY` | Derivada de SECRET_KEY | Chave para criptografia de campos sensiveis |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | Tempo de expiracao do token |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Origens CORS permitidas (lista separada por virgula). Em producao, defina o dominio real |

## CORS

- Controlado por `ALLOWED_ORIGINS` (lista separada por virgula).
- Nao e mais hardcoded no codigo.
- Exemplo producao: `ALLOWED_ORIGINS=https://app.minhaempresa.com`

## Seed de Usuario de Teste (desenvolvimento local)

> **Atencao:** O seed roda **apenas** quando `SEED_DEFAULT_USER` esta habilitado
> E o banco nao possui nenhum usuario. Em producao, NAO defina `SEED_DEFAULT_USER`.

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `SEED_DEFAULT_USER` | — | Habilita o seed (`true`/`1`/`yes`) |
| `SEED_USER_EMAIL` | `teste@flowai.com` | Email do usuario de teste |
| `SEED_USER_PASSWORD` | `teste123` | Senha do usuario de teste |
| `SEED_USER_NAME` | `Usuario Teste` | Nome do usuario de teste |
| `SEED_COMPANY_NAME` | `Empresa Teste` | Nome da empresa de teste |

## IA (Defaults Globais)

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `DEFAULT_AI_PROVIDER` | `groq` | Provedor padrao de IA |
| `DEFAULT_AI_MODEL` | `qwen/qwen3.8-27b` | Modelo padrao |
| `DEFAULT_AI_API_KEY` | — | Chave de API do provedor padrao (Groq). **NAO reutilizar como Evolution API key** |
| `DEFAULT_AI_BASE_URL` | — | URL base do provedor (auto-resolvido) |

## WhatsApp / Evolution API

> A versao fixada da Evolution (`evoapicloud/evolution-api:v2.3.7`) usa a chave
> que VOCE define como `AUTHENTICATION_API_KEY` (nao requer ativacao de licenca,
> que so existe na v2.4.0+). O compose injeta essa chave a partir de
> `EVOLUTION_AUTH_KEY`.

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `EVOLUTION_BASE_URL` | `http://evolution:8080` | URL da Evolution API (dentro do docker, hostname `evolution`) |
| `EVOLUTION_API_KEY` | — | Chave que o **backend** usa para autenticar na Evolution (`send_text`) |
| `EVOLUTION_AUTH_KEY` | — | Chave para autenticar o **webhook** (`evolution-auth` header) e usada pelo compose como `AUTHENTICATION_API_KEY`. **Use a MESMA de `EVOLUTION_API_KEY`** |
| `EVOLUTION_INSTANCE` | `default` | Nome da instancia (ex.: `flowai`) |

> **Nota (variaveis mortas):** `EVOLUTION_SERVER_URL` e `EVOLUTION_DATABASE_URI`
> **NAO sao lidas por nenhum codigo** (backend Python ou compose). O
> `docker-compose.evolution.yml` define `SERVER_URL` e `DATABASE_CONNECTION_URI`
> **hardcoded no proprio arquivo** (via `POSTGRES_PASSWORD`). Voce pode remove-las
> do `.env` sem efeito. Elas permaneciam no template por engano.

## Frontend

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `VITE_API_BASE` | `http://localhost:8000` | URL do backend para o frontend |

## Regras Importantes

1. **SECRET_KEY**: Nunca altere depois de salvar dados criptografados
2. **SECRET_ENCRYPTION_KEY**: NUNCA altere depois de salvar dados criptografados. **Nao use o mesmo valor de `SECRET_KEY`** (gerar valores distintos)
3. **Chaves de IA**: Sao criptografadas em repouso no banco de dados
4. **NUNCA** coloque secrets em arquivos versionados (git)
5. **NAO use a chave da Groq como `EVOLUTION_API_KEY`** — sao chaves diferentes
6. O `docker-compose.evolution.yml` **nao usa `env_file`** — vazar variaveis do app para a Evolution causa conflitos no `AUTHENTICATION_API_KEY`
7. **`SEED_DEFAULT_USER`**: habilitar apenas em desenvolvimento local. Em producao, NAO definir.
