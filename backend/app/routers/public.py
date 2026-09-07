"""Public API router providing statistics, platform metrics, and workflow details."""
from typing import Any, Dict
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import (
    Candidate,
    Company,
    Contact,
    CVExtraction,
    Opportunity,
    OutreachHistory,
    Proposal,
    RejectionLog,
    WorkflowExecution,
)

router = APIRouter()


@router.get("/statistics")
async def get_public_statistics(db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    """Return aggregated platform statistics and capabilities for the public website."""
    # Live database queries
    companies_count = (await db.scalar(select(func.count()).select_from(Company))) or 0
    opportunities_count = (await db.scalar(select(func.count()).select_from(Opportunity))) or 0
    contacts_count = (await db.scalar(select(func.count()).select_from(Contact))) or 0
    proposals_count = (await db.scalar(select(func.count()).select_from(Proposal))) or 0
    outreach_count = (await db.scalar(select(func.count()).select_from(OutreachHistory))) or 0
    candidates_count = (await db.scalar(select(func.count()).select_from(Candidate))) or 0
    rejections_count = (await db.scalar(select(func.count()).select_from(RejectionLog))) or 0
    workflows_count = (await db.scalar(select(func.count()).select_from(WorkflowExecution))) or 0

    # Recovery rate is computed from real rejection-log outcomes only.
    # Returns None (no fabricated number) until at least one rejection has been logged.
    recovered_rejections = (
        await db.scalar(
            select(func.count())
            .select_from(RejectionLog)
            .where(RejectionLog.similar_search_triggered.is_(True))
        )
    ) or 0
    rejection_recovery_rate = (
        round((recovered_rejections / rejections_count) * 100, 1) if rejections_count > 0 else None
    )

    # Extraction accuracy is the real average confidence score across processed CVs.
    # Returns None (no fabricated number) until at least one CV has been processed.
    avg_confidence = await db.scalar(select(func.avg(CVExtraction.confidence_score)))
    data_extraction_accuracy = round(float(avg_confidence) * 100, 1) if avg_confidence is not None else None

    # 14-stage workflow architecture definition
    workflow_stages = [
        {"id": 1, "name": "Profile & Search Strategy", "agent": "ProfileAnalyzerAgent", "icon": "Brain", "desc": "Analyzes candidate or enterprise criteria and forms multi-angle search queries."},
        {"id": 2, "name": "Multi-Source Discovery", "agent": "ScraperRegistry", "icon": "Compass", "desc": "Scrapes across 10 specialized sources (Google, LinkedIn, Indeed, GitHub, Reddit, Upwork, etc.)."},
        {"id": 3, "name": "Target Validation", "agent": "ValidationAgent", "icon": "ShieldCheck", "desc": "Calculates email, company, and opportunity confidence scores (0.0 to 1.0)."},
        {"id": 4, "name": "Structured Extraction", "agent": "DataExtractionAgent", "icon": "FileSpreadsheet", "desc": "Normalizes compensation, tech stack, and location with strict zero-hallucination rules."},
        {"id": 5, "name": "Cross-Source Deduplication", "agent": "DeduplicationAgent", "icon": "CopyCheck", "desc": "Identifies duplicate postings across platforms, combining source URLs and insights."},
        {"id": 6, "name": "Deep Company Research", "agent": "CompanyResearchAgent", "icon": "Search", "desc": "Researches business model, pain points, funding stage, and recent engineering investments."},
        {"id": 7, "name": "Decision Maker Discovery", "agent": "ContactFinderAgent", "icon": "Users", "desc": "Identifies relevant engineering leaders, hiring managers, and decision makers."},
        {"id": 8, "name": "6-Factor Weighted Matching", "agent": "MatchingAgent", "icon": "Target", "desc": "Computes alignment across Skills (35%), Exp (20%), Location (10%), Comp (10%), Tech (10%), Goals (15%)."},
        {"id": 9, "name": "Tailored Proposal Generation", "agent": "ProposalAgent", "icon": "PenTool", "desc": "Drafts hyper-personalized value proposition aligned directly to company pain points."},
        {"id": 10, "name": "Human-in-the-Loop Review", "agent": "ReviewGate", "icon": "CheckSquare", "desc": "Allows one-click review and approval before any external communication is dispatched."},
        {"id": 11, "name": "Automated Dispatch", "agent": "OutreachAgent", "icon": "Send", "desc": "Dispatches approved messages through verified channels with deliverability safeguards."},
        {"id": 12, "name": "Multi-Step Follow-Up", "agent": "FollowUpAgent", "icon": "CalendarClock", "desc": "Schedules intelligent Day 3, Day 7, and Day 14 follow-up cadences with auto-stop on reply."},
        {"id": 13, "name": "Rejection Recovery Engine", "agent": "RejectionRecoveryAgent", "icon": "RefreshCw", "desc": "Transforms rejections into lookalike companies, alternate contacts, and refined strategies."},
        {"id": 14, "name": "Continuous Analytics & Learning", "agent": "AnalyticsEngine", "icon": "TrendingUp", "desc": "Continuously tunes search keywords, response predictors, and conversion metrics."}
    ]

    active_sources = [
        {"id": "google_search", "name": "Google Search", "type": "Search Engine", "status": "active"},
        {"id": "google_maps", "name": "Google Maps", "type": "Local Business", "status": "active"},
        {"id": "linkedin", "name": "LinkedIn Jobs & People", "type": "Professional Network", "status": "active"},
        {"id": "indeed", "name": "Indeed", "type": "Job Board", "status": "active"},
        {"id": "glassdoor", "name": "Glassdoor", "type": "Employer Reviews & Jobs", "status": "active"},
        {"id": "reddit", "name": "Reddit Communities", "type": "Social Discussions", "status": "active"},
        {"id": "github", "name": "GitHub Jobs & Repos", "type": "Developer Ecosystem", "status": "active"},
        {"id": "upwork", "name": "Upwork Contracts", "type": "Freelance Marketplace", "status": "active"},
        {"id": "freelancer", "name": "Freelancer.com", "type": "Freelance Marketplace", "status": "active"},
        {"id": "website_direct", "name": "Company Career Portals", "type": "Direct Web Crawl", "status": "active"},
    ]

    return {
        "status": "success",
        "data": {
            "metrics": {
                "total_opportunities_indexed": opportunities_count,
                "total_companies_verified": companies_count,
                "contacts_discovered": contacts_count,
                "outreach_delivered": outreach_count,
                "candidates_matched": candidates_count,
                "rejection_recovery_rate": rejection_recovery_rate,
                "data_extraction_accuracy": data_extraction_accuracy,
                "active_sources_count": len(active_sources),
                "workflow_stages_count": len(workflow_stages),
            },
            "live_counts": {
                "companies": companies_count,
                "opportunities": opportunities_count,
                "contacts": contacts_count,
                "proposals": proposals_count,
                "outreach": outreach_count,
                "candidates": candidates_count,
                "rejections": rejections_count,
                "workflows": workflows_count,
            },
            "sources": active_sources,
            "workflow_stages": workflow_stages,
        },
    }
