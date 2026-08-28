# 07 — Redis e Filas

## Tecnologia

- **Redis 7** (broker + backend do Celery)
- **Celery** (sistema de filas)
- **RedBeat** (agendador de tarefas periodic)

## Configuracao

```python
# celery_app.py
celery_app = Celery(
    "ai_saas",
    broker=get_secret("REDIS_URL", "redis://localhost:6379/0"),
    backend=get_secret("REDIS_URL", "redis://localhost:6379/0"),
)
```

## Filas

| Fila | Funcao |
|------|--------|
| `celery` (default) | Execucao assincrona de workflows |
| `beat` | Agendamento de tarefas periodicas |

## Workers

| Worker | Concorrencia | Funcao |
|--------|-------------|--------|
| `celery-worker` | 4 | Processa workflows assincronos |
| `celery-beat` | — | Agenda tarefas periodicas |

## Tarefas

### run_workflow_task
- **Parametros**: workflow_id, payload, company_id
- **Max retries**: 3
- **Retry delay**: 60s
- **Time limit**: 300s (hard), 240s (soft)
- **Funcao**: Executa um workflow de forma assincrona

### cleanup_old_executions
- **Agendamento**: Diariamente as 03:00 (cron)
- **Funcao**: Remove execucoes com mais de 30 dias

## Configuracoes Celery

```python
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    task_soft_time_limit=240,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)
```

## Uso do Redis

| Finalidade | Estrutura |
|-----------|-----------|
| Broker do Celery | Strings (mensagens) |
| Backend do Celery | Strings (resultados) |
| Agendador RedBeat | Sorted sets |
| Cache | Nao utilizado diretamente |
