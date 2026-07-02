"""Dashboard router for frontend summary and metrics."""
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models import Company, Opportunity, Proposal, OutreachHistory, Report, AgentRun

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Return a dashboard summary for Phase 4 frontend."""
    counts = {}
    counts["companies"] = await db.scalar(select(func.count()).select_from(Company))
    counts["opportunities"] = await db.scalar(select(func.count()).select_from(Opportunity))
    counts["proposals"] = await db.scalar(select(func.count()).select_from(Proposal))
    counts["outreach_history"] = await db.scalar(select(func.count()).select_from(OutreachHistory))
    counts["reports"] = await db.scalar(select(func.count()).select_from(Report))
    counts["active_agents"] = await db.scalar(
        select(func.count(func.distinct(AgentRun.agent_name))).where(AgentRun.status == "running")
    )

    latest_opportunities = (
        await db.execute(
            select(Opportunity.id, Opportunity.title, Opportunity.company_id, Opportunity.status)
            .order_by(Opportunity.created_at.desc())
            .limit(3)
        )
    ).all()

    recent_agent_runs = (
        await db.execute(
            select(AgentRun.agent_name, AgentRun.status, AgentRun.started_at)
            .order_by(AgentRun.started_at.desc())
            .limit(5)
        )
    ).all()

    return {
        "status": "operational",
        "counts": {
            "companies": counts["companies"] or 0,
            "opportunities": counts["opportunities"] or 0,
            "proposals": counts["proposals"] or 0,
            "outreach_history": counts["outreach_history"] or 0,
            "reports": counts["reports"] or 0,
            "active_agents": counts["active_agents"] or 0,
        },
        "latest_opportunities": [
            {
                "id": str(row.id),
                "title": row.title,
                "company_id": str(row.company_id) if row.company_id else None,
                "status": row.status,
            }
            for row in latest_opportunities
        ],
        "recent_agent_runs": [
            {
                "agent_name": row.agent_name,
                "status": row.status,
                "started_at": row.started_at.isoformat() if row.started_at else None,
            }
            for row in recent_agent_runs
        ],
    }
