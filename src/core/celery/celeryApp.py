from celery import Celery
from src.core.config import settings

celery_app = Celery(
    "notifications",
    broker = settings.REDIS_BROKER,
    backend = settings.REDIS_BACKEND,
    include = ["src.core.celery.tasks.notification_task"],
)

celery_app.conf.update(
    timezone="UTC",
    task_ignore_result=True,
    beat_schedule={
        "poll-notifications-every-minute": {
            "task": "poll_and_deliver_notification",
            "schedule": 60.0,  # seconds
        },
    },
)