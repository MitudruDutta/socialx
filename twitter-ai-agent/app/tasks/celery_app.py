from celery import Celery
from app.config import settings

celery_app = Celery(
    "twitter_bot",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    "check-mentions": {
        "task": "app.tasks.scheduled_tasks.check_mentions",
        "schedule": 120.0,  # Every 2 minutes
    },
    "health-check": {
        "task": "app.tasks.scheduled_tasks.health_check",
        "schedule": 300.0,  # Every 5 minutes
    },
    "cleanup-media": {
        "task": "app.tasks.scheduled_tasks.cleanup_media",
        "schedule": 86400.0,  # Daily
    },
}
