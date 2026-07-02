"""Agents router — status, runs, and direct trigger."""
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import AgentRun, Company, Contact, Opportunity

router = APIRouter()
logger = logging.getLogger(__name__)

KNOWN_AGENTS = [
    "supervisor", "job_scout", "company_scout", "research",
    "ranking", "contact_discovery", "knowledge_base",
    "proposal_generation", "outreach", "reply_monitoring",
]


class AgentRunResponse(BaseModel):
    id: str
    agent_name: str
    trigger_type: Optional[str]
    status: str
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_ms: Optional[int]
    items_processed: int
    items_created: int
    error_message: Optional[str]


def _base_state(agent_name: str) -> dict:
    from agents.base.base_agent import AgentStatus
    return {
        "status": AgentStatus.PENDING,
        "input_data": {"trigger_type": "manual"},
        "output_data": {},
        "messages": [],
        "current_step": "init",
        "steps_completed": [],
        "error_count": 0,
        "confidence_score": 1.0,
        "quality_checks_passed": True,
    }


@router.get("/status")
async def get_agent_status(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentRun).order_by(AgentRun.started_at.desc()).limit(200))
    runs = result.scalars().all()
    latest: dict = {}
    for run in runs:
        if run.agent_name not in latest:
            latest[run.agent_name] = {
                "agent_name": run.agent_name,
                "status": run.status,
                "last_run": run.started_at.isoformat() if run.started_at else None,
                "last_duration_ms": run.duration_ms,
                "last_error": run.error_message,
            }
    for name in KNOWN_AGENTS:
        if name not in latest:
            latest[name] = {"agent_name": name, "status": "never_run", "last_run": None,
                            "last_duration_ms": None, "last_error": None}
    return list(latest.values())


@router.get("/runs", response_model=List[AgentRunResponse])
async def list_agent_runs(
    skip: int = 0, limit: int = 50,
    agent_name: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    query = select(AgentRun).order_by(AgentRun.started_at.desc())
    if agent_name:
        query = query.where(AgentRun.agent_name == agent_name)
    result = await db.execute(query.offset(skip).limit(limit))
    runs = result.scalars().all()
    return [AgentRunResponse(
        id=str(r.id), agent_name=r.agent_name, trigger_type=r.trigger_type,
        status=r.status,
        started_at=r.started_at.isoformat() if r.started_at else None,
        completed_at=r.completed_at.isoformat() if r.completed_at else None,
        duration_ms=r.duration_ms, items_processed=r.items_processed or 0,
        items_created=r.items_created or 0, error_message=r.error_message,
    ) for r in runs]


# ---------------------------------------------------------------------------
# Agent runner implementations
# ---------------------------------------------------------------------------

async def _run_job_scout(db: AsyncSession, run: AgentRun):
    from agents.job_scout.job_scout_agent import JobScoutAgent
    from agents.base.base_agent import AgentStatus

    agent = JobScoutAgent()
    result = await agent.process(_base_state("job_scout"))
    opportunities = result.get("output_data", {}).get("opportunities", [])

    created = 0
    for opp in opportunities:
        url = opp.get("url", "")
        if not url:
            continue
        existing = await db.execute(select(Opportunity).where(Opportunity.source_url == url))
        if existing.scalars().first():
            continue
        db.add(Opportunity(
            title=opp.get("title", "Untitled")[:255],
            type=opp.get("type", "job"),
            status="new",
            source_platform=opp.get("source_platform", "unknown"),
            source_url=url,
            location=opp.get("location", ""),
            raw_description=opp.get("description", ""),
            score=0,
        ))
        created += 1

    await db.commit()
    run.items_processed = len(opportunities)
    run.items_created = created
    run.status = "success" if result.get("status") == AgentStatus.SUCCESS else "failure"
    run.error_message = result.get("error_message")


async def _run_company_scout(db: AsyncSession, run: AgentRun):
    from agents.company_scout.company_scout_agent import CompanyScoutAgent
    from agents.base.base_agent import AgentStatus

    agent = CompanyScoutAgent()
    result = await agent.process(_base_state("company_scout"))
    companies = result.get("output_data", {}).get("companies", [])

    created = 0
    for c in companies:
        domain = c.get("domain", "")
        if not domain:
            continue
        existing = await db.execute(select(Company).where(Company.domain == domain))
        if existing.scalars().first():
            continue
        db.add(Company(
            name=c.get("name", domain)[:255],
            domain=domain[:255],
            website_url=c.get("website", ""),
            industry=c.get("industry", "Technology"),
            description=c.get("description", ""),
            status="discovered",
            fit_score=0,
        ))
        created += 1

    await db.commit()
    run.items_processed = len(companies)
    run.items_created = created
    run.status = "success" if result.get("status") == AgentStatus.SUCCESS else "failure"
    run.error_message = result.get("error_message")


async def _run_ranking(db: AsyncSession, run: AgentRun):
    from agents.ranking.ranking_agent import RankingAgent
    from agents.base.base_agent import AgentStatus

    result_q = await db.execute(select(Opportunity).where(Opportunity.score == 0))
    opps = result_q.scalars().all()

    if not opps:
        run.status = "success"
        run.items_processed = 0
        run.items_created = 0
        return

    agent = RankingAgent()
    opp_dicts = [{
        "id": str(o.id), "title": o.title, "type": o.type,
        "source_platform": o.source_platform, "location": o.location,
    } for o in opps]

    state = _base_state("ranking")
    state["input_data"] = {"opportunities": opp_dicts, "companies": {}}
    result = await agent.process(state)
    scored = result.get("output_data", {}).get("opportunities", [])

    for scored_opp in scored:
        opp_id = scored_opp.get("id")
        score = scored_opp.get("score", 0)
        for o in opps:
            if str(o.id) == opp_id:
                o.score = score
                o.score_breakdown = scored_opp.get("score_breakdown")
                o.rank = scored_opp.get("rank")
                break

    await db.commit()
    run.items_processed = len(opps)
    run.items_created = 0
    run.status = "success"


async def _run_research(db: AsyncSession, run: AgentRun):
    from agents.research.research_agent import ResearchAgent
    from backend.app.models.core import CompanyResearchReport
    from agents.base.base_agent import AgentStatus

    # Research top 5 unresearched companies
    result_q = await db.execute(
        select(Company)
        .where(Company.last_researched == None)
        .where(Company.domain != None)
        .limit(5)
    )
    companies = result_q.scalars().all()

    if not companies:
        run.status = "success"
        run.items_processed = 0
        run.items_created = 0
        return

    agent = ResearchAgent()
    created = 0
    for company in companies:
        state = _base_state("research")
        state["input_data"] = {"company_id": str(company.id), "domain": company.domain}
        result = await agent.process(state)

        if result.get("status") == AgentStatus.SUCCESS:
            output = result.get("output_data", {})
            analysis = output.get("analysis", {})

            # Update company fit score and pain points
            fit_score = analysis.get("ejicode_fit_score", 0)
            company.fit_score = min(int(fit_score), 100)
            company.pain_points = analysis.get("pain_points", [])
            company.last_researched = datetime.utcnow()

            # Save research report
            report = CompanyResearchReport(
                company_id=company.id,
                summary=analysis.get("recommended_angle", ""),
                full_report=output,
                model_used=output.get("tech_stack", {}).get("model", ""),
            )
            db.add(report)
            created += 1

    await db.commit()
    run.items_processed = len(companies)
    run.items_created = created
    run.status = "success"


async def _run_contact_discovery(db: AsyncSession, run: AgentRun):
    from agents.contact_discovery.contact_discovery_agent import ContactDiscoveryAgent
    from agents.base.base_agent import AgentStatus

    # Discover contacts for top researched companies with no contacts yet
    result_q = await db.execute(
        select(Company)
        .where(Company.last_researched != None)
        .where(Company.domain != None)
        .limit(5)
    )
    companies = result_q.scalars().all()

    if not companies:
        run.status = "success"
        run.items_processed = 0
        run.items_created = 0
        return

    agent = ContactDiscoveryAgent()
    created = 0
    for company in companies:
        # Skip if already has contacts
        existing_q = await db.execute(
            select(Contact).where(Contact.company_id == company.id).limit(1)
        )
        if existing_q.scalars().first():
            continue

        state = _base_state("contact_discovery")
        state["input_data"] = {
            "company_id": str(company.id),
            "domain": company.domain,
            "company_name": company.name,
        }
        result = await agent.process(state)

        if result.get("status") == AgentStatus.SUCCESS:
            contacts = result.get("output_data", {}).get("contacts", [])
            for c in contacts:
                email = c.get("email", "")
                if not email:
                    continue
                # Check duplicate email
                dup = await db.execute(select(Contact).where(Contact.email == email))
                if dup.scalars().first():
                    continue
                name = c.get("name", "")
                parts = name.split(" ", 1) if name else ["", ""]
                db.add(Contact(
                    company_id=company.id,
                    email=email,
                    first_name=parts[0] if parts else "",
                    last_name=parts[1] if len(parts) > 1 else "",
                    full_name=name,
                    title=c.get("title", ""),
                    email_confidence=c.get("confidence", "unverified"),
                    is_decision_maker=c.get("is_decision_maker", False),
                    source=c.get("source", "agent"),
                    status="active",
                ))
                created += 1

    await db.commit()
    run.items_processed = len(companies)
    run.items_created = created
    run.status = "success"


async def _run_knowledge_base(db: AsyncSession, run: AgentRun):
    from agents.knowledge_base.knowledge_base_agent import KnowledgeBaseAgent
    from agents.base.base_agent import AgentStatus
    from backend.app.models.core import CompanyResearchReport

    # Sync latest research reports into ChromaDB
    result_q = await db.execute(
        select(CompanyResearchReport)
        .where(CompanyResearchReport.embedding_id == None)
        .limit(20)
    )
    reports = result_q.scalars().all()

    documents = []
    for r in reports:
        text = r.summary or ""
        if r.full_report:
            analysis = r.full_report.get("analysis", {})
            text += " " + " ".join(analysis.get("pain_points", []))
        documents.append({"id": str(r.id), "text": text, "metadata": {"company_id": str(r.company_id)}})

    agent = KnowledgeBaseAgent()
    state = _base_state("knowledge_base")
    state["input_data"] = {"operation": "sync", "documents": documents}
    result = await agent.process(state)

    stored = result.get("output_data", {}).get("stored_documents", 0)

    # Mark reports as embedded
    for r in reports:
        r.embedding_id = f"chroma_{r.id}"
    await db.commit()

    run.items_processed = len(documents)
    run.items_created = stored
    run.status = "success" if result.get("status") == AgentStatus.SUCCESS else "failure"


async def _run_reply_monitoring(db: AsyncSession, run: AgentRun):
    from agents.reply_monitoring.reply_monitoring_agent import ReplyMonitoringAgent
    from backend.app.services.outreach_service import update_outreach_reply
    from agents.base.base_agent import AgentStatus

    agent = ReplyMonitoringAgent()
    state = _base_state("reply_monitoring")
    result = await agent.process(state)

    replies = result.get("output_data", {}).get("replies", [])
    created = 0
    for reply in replies:
        in_reply_to = reply.get("in_reply_to", "")
        if not in_reply_to:
            continue
        updated = await update_outreach_reply(
            db,
            message_id=in_reply_to,
            reply_content=reply.get("content", ""),
            reply_classification=reply.get("classification", "UNKNOWN"),
            replied_at=reply.get("received_at"),
        )
        if updated:
            created += 1

    await db.commit()
    run.items_processed = len(replies)
    run.items_created = created
    run.status = "success"


async def _run_supervisor(db: AsyncSession, run: AgentRun):
    """Run the full pipeline: scout → rank → research → contacts → knowledge base."""
    sub_runs = []
    for agent_name, runner in [
        ("job_scout", _run_job_scout),
        ("company_scout", _run_company_scout),
        ("ranking", _run_ranking),
        ("research", _run_research),
        ("contact_discovery", _run_contact_discovery),
        ("knowledge_base", _run_knowledge_base),
    ]:
        sub_run = AgentRun(
            agent_name=agent_name,
            trigger_type="supervisor",
            status="pending",
            started_at=datetime.utcnow(),
            items_processed=0,
            items_created=0,
        )
        db.add(sub_run)
        await db.commit()
        try:
            await runner(db, sub_run)
        except Exception as e:
            sub_run.status = "failure"
            sub_run.error_message = str(e)[:500]
        finally:
            sub_run.completed_at = datetime.utcnow()
            if sub_run.started_at:
                sub_run.duration_ms = int(
                    (sub_run.completed_at - sub_run.started_at).total_seconds() * 1000
                )
        await db.commit()
        sub_runs.append(sub_run)

    total_created = sum(s.items_created or 0 for s in sub_runs)
    total_processed = sum(s.items_processed or 0 for s in sub_runs)
    failures = [s.agent_name for s in sub_runs if s.status == "failure"]

    run.items_processed = total_processed
    run.items_created = total_created
    run.status = "failure" if len(failures) == len(sub_runs) else "success"
    if failures:
        run.error_message = f"Partial failures: {', '.join(failures)}"


AGENT_RUNNERS = {
    "job_scout": _run_job_scout,
    "company_scout": _run_company_scout,
    "ranking": _run_ranking,
    "research": _run_research,
    "contact_discovery": _run_contact_discovery,
    "knowledge_base": _run_knowledge_base,
    "reply_monitoring": _run_reply_monitoring,
    "supervisor": _run_supervisor,
}


async def _execute_agent(agent_name: str, run_id: str):
    from backend.app.database import async_session
    async with async_session() as db:
        result = await db.execute(select(AgentRun).where(AgentRun.id == run_id))
        run = result.scalars().first()
        if not run:
            return

        run.status = "running"
        run.started_at = datetime.utcnow()
        await db.commit()

        start = datetime.utcnow()
        try:
            runner = AGENT_RUNNERS.get(agent_name)
            if runner:
                await runner(db, run)
            else:
                # proposal_generation and outreach are triggered per-record, not in bulk
                run.status = "success"
                run.items_processed = 0
                run.items_created = 0
        except Exception as e:
            logger.error(f"Agent {agent_name} error: {e}", exc_info=True)
            run.status = "failure"
            run.error_message = str(e)[:500]
        finally:
            run.completed_at = datetime.utcnow()
            run.duration_ms = int((datetime.utcnow() - start).total_seconds() * 1000)
            await db.commit()


@router.post("/{agent_name}/trigger")
async def trigger_agent(
    agent_name: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    if agent_name not in KNOWN_AGENTS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown agent: {agent_name}")

    import uuid as _uuid
    run = AgentRun(
        id=_uuid.uuid4(),
        agent_name=agent_name,
        trigger_type="manual",
        status="pending",
        started_at=datetime.utcnow(),
        items_processed=0,
        items_created=0,
    )
    db.add(run)
    await db.commit()

    run_id = str(run.id)
    background_tasks.add_task(_execute_agent, agent_name, run_id)
    return {"status": "triggered", "agent": agent_name, "run_id": run_id}
