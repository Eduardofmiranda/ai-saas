#!/usr/bin/env bash
# deploy-railway.sh - Deploy manual para Railway
# Uso: chmod +x deploy-railway.sh && ./deploy-railway.sh

set -euo pipefail

echo "🚀 Deploy Railway - AI SaaS"

# Verifica se Railway CLI está instalado
if ! command -v railway &> /dev/null; then
    echo "❌ Railway CLI não encontrado. Instalando..."
    npm install -g @railway/cli
fi

# Login (usa token do env ou browser)
if [[ -n "${RAILWAY_TOKEN:-}" ]]; then
    echo "🔐 Login com token..."
    railway login --token "$RAILWAY_TOKEN"
else
    echo "🔐 Login no browser..."
    railway login
fi

# Link do projeto (primeira vez)
if [[ -n "${RAILWAY_PROJECT_ID:-}" ]]; then
    echo "🔗 Linking project..."
    railway link "$RAILWAY_PROJECT_ID"
fi

# Deploy backend
echo "📦 Deploying backend..."
railway up --service backend --detach

# Deploy frontend
echo "📦 Deploying frontend..."
railway up --service frontend --detach

# Run migrations
echo "🔄 Running migrations..."
railway run --service backend alembic upgrade head

echo "✅ Deploy concluído!"
echo "🌐 Backend: https://backend.up.railway.app"
echo "🌐 Frontend: https://frontend.up.railway.app"