# 21 - Checklist de deploy e verificacao na VPS

## Objetivo

Executar esta lista apos cada deploy que altere backend, configuracao, banco,
workflow ou integracao WhatsApp. Nao exibe nem registra secrets.

## 1. Atualizar com seguranca

No diretorio do projeto na VPS, confira primeiro o estado do checkout e preserve
o arquivo .env. Nao use docker compose down -v.

    cd /opt/ai-saas
    git status --short
    git log -1 --oneline

Aplique alteracoes de imagem e recrie os processos que recebem ambiente. Restart
nao recarrega variaveis de ambiente.

    docker compose up -d --build backend celery-worker celery-beat frontend
    docker compose up -d --no-deps --force-recreate backend celery-worker celery-beat
    docker compose -f docker-compose.evolution.yml up -d

## 2. Confirmar banco efetivo

O banco do aplicativo em producao e Supabase. O valor dentro do container e a
fonte de verdade; o .env em disco sozinho nao confirma a configuracao.

    docker compose exec backend python -c "import os; print('DATABASE_URL_SUPABASE=', 'supabase.co' in os.environ.get('DATABASE_URL', ''))"
    docker compose exec backend python -c "from app.database.database import engine; from sqlalchemy import text; print(dict(engine.connect().execute(text('select current_database(), inet_server_addr()')).mappings().first()))"

O resultado do backend nao pode apontar para postgres:5432 quando a producao deve
usar Supabase.

## 3. Confirmar servicos

    curl -fsS http://127.0.0.1:8000/health
    curl -fsS http://127.0.0.1:8000/health/db
    curl -fsS http://127.0.0.1:8000/health/redis
    curl -fsS http://127.0.0.1:8000/health/evolution
    docker compose ps
    docker compose logs --tail=100 backend celery-worker

## 4. Confirmar Evolution

A Evolution deve receber a mesma chave em EVOLUTION_AUTH_KEY e
EVOLUTION_API_KEY. Nunca cole a chave no historico do terminal ou em tickets.

    docker compose exec backend python -c "import os; print('EVOLUTION_KEYS_EQUAL=', bool(os.environ.get('EVOLUTION_AUTH_KEY')) and os.environ.get('EVOLUTION_AUTH_KEY') == os.environ.get('EVOLUTION_API_KEY'))"
    curl -sS -H "apikey: $KEY" http://127.0.0.1:8080/instance/fetchInstances

Para cada empresa, confirme a instancia inst-<company_id>, o estado open e o
webhook apontando para http://backend:8000/webhook/whatsapp/<company_id>.

## 5. Validacao funcional

1. No painel, confirme que existe um unico workflow de mensagens ativo para a empresa.
2. Envie uma mensagem ao numero conectado.
3. Confirme no log do backend um POST para o webhook e uma execucao do workflow.
4. Confirme a resposta no WhatsApp.
5. Se falhar, salve somente logs sem chaves e compare ambiente real, instancia,
   webhook e workflow ativo.

## 6. Confirmar migrations

Apos o deploy, confirme que todas as migrations foram aplicadas:

    docker compose exec backend alembic current

O resultado deve estar em `0018_audit_log` (head). Se estiver
atrasado, o backend aplicou automaticamente no startup; verifique os logs.

## Resultado esperado

O deploy so esta concluido quando banco, Redis, Evolution e os health checks
estao saudaveis e uma mensagem real conclui o fluxo ponta a ponta.
