"""Celery task definitions for discovery agents."""
from celery import shared_task
from backend.tasks.celery_app import celery_app
import logging

from backend.tasks.agent_tasks import run_job_scout, run_company_scout

logger = logging.getLogger(__name__)


@shared_task
def run_job_scout_task():
    """Run Job Scout Agent daily discovery."""
    logger.info("Job Scout: Starting daily job discovery")
    result = run_job_scout()
    return result


@shared_task
def run_company_scout_task():
    """Run Company Scout Agent daily company discovery."""
    logger.info("Company Scout: Starting daily company discovery")
    result = run_company_scout()
    return result
