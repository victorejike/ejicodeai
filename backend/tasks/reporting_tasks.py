"""Celery task definitions for reporting."""
from celery import shared_task
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task
def generate_daily_report():
    """Generate daily intelligence report."""
    logger.info("Generating daily report")
    return {
        "status": "completed",
        "report_id": f"daily-{datetime.utcnow().strftime('%Y%m%d')}",
        "generated_at": datetime.utcnow().isoformat(),
    }


@shared_task
def generate_weekly_report():
    """Generate weekly intelligence report."""
    logger.info("Generating weekly report")
    return {
        "status": "completed",
        "report_id": f"weekly-{datetime.utcnow().strftime('%G%V')}",
        "generated_at": datetime.utcnow().isoformat(),
    }
