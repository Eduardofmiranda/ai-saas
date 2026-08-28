#!/usr/bin/env bash
# deploy-vps.sh - Setup + Deploy para VPS (Linux)
# Uso sem permissoes: ./deploy-vps.sh
# Uso como root: sudo ./deploy-vps.sh
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
log() { echo -e "${GREEN}[deploy]${NC} $1"; }
warn() { echo -e "${YELLOW}[aviso]${NC} $1"; }
die() { echo -e "${RED}[erro]${NC} $1"; exit 1; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------
# 1. Verificacoes de ambiente
# ---------------------------------------------------------------
log "Verificando ambiente..."
command -v docker >/dev/null 2>&1 || die "Docker nao instalado. Rode: curl -fsSL https://get.docker.com | sh"
command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1 || \
  warn "Docker Compose v2 nao detectado (necessario para docker compose)."

# Criar usuario deploy se rodando como root
if [[ "$(id -u)" == "0" ]]; then
  if ! id deploy >/dev/null 2>&1; then
    log "Criando usuario 'deploy'..."
    useradd -m -s /bin/bash deploy
    usermod -aG docker deploy
    log "Usuario 'deploy' criado. Reexecute este script como deploy:"
    log "  su - deploy && cd $SCRIPT_DIR && ./deploy-vps.sh"
    exit 0
  fi
fi

# ---------------------------------------------------------------
# 2. Configuracao (.env)
# ---------------------------------------------------------------
if [[ ! -f ".env" ]]; then
  if [[ -f ".env.example" ]]; then
    cp .env.example .env
    warn "Arquivo .env criado a partir do .env.example."
    warn "EDITE AGORA: nano .env  (coloque valores REAIS)"
    warn "Preencha: DATABASE_URL, SECRET_KEY, DEFAULT_AI_API_KEY, Evolution keys"
    exit 0
  else
    die ".env nao encontrado. Crie manualmente."
  fi
fi

# ---------------------------------------------------------------
# 3. Validar variaveis criticas + segredos
# ---------------------------------------------------------------
source .env

# SECRET_KEY forte
if [[ -z "${SECRET_KEY:-}" || "$SECRET_KEY" == *"changeme"* ]]; then
  NEW=$(openssl rand -hex 32)
  sed -i "s|^SECRET_KEY=.*|SECRET_KEY=$NEW|" .env
  warn "SECRET_KEY gerada e gravada no .env"
fi

# SECRET_ENCRYPTION_KEY (criptografia dos campos sensiveis)
if [[ -z "${SECRET_ENCRYPTION_KEY:-}" || "$SECRET_ENCRYPTION_KEY" == *"changeme"* ]]; then
  NEW=$(openssl rand -hex 32)
  sed -i "s|^SECRET_ENCRYPTION_KEY=.*|SECRET_ENCRYPTION_KEY=$NEW|" .env || \
    echo "SECRET_ENCRYPTION_KEY=$NEW" >> .env
  warn "SECRET_ENCRYPTION_KEY gerada e gravada no .env"
fi
source .env

# ---------------------------------------------------------------
# 4. Build + subir
# ---------------------------------------------------------------
log "Subindo stack com Docker Compose..."
docker compose pull || true
docker compose up -d --build
log "Stack iniciada."

# ---------------------------------------------------------------
# 5. Migracoes
# ---------------------------------------------------------------
log "Rodando migracoes (alembic)..."
docker compose exec -T backend alembic upgrade head || warn "Migracao falhou - rode manualmente: docker compose exec backend alembic upgrade head"

# ---------------------------------------------------------------
# 6. Verificacao
# ---------------------------------------------------------------
log "Verificando saude dos servicos..."
sleep 3
docker compose ps || true

log "Deploy concluido!"
log "Backend:  $(docker compose port backend 8000 2>/dev/null || echo 'verifique docker compose ps')"
log "Frontend: $(docker compose port frontend 80 2>/dev/null || echo 'verifique docker compose ps')"
log ""
log "Logs: docker compose logs -f backend"
log "Docs:  http://<IP>:8000/docs"