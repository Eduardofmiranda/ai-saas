from celery import Celery
from celery.schedules import crontab
from app.config import get_secret

celery_app = Celery(
    "ai_saas",
    broker=get_secret("REDIS_URL", "redis://localhost:6379/0"),
    backend=get_secret("REDIS_URL", "redis://localhost:6379/0"),
    include=[
        "app.tasks.workflow_tasks",
    ],
)

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
    beat_schedule={
        "cleanup-old-executions-daily": {
            "task": "app.tasks.workflow_tasks.cleanup_old_executions",
            "schedule": crontab(hour=3, minute=0),
        },
    },
)

celery_app.autodiscover_tasks()