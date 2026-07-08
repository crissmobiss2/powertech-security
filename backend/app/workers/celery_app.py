"""Celery application factory."""
from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "powertech_security",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks", "app.workers.vision_worker"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Manila",
    enable_utc=True,
    task_routes={
        "app.workers.tasks.dispatch_alert": {"queue": "alerts"},
        "app.workers.tasks.process_security_event": {"queue": "events"},
        "app.workers.tasks.execute_playbook_async": {"queue": "playbooks"},
        "app.workers.tasks.process_camera_feed": {"queue": "vision"},
        "app.workers.tasks.start_all_camera_feeds": {"queue": "vision"},
    },
    beat_schedule={
        "check_asset_health": {
            "task": "app.workers.tasks.sweep_asset_health",
            "schedule": 300.0,
        },
        "check_sla_breaches": {
            "task": "app.workers.tasks.check_sla_breaches",
            "schedule": 900.0,
        },
        "start_camera_feeds": {
            "task": "app.workers.tasks.start_all_camera_feeds",
            "schedule": 300.0,
        },
    },
)
