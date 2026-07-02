"""Celery configuration and task queue setup."""
from celery import Celery
from celery.schedules import crontab
from backend.app.config import get_settings

settings = get_settings()

# Initialize Celery
celery_app = Celery(
    "ejicode_bdp",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=1000,
    result_expires=3600,  # 1 hour
)

# Define periodic tasks
celery_app.conf.beat_schedule = {
    "job-discovery-daily": {
        "task": "backend.tasks.agent_tasks.run_job_scout",
        "schedule": crontab(hour=6, minute=0),
        "options": {"queue": "agents"},
    },
    "company-discovery-daily": {
        "task": "backend.tasks.agent_tasks.run_company_scout",
        "schedule": crontab(hour=12, minute=0),
        "options": {"queue": "agents"},
    },
    "daily-reporting": {
        "task": "backend.tasks.agent_tasks.generate_daily_report",
        "schedule": crontab(hour=18, minute=0),
        "options": {"queue": "reporting"},
    },
    "weekly-reporting": {
        "task": "backend.tasks.agent_tasks.generate_weekly_report",
        "schedule": crontab(day_of_week=0, hour=8, minute=0),
        "options": {"queue": "reporting"},
    },
    "reply-monitoring-hourly": {
        "task": "backend.tasks.agent_tasks.monitor_replies_task",
        "schedule": crontab(minute=0),
        "options": {"queue": "agents"},
    },
}
