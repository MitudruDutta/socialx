from celery import Celery
from celery.schedules import crontab
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
    task_time_limit=600,  # 10 minutes max
    task_soft_time_limit=540,  # Soft limit 9 minutes
    worker_prefetch_multiplier=1,
    task_acks_late=True,  # Acknowledge after completion
    task_reject_on_worker_lost=True,
)

celery_app.conf.beat_schedule = {
    "check-mentions": {
        "task": "app.tasks.scheduled_tasks.check_mentions",
        "schedule": 900.0,  # Every 15 minutes (as per spec)
    },
    "health-check": {
        "task": "app.tasks.scheduled_tasks.health_check",
        "schedule": 300.0,  # Every 5 minutes
    },
    "cleanup-media": {
        "task": "app.tasks.scheduled_tasks.cleanup_media",
        "schedule": crontab(hour=2, minute=0),  # Daily at 2 AM
    },
    "generate-content": {
        "task": "app.tasks.scheduled_tasks.generate_and_post_content",
        "schedule": crontab(hour="9,13,18", minute=0),  # 9 AM, 1 PM, 6 PM UTC
    },
}
