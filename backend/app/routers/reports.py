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


@router.get("/weekly")
async def get_weekly_reports(db: AsyncSession = Depends(get_db)):
    """Get all weekly reports."""
    result = await db.execute(
        select(Report).where(Report.type == "weekly").order_by(Report.generated_at.desc())
    )
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


@router.get("/{report_id}")
async def get_report_by_id(report_id: str, db: AsyncSession = Depends(get_db)):
    """Get report by ID."""
    from uuid import UUID
    from fastapi import HTTPException, status
    try:
        uid = UUID(str(report_id))
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid report ID")

    report = await db.get(Report, uid)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return {
        "id": str(report.id),
        "type": report.type,
        "title": report.title,
        "summary": report.summary,
        "content": report.content,
        "markdown": report.markdown,
        "metrics": report.metrics,
        "period_start": report.period_start,
        "period_end": report.period_end,
        "generated_at": report.generated_at.isoformat() if report.generated_at else None,
    }


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
