"""Dashboard router for summary, real-time KPI metrics, and analytics charts."""
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from fastapi import APIRouter, Depends
from sqlalchemy import case, desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import (
    AgentRun,
    Campaign,
    Company,
    Contact,
    Opportunity,
    OutreachHistory,
    Proposal,
    Report,
)

router = APIRouter()


@router.get("/summary")
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Return dashboard summary KPIs and latest items."""
    counts = {}
    counts["companies"] = (await db.scalar(select(func.count()).select_from(Company))) or 0
    counts["opportunities"] = (await db.scalar(select(func.count()).select_from(Opportunity))) or 0
    counts["contacts"] = (await db.scalar(select(func.count()).select_from(Contact))) or 0
    counts["proposals"] = (await db.scalar(select(func.count()).select_from(Proposal))) or 0
    counts["outreach_history"] = (await db.scalar(select(func.count()).select_from(OutreachHistory))) or 0
    counts["reports"] = (await db.scalar(select(func.count()).select_from(Report))) or 0
    counts["active_agents"] = (
        await db.scalar(
            select(func.count(func.distinct(AgentRun.agent_name))).where(AgentRun.status == "running")
        )
    ) or 0

    latest_opportunities = (
        await db.execute(
            select(Opportunity.id, Opportunity.title, Opportunity.company_id, Opportunity.status, Opportunity.score)
            .order_by(Opportunity.created_at.desc())
            .limit(5)
        )
    ).all()

    recent_agent_runs = (
        await db.execute(
            select(AgentRun.agent_name, AgentRun.status, AgentRun.started_at, AgentRun.duration_ms)
            .order_by(AgentRun.started_at.desc())
            .limit(5)
        )
    ).all()

    return {
        "status": "operational",
        "counts": counts,
        "latest_opportunities": [
            {
                "id": str(row.id),
                "title": row.title,
                "company_id": str(row.company_id) if row.company_id else None,
                "status": row.status,
                "score": row.score,
            }
            for row in latest_opportunities
        ],
        "recent_agent_runs": [
            {
                "agent_name": row.agent_name,
                "status": row.status,
                "started_at": row.started_at.isoformat() if row.started_at else None,
                "duration_ms": row.duration_ms,
            }
            for row in recent_agent_runs
        ],
    }


@router.get("/analytics")
async def get_dashboard_analytics(db: AsyncSession = Depends(get_db)):
    """Return structured dataset for all 6 required Recharts dashboard graphs."""
    # 1. Opportunity Discovery Graph (distribution by score buckets)
    score_buckets = [
        {"range": "90-100", "count": 0, "label": "Hot Fit"},
        {"range": "80-89", "count": 0, "label": "Strong Fit"},
        {"range": "70-79", "count": 0, "label": "Moderate"},
        {"range": "50-69", "count": 0, "label": "Evaluating"},
        {"range": "<50", "count": 0, "label": "Low"},
    ]
    opps = (await db.execute(select(Opportunity.score, Opportunity.status))).all()
    for opp in opps:
        s = opp.score or 0
        if s >= 90:
            score_buckets[0]["count"] += 1
        elif s >= 80:
            score_buckets[1]["count"] += 1
        elif s >= 70:
            score_buckets[2]["count"] += 1
        elif s >= 50:
            score_buckets[3]["count"] += 1
        else:
            score_buckets[4]["count"] += 1

    # 2. Company Growth Graph (by status / industry)
    companies = (await db.execute(select(Company.status, Company.industry, Company.fit_score))).all()
    status_counts: Dict[str, int] = {}
    for c in companies:
        st = c.status or "discovered"
        status_counts[st] = status_counts.get(st, 0) + 1

    company_growth = [
        {"stage": "Discovered", "companies": status_counts.get("discovered", 0)},
        {"stage": "Researched", "companies": status_counts.get("researched", 0)},
        {"stage": "Contacted", "companies": status_counts.get("contacted", 0)},
        {"stage": "Meeting", "companies": status_counts.get("meeting", 0)},
        {"stage": "Client", "companies": status_counts.get("client", 0)},
    ]

    # 3. Agent Performance Graph (runs, average duration, success rate)
    agent_runs = (
        await db.execute(
            select(AgentRun.agent_name, AgentRun.status, AgentRun.duration_ms)
            .order_by(AgentRun.started_at.desc())
            .limit(100)
        )
    ).all()
    perf_by_agent: Dict[str, Dict[str, Any]] = {}
    for run in agent_runs:
        name = run.agent_name
        if name not in perf_by_agent:
            perf_by_agent[name] = {"agent": name, "success": 0, "failure": 0, "total_ms": 0, "count": 0}
        perf_by_agent[name]["count"] += 1
        perf_by_agent[name]["total_ms"] += run.duration_ms or 1500
        if run.status in ["completed", "success"]:
            perf_by_agent[name]["success"] += 1
        elif run.status in ["failed", "failure"]:
            perf_by_agent[name]["failure"] += 1

    agent_performance = []
    for k, v in perf_by_agent.items():
        avg_sec = round((v["total_ms"] / max(v["count"], 1)) / 1000.0, 1)
        rate = round((v["success"] / max(v["count"], 1)) * 100, 1)
        agent_performance.append({
            "agent": k.replace("_", " ").title(),
            "runs": v["count"],
            "success_rate": rate,
            "avg_seconds": avg_sec,
        })

    # No fabricated fallback series: if no agents have run yet, the chart
    # honestly renders empty until real agent runs are recorded.

    # 4. Outreach Success Graph
    outreach_records = (await db.execute(select(OutreachHistory))).scalars().all()
    outreach_stats = {"sent": 0, "opened": 0, "replied": 0, "bounced": 0}
    for r in outreach_records:
        if r.delivery_status == "sent":
            outreach_stats["sent"] += 1
        elif r.delivery_status == "bounced":
            outreach_stats["bounced"] += 1
        if (r.open_count or 0) > 0 or r.opened_at:
            outreach_stats["opened"] += 1
        if r.replied_at:
            outreach_stats["replied"] += 1

    outreach_success = [
        {"metric": "Sent", "value": outreach_stats["sent"], "fill": "#3b82f6"},
        {"metric": "Opened", "value": outreach_stats["opened"], "fill": "#8b5cf6"},
        {"metric": "Replied", "value": outreach_stats["replied"], "fill": "#10b981"},
        {"metric": "Bounced", "value": outreach_stats["bounced"], "fill": "#ef4444"},
    ]

    # 5. Revenue Pipeline Graph: real compensation figures attached to opportunities,
    # aggregated by their company's real pipeline stage. No invented dollar amounts -
    # stages with no priced opportunities yet honestly show $0.
    opp_value_rows = (
        await db.execute(
            select(Company.status, Opportunity.salary_max, Opportunity.salary_min)
            .join(Opportunity, Opportunity.company_id == Company.id)
        )
    ).all()
    value_by_stage: Dict[str, float] = {}
    deals_by_stage: Dict[str, int] = {}
    for row in opp_value_rows:
        st = row.status or "discovered"
        estimate = row.salary_max or row.salary_min or 0.0
        value_by_stage[st] = value_by_stage.get(st, 0.0) + estimate
        deals_by_stage[st] = deals_by_stage.get(st, 0) + 1

    pipeline_stages = [
        {"stage": "New Leads", "value": value_by_stage.get("discovered", 0), "deals": deals_by_stage.get("discovered", 0)},
        {"stage": "Researched", "value": value_by_stage.get("researched", 0), "deals": deals_by_stage.get("researched", 0)},
        {"stage": "Contacted", "value": value_by_stage.get("contacted", 0), "deals": deals_by_stage.get("contacted", 0)},
        {"stage": "In Discussion", "value": value_by_stage.get("meeting", 0), "deals": deals_by_stage.get("meeting", 0)},
        {"stage": "Closed Won", "value": value_by_stage.get("client", 0), "deals": deals_by_stage.get("client", 0)},
    ]

    # 6. Contact Acquisition Graph
    contacts = (await db.execute(select(Contact.is_decision_maker, Contact.email_confidence))).all()
    dm_count = sum(1 for c in contacts if c.is_decision_maker)
    non_dm_count = len(contacts) - dm_count
    verified_count = sum(1 for c in contacts if c.email_confidence in ["high", "verified"])

    contact_acquisition = [
        {"category": "Decision Makers", "count": dm_count},
        {"category": "Influencers / Eng", "count": non_dm_count},
        {"category": "Verified Emails", "count": verified_count},
    ]

    # 7. Activity Timeline: built only from real, persisted events - recent agent runs,
    # proposals awaiting approval, and inbound outreach replies. No invented companies,
    # people, or outcomes. Empty when nothing has happened yet.
    timeline: List[Dict[str, Any]] = []

    recent_runs = (
        await db.execute(
            select(AgentRun.id, AgentRun.agent_name, AgentRun.status, AgentRun.started_at, AgentRun.duration_ms)
            .order_by(desc(AgentRun.started_at))
            .limit(5)
        )
    ).all()
    for run in recent_runs:
        timeline.append({
            "id": f"run-{run.id}",
            "type": "agent",
            "title": f"{run.agent_name.replace('_', ' ').title()} {run.status}",
            "timestamp": run.started_at.isoformat() if run.started_at else None,
            "badge": "success" if run.status in ("completed", "success") else run.status,
            "detail": f"Finished in {run.duration_ms}ms" if run.duration_ms else "Run in progress",
        })

    recent_proposals = (
        await db.execute(
            select(Proposal.id, Proposal.subject, Proposal.created_at)
            .where(Proposal.status == "draft")
            .order_by(desc(Proposal.created_at))
            .limit(3)
        )
    ).all()
    for prop in recent_proposals:
        timeline.append({
            "id": f"proposal-{prop.id}",
            "type": "proposal",
            "title": "AI Proposal Awaiting Approval",
            "timestamp": prop.created_at.isoformat() if prop.created_at else None,
            "badge": "pending",
            "detail": prop.subject or "Draft proposal ready for review",
        })

    recent_replies = (
        await db.execute(
            select(OutreachHistory.id, OutreachHistory.replied_at, OutreachHistory.reply_classification, Contact.full_name)
            .join(Contact, Contact.id == OutreachHistory.contact_id, isouter=True)
            .where(OutreachHistory.replied_at.isnot(None))
            .order_by(desc(OutreachHistory.replied_at))
            .limit(3)
        )
    ).all()
    for reply in recent_replies:
        timeline.append({
            "id": f"reply-{reply.id}",
            "type": "outreach",
            "title": "Reply Received",
            "timestamp": reply.replied_at.isoformat() if reply.replied_at else None,
            "badge": reply.reply_classification or "replied",
            "detail": f"{reply.full_name} replied" if reply.full_name else "A contact replied",
        })

    timeline.sort(key=lambda e: e["timestamp"] or "", reverse=True)
    timeline = timeline[:6]

    return {
        "opportunity_discovery": score_buckets,
        "company_growth": company_growth,
        "agent_performance": agent_performance,
        "outreach_success": outreach_success,
        "revenue_pipeline": pipeline_stages,
        "contact_acquisition": contact_acquisition,
        "activity_timeline": timeline,
    }
