"""Reports router - reporting and analytics."""
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models import Report

router = APIRouter()


@router.get("")
async def list_reports(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    report_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List reports."""
    query = select(Report).order_by(Report.generated_at.desc())
    if report_type:
        query = query.where(Report.type == report_type)
    result = await db.execute(query.offset(skip).limit(limit))
    reports = result.scalars().all()
    return [
        {
            "id": str(r.id),
            "type": r.type,
            "title": r.title,
            "summary": r.summary,
            "period_start": r.period_start,
            "period_end": r.period_end,
            "generated_at": r.generated_at.isoformat() if r.generated_at else None,
        }
        for r in reports
    ]


@router.post("/generate")
async def generate_report(report_type: str = "daily"):
    """Queue report generation via Celery."""
    try:
        from backend.tasks.agent_tasks import generate_daily_report, generate_weekly_report
        if report_type == "weekly":
            task = generate_weekly_report.delay()
        else:
            task = generate_daily_report.delay()
        return {"status": "queued", "report_type": report_type, "task_id": task.id}
    except Exception as e:
        return {"status": "queued", "report_type": report_type, "error": str(e)}
