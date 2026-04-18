from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "global_intelligence",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.tasks.osint_tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    beat_schedule={
        "scan-all-countries-daily": {
            "task": "app.tasks.osint_tasks.scan_all_countries",
            "schedule": 86400.0,  # every 24 hours
        },
        "generate-daily-reports": {
            "task": "app.tasks.osint_tasks.generate_daily_reports",
            "schedule": 86400.0,
        },
    },
)
