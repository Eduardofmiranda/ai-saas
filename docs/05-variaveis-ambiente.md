# 05 — Variaveis de Ambiente

## Obrigatórias

| Variavel | Finalidade | Exemplo |
|----------|-----------|---------|
| `DATABASE_URL` | URL de conexao com o banco | `postgresql://postgres:senha@localhost:5432/ai_saas` |
| `SECRET_KEY` | Chave secreta para JWT e derivacao de criptografia | `openssl rand -hex 32` |

## Opcionais (com defaults)

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `POSTGRES_PASSWORD` | `changeme` | Senha do PostgreSQL (usado no docker-compose) |
| `REDIS_URL` | `redis://localhost:6379/0` | URL do Redis (Celery broker) |
| `SECRET_ENCRYPTION_KEY` | Derivada de SECRET_KEY | Chave para criptografia de campos sensiveis |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` (24h) | Tempo de expiracao do token |

## IA (Defaults Globais)

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `DEFAULT_AI_PROVIDER` | `groq` | Provedor padrao de IA |
| `DEFAULT_AI_MODEL` | `llama-3.3-70b-versatile` | Modelo padrao |
| `DEFAULT_AI_API_KEY` | — | Chave de API do provedor padrao |
| `DEFAULT_AI_BASE_URL` | — | URL base do provedor (auto-resolvido) |

## WhatsApp / Evolution API

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `EVOLUTION_BASE_URL` | — | URL da Evolution API |
| `EVOLUTION_API_KEY` | — | Chave de API da Evolution |
| `EVOLUTION_INSTANCE` | `default` | Nome da instancia |

## Frontend

| Variavel | Default | Finalidade |
|----------|---------|-----------|
| `VITE_API_BASE` | `http://localhost:8000` | URL do backend para o frontend |

## Regras Importantes

1. **SECRET_KEY**: Nunca altere depois de salvar dados criptografados
2. **SECRET_ENCRYPTION_KEY**: Se vazio, deriva de SECRET_KEY. NUNCA altere depois de salvar dados criptografados
3. **Chaves de IA**: Sao criptografadas em repouso no banco de dados
4. **NUNCA** coloque secrets em arquivos versionados (git)
