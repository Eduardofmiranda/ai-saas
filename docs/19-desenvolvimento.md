# 19 — Guia de Desenvolvimento

## Pre-requisitos

- Python 3.13+
- Node.js 24+
- PostgreSQL 16+ (ou SQLite para dev)
- Redis 7+ (para Celery)
- Docker + Docker Compose (opcional, para producao)

## Estrutura de Commits

```
feat: nova funcionalidade
fix: correcao de bug
refactor: refatoracao
test: adicionar/corrigir testes
docs: documentacao
chore: configuracao, dependencias
```

## Exemplo: Criar um Node

1. Criar funcao em `app/services/nodes/registry.py`
2. Registrar no `TYPE_MAP`
3. Adicionar schema do frontend em `NODE_TYPES` (Editor.jsx)
4. Adicionar cor e icone no `nodeColors` e `nodeIcons`
5. Criar campos de edicao no `NodeFields`
6. Criar teste em `tests/test_nodes_registry.py`

## Exemplo: Criar uma Rota

1. Criar schema em `app/schemas/`
2. Criar modelo (se necessario) em `app/models/`
3. Criar router em `app/routers/`
4. Incluir router em `app/main.py`
5. Adicionar rota no frontend em `src/api.js`

## Rodar Testes

```bash
# Todos os testes
pytest tests/ -xvs

# Teste especifico
pytest tests/test_crypto.py -xvs

# Com cobertura
pytest tests/ --cov=app --cov-report=html
```

## Rodar o Projeto

### Backend
```bash
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm run dev
```

### Celery Worker
```bash
celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
```

### Celery Beat
```bash
celery -A app.tasks.celery_app beat --loglevel=info
```

## Docker

```bash
# Subir tudo
docker compose up -d --build

# Ver logs
docker compose logs -f

# Entrar no container do backend
docker compose exec backend bash
```

## Banco de Dados

### Criacao das tabelas (automatica)
As tabelas sao criadas **automaticamente no boot** do backend (`lifespan` em
`app/main.py` chama `Base.metadata.create_all`). Nao e preciso rodar `create_all`
manualmente. Para conferir as tabelas:

```bash
python -c "from app.database.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"
```

> Este projeto **nao usa Alembic para o schema base** (ver docs/06). As migrations
> em `alembic/versions/` sao adicionais/idempotentes (ex.: `knowledge`). O fluxo de
> desenvolvimento NAO depende de `alembic upgrade head`.

## Arquivos Importantes

| Arquivo | Funcao |
|---------|--------|
| `app/config.py` | Leitura de variaveis de ambiente |
| `app/services/security.py` | JWT e bcrypt |
| `app/services/llm.py` | Adaptador de IA |
| `app/services/evolution.py` | Cliente WhatsApp |
| `app/services/workflow_engine.py` | Motor de workflows |
| `app/services/nodes/registry.py` | Registro de nodes |
| `app/services/nodes/context.py` | Contexto de execucao |
| `app/services/field_crypto.py` | Criptografia de campos |
| `frontend/src/api.js` | Cliente HTTP do frontend |
| `frontend/src/pages/Editor.jsx` | Editor visual |

## Trabalhando com o Motor

### Contexto de execucao

```python
ctx = NodeContext(
    db=session,
    company_id=1,
    execution_id=1,
    workflow_id=1,
    data={"message": {"text": "ola"}},
    config=config,
)
```

### Executar um node

```python
from app.services.nodes.registry import run_node

node = {"id": "n1", "type": "ai", "data": {"prompt": "Ola"}}
result = await run_node(ctx, node)
# result = {"outputs": {"ai_reply": "Ola! Como posso ajudar?"}}
```
