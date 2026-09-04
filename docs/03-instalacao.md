# 03 — Instalacao

## Requisitos

- Python 3.13+
- Node.js 24+
- PostgreSQL 16+ (ou SQLite para dev)
- Redis 7+ (para Celery)
- Docker + Docker Compose (para producao)

## Instalacao Local (Desenvolvimento)

### Backend

```bash
# 1. Clonar o repositorio
git clone <repo-url>
cd ai-saas

# 2. Criar virtualenv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar variaveis de ambiente
cp .env.example .env
# Editar .env com suas configuracoes

# 5. Aplicar migrations (necessario ao reutilizar um banco local existente)
alembic upgrade head

# 6. Iniciar o backend
# SQLite local recebe o schema inicial automaticamente; migrations continuam
# sendo a fonte de verdade para evolucoes estruturais.
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
# 1. Entrar na pasta frontend
cd frontend

# 2. Instalar dependencias
npm install

# 3. Iniciar o servidor de desenvolvimento
npm run dev
```

O frontend estara disponivel em `http://localhost:5173`.

## Instalacao com Docker (Producao)

```bash
# 1. Configurar variaveis de ambiente
cp .env.example .env
# Editar .env com configuracoes de producao

# 2. Subir todos os servicos
# O backend executa `alembic upgrade head` antes de iniciar a API.
docker compose up -d --build
```

Servicos disponiveis:
- Frontend: `http://localhost:80`
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`

## Instalacao com Docker (Desenvolvimento)

```bash
# Usar docker-compose.dev.yml (modo dev, explicitamente)
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

## Comandos Uteis

```bash
# Ver logs do backend
docker compose logs -f backend

# Entrar no container do backend
docker compose exec backend bash

# Ver a revisao de schema aplicada:
docker compose exec backend alembic current
# Ver tabelas (confirmacao):
docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import inspect; print(inspect(engine).get_table_names())"

# Rodar testes
docker compose exec backend pytest tests/ -xvs
```
