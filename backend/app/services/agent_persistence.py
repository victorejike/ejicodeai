"""Agent persistence service - saves scraped leads, rankings, research, and execution logs."""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import async_session
from backend.app.models.core import (
    AgentRun,
    Company,
    CompanyResearchReport,
    Contact,
    Opportunity,
    Proposal,
)

logger = logging.getLogger(__name__)


class AgentPersistenceService:
    """Handles database persistence for multi-agent workflows."""

    @staticmethod
    async def record_run_start(agent_name: str, trigger_type: str = "manual", input_payload: Optional[Dict[str, Any]] = None) -> str:
        """Create an AgentRun record in running status."""
        run_id = str(uuid4())
        try:
            async with async_session() as session:
                run = AgentRun(
                    id=run_id,
                    agent_name=agent_name,
                    trigger_type=trigger_type,
                    status="running",
                    started_at=datetime.now(timezone.utc),
                    input_payload=input_payload or {},
                    items_processed=0,
                    items_created=0,
                )
                session.add(run)
                await session.commit()
        except Exception as exc:
            logger.warning("Could not record agent run start: %s", exc)
        return run_id

    @staticmethod
    async def record_run_completion(
        run_id: str,
        status: str = "completed",
        duration_ms: Optional[int] = None,
        items_processed: int = 0,
        items_created: int = 0,
        output_summary: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> None:
        """Update an AgentRun record with completion results."""
        try:
            async with async_session() as session:
                run = await session.get(AgentRun, run_id)
                if run:
                    run.status = status
                    run.completed_at = datetime.now(timezone.utc)
                    if duration_ms is not None:
                        run.duration_ms = duration_ms
                    elif run.started_at:
                        run.duration_ms = int(
                            (datetime.now(timezone.utc) - run.started_at.replace(tzinfo=timezone.utc)).total_seconds() * 1000
                        )
                    run.items_processed = items_processed
                    run.items_created = items_created
                    run.output_summary = output_summary or {}
                    run.error_message = error_message
                    await session.commit()
        except Exception as exc:
            logger.warning("Could not update agent run completion: %s", exc)

    @staticmethod
    async def save_companies(companies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Persist or update discovered companies, deduplicating on domain."""
        saved: List[Dict[str, Any]] = []
        if not companies:
            return saved

        try:
            async with async_session() as session:
                for item in companies:
                    name = item.get("name") or item.get("company_name") or "Unknown Company"
                    domain = item.get("domain") or item.get("company_domain")
                    if domain:
                        domain = domain.lower().replace("http://", "").replace("https://", "").strip("/")

                    existing = None
                    if domain:
                        res = await session.execute(select(Company).where(Company.domain == domain))
                        existing = res.scalars().first()
                    if not existing and name:
                        res = await session.execute(select(Company).where(Company.name == name))
                        existing = res.scalars().first()

                    if existing:
                        # Update fields
                        if item.get("tech_stack"):
                            existing.tech_stack = list(set((existing.tech_stack or []) + item["tech_stack"]))
                        if item.get("fit_score") is not None:
                            existing.fit_score = max(existing.fit_score or 0, item["fit_score"])
                        if item.get("description") and not existing.description:
                            existing.description = item["description"]
                        if item.get("website_url") and not existing.website_url:
                            existing.website_url = item["website_url"]
                        saved.append({"id": str(existing.id), "name": existing.name, "domain": existing.domain})
                    else:
                        new_c = Company(
                            name=name,
                            domain=domain,
                            website_url=item.get("website_url") or (f"https://{domain}" if domain else None),
                            linkedin_url=item.get("linkedin_url"),
                            github_org=item.get("github_org"),
                            industry=item.get("industry") or "Technology",
                            company_size=item.get("company_size") or "11-50",
                            funding_stage=item.get("funding_stage"),
                            location=item.get("location") or "Remote",
                            description=item.get("description") or f"{name} technology operations.",
                            tech_stack=item.get("tech_stack") or [],
                            pain_points=item.get("pain_points") or [],
                            fit_score=item.get("fit_score") or 70,
                            fit_reasoning=item.get("fit_reasoning"),
                            status="discovered",
                        )
                        session.add(new_c)
                        await session.flush()
                        saved.append({"id": str(new_c.id), "name": new_c.name, "domain": new_c.domain})

                await session.commit()
        except Exception as exc:
            logger.error("Failed to persist companies: %s", exc)

        return saved

    @staticmethod
    async def save_opportunities(opportunities: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Persist opportunities, deduplicating on source_url."""
        saved: List[Dict[str, Any]] = []
        if not opportunities:
            return saved

        try:
            async with async_session() as session:
                for opp in opportunities:
                    source_url = opp.get("source_url") or opp.get("url")
                    title = opp.get("title") or "Engineering Opportunity"
                    company_name = opp.get("company") or opp.get("company_name")

                    # Link company if known
                    company_id = opp.get("company_id")
                    if not company_id and company_name:
                        c_res = await session.execute(select(Company).where(Company.name == company_name))
                        c = c_res.scalars().first()
                        if c:
                            company_id = c.id

                    existing = None
                    if source_url:
                        res = await session.execute(select(Opportunity).where(Opportunity.source_url == source_url))
                        existing = res.scalars().first()

                    if existing:
                        if opp.get("score") is not None:
                            existing.score = opp["score"]
                        if opp.get("rank") is not None:
                            existing.rank = opp["rank"]
                        saved.append({"id": str(existing.id), "title": existing.title, "company_id": str(existing.company_id)})
                    else:
                        new_opp = Opportunity(
                            company_id=company_id,
                            title=title,
                            type=opp.get("type") or "contract",
                            source_platform=opp.get("source_platform") or opp.get("source") or "RemoteOK",
                            source_url=source_url or f"https://example.com/opp/{uuid4()}",
                            raw_description=opp.get("raw_description") or opp.get("description") or "",
                            location_type=opp.get("location_type") or "remote",
                            location=opp.get("location") or "Remote",
                            salary_min=opp.get("salary_min"),
                            salary_max=opp.get("salary_max"),
                            tech_required=opp.get("tech_required") or opp.get("tags") or [],
                            score=opp.get("score") or 75,
                            score_breakdown=opp.get("score_breakdown") or {},
                            rank=opp.get("rank"),
                            status="new",
                        )
                        session.add(new_opp)
                        await session.flush()
                        saved.append({"id": str(new_opp.id), "title": new_opp.title, "company_id": str(company_id)})

                await session.commit()
        except Exception as exc:
            logger.error("Failed to persist opportunities: %s", exc)

        return saved

    @staticmethod
    async def save_contacts(contacts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Persist contacts, deduplicating on email."""
        saved: List[Dict[str, Any]] = []
        if not contacts:
            return saved

        try:
            async with async_session() as session:
                for ct in contacts:
                    email = ct.get("email")
                    if not email:
                        continue

                    res = await session.execute(select(Contact).where(Contact.email == email))
                    existing = res.scalars().first()

                    company_id = ct.get("company_id")
                    if not company_id and ct.get("company_name"):
                        c_res = await session.execute(select(Company).where(Company.name == ct["company_name"]))
                        c = c_res.scalars().first()
                        if c:
                            company_id = c.id

                    if existing:
                        if ct.get("title"):
                            existing.title = ct["title"]
                        if ct.get("is_decision_maker") is not None:
                            existing.is_decision_maker = ct["is_decision_maker"]
                        saved.append({"id": str(existing.id), "email": existing.email})
                    else:
                        new_ct = Contact(
                            company_id=company_id,
                            email=email,
                            first_name=ct.get("first_name"),
                            last_name=ct.get("last_name"),
                            full_name=ct.get("full_name") or f"{ct.get('first_name', '')} {ct.get('last_name', '')}".strip() or email,
                            title=ct.get("title") or "Engineering Leader",
                            role_category=ct.get("role_category") or "engineering",
                            is_decision_maker=ct.get("is_decision_maker", False),
                            linkedin_url=ct.get("linkedin_url"),
                            email_confidence=ct.get("email_confidence", "verified"),
                            source=ct.get("source", "scout"),
                            notes=ct.get("notes"),
                            status="active",
                        )
                        session.add(new_ct)
                        await session.flush()
                        saved.append({"id": str(new_ct.id), "email": new_ct.email})

                await session.commit()
        except Exception as exc:
            logger.error("Failed to persist contacts: %s", exc)

        return saved

    @staticmethod
    async def save_research_report(company_id: str, report_data: Dict[str, Any]) -> Optional[str]:
        """Save company research report and update company fit reasoning."""
        try:
            async with async_session() as session:
                company = await session.get(Company, company_id)
                report_id = str(uuid4())
                summary = report_data.get("summary") or "Comprehensive company profile and engineering pain-point audit."
                fit_score = report_data.get("fit_score", 85)

                rep = CompanyResearchReport(
                    id=report_id,
                    company_id=company_id,
                    report_type="deep_dive",
                    summary=summary,
                    full_report=report_data,
                    sources_used=report_data.get("sources_used", ["Google Search", "Company Website", "LinkedIn"]),
                    model_used=report_data.get("model_used", "gemini-2.5-flash"),
                )
                session.add(rep)

                if company:
                    company.fit_score = fit_score
                    company.fit_reasoning = summary
                    company.status = "researched"
                    company.last_researched = datetime.now(timezone.utc)

                await session.commit()
                return report_id
        except Exception as exc:
            logger.error("Failed to save research report: %s", exc)
            return None
