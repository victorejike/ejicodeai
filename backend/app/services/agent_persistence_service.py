"""Agent persistence service for saving agent runs to database."""
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import AgentRun, Company, Opportunity, Contact, CompanyResearchReport
from backend.app.schemas import AgentRunStatus


class AgentPersistenceService:
    """Handle persistence of agent runs and their outputs."""

    @staticmethod
    async def create_agent_run(
        session: AsyncSession,
        agent_name: str,
        input_data: Optional[Dict[str, Any]] = None,
        parent_run_id: Optional[str] = None,
    ) -> AgentRun:
        """Create a new agent run record."""
        run_id = str(uuid.uuid4())
        
        db_run = AgentRun(
            agent_name=agent_name,
            status="pending",
            input_payload=input_data,
            trigger_type="manual",
            items_processed=0,
            items_created=0,
        )
        session.add(db_run)
        await session.commit()
        await session.refresh(db_run)
        return db_run

    @staticmethod
    async def update_agent_run(
        session: AsyncSession,
        run_id: str,
        status: AgentRunStatus = None,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ) -> Optional[AgentRun]:
        """Update an agent run with results."""
        from sqlalchemy import select
        
        import uuid as _uuid
        stmt = select(AgentRun).where(AgentRun.id == _uuid.UUID(run_id))
        result = await session.execute(stmt)
        agent_run = result.scalars().first()
        
        if not agent_run:
            return None
        
        if status:
            agent_run.status = status
        if output_data is not None:
            agent_run.output_summary = output_data
        if error_message:
            agent_run.error_message = error_message
        
        if status in (AgentRunStatus.COMPLETED, AgentRunStatus.FAILED):
            agent_run.completed_at = datetime.utcnow()
        elif status == AgentRunStatus.RUNNING:
            agent_run.started_at = datetime.utcnow()
        
        await session.commit()
        await session.refresh(agent_run)
        return agent_run

    @staticmethod
    async def save_discovered_companies(
        session: AsyncSession,
        companies_data: list,
    ) -> list:
        """Persist discovered companies from agents."""
        saved_companies = []
        
        for company_data in companies_data:
            # Check if exists by domain
            if company_data.get("domain"):
                from sqlalchemy import select
                stmt = select(Company).where(Company.domain == company_data["domain"])
                result = await session.execute(stmt)
                existing = result.scalars().first()
                if existing:
                    continue
            
            # Create new company
            db_company = Company(
                name=company_data.get("name"),
                domain=company_data.get("domain"),
                website_url=company_data.get("website"),
                industry=company_data.get("industry"),
                company_size=company_data.get("size"),
                location=company_data.get("location"),
                description=company_data.get("description"),
                fit_score=company_data.get("fit_score") or 0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(db_company)
            saved_companies.append(db_company)
        
        if saved_companies:
            await session.commit()
            for company in saved_companies:
                await session.refresh(company)
        
        return saved_companies

    @staticmethod
    async def save_discovered_opportunities(
        session: AsyncSession,
        opportunities_data: list,
    ) -> list:
        """Persist discovered opportunities from agents."""
        saved_opportunities = []
        
        for opp_data in opportunities_data:
            # Check for duplicates by source_id
            if opp_data.get("source_id") and opp_data.get("source"):
                from sqlalchemy import select, and_
                stmt = select(Opportunity).where(
                    Opportunity.source_url == opp_data.get("url", "")
                )
                result = await session.execute(stmt)
                existing = result.scalars().first()
                if existing:
                    continue
            
            # Create new opportunity
            db_opp = Opportunity(
                title=opp_data.get("title"),
                raw_description=opp_data.get("description"),
                source_url=opp_data.get("url"),
                source_platform=opp_data.get("source"),
                company_id=opp_data.get("company_id"),
                type=opp_data.get("type", "job"),
                score=opp_data.get("score") or 0,
                status=opp_data.get("status", "new"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(db_opp)
            saved_opportunities.append(db_opp)
        
        if saved_opportunities:
            await session.commit()
            for opp in saved_opportunities:
                await session.refresh(opp)
        
        return saved_opportunities

    @staticmethod
    async def save_discovered_contacts(
        session: AsyncSession,
        contacts_data: list,
    ) -> list:
        """Persist discovered contacts from agents."""
        saved_contacts = []
        
        for contact_data in contacts_data:
            # Check for duplicates by email
            if contact_data.get("email"):
                from sqlalchemy import select
                stmt = select(Contact).where(Contact.email == contact_data["email"])
                result = await session.execute(stmt)
                existing = result.scalars().first()
                if existing:
                    continue
            
            # Create new contact
            name = contact_data.get("name", "")
            parts = name.split(" ", 1) if name else []
            db_contact = Contact(
                email=contact_data.get("email"),
                first_name=contact_data.get("first_name") or (parts[0] if parts else ""),
                last_name=contact_data.get("last_name") or (parts[1] if len(parts) > 1 else ""),
                full_name=name or contact_data.get("full_name", ""),
                title=contact_data.get("title"),
                company_id=contact_data.get("company_id"),
                linkedin_url=contact_data.get("linkedin_url"),
                source=contact_data.get("source"),
                status=contact_data.get("status", "active"),
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            session.add(db_contact)
            saved_contacts.append(db_contact)
        
        if saved_contacts:
            await session.commit()
            for contact in saved_contacts:
                await session.refresh(contact)
        
        return saved_contacts

    @staticmethod
    async def save_research_report(
        session: AsyncSession,
        company_id: int,
        summary: str,
        tech_stack: Optional[list] = None,
        team_size: Optional[str] = None,
        funding_status: Optional[str] = None,
        key_metrics: Optional[Dict[str, Any]] = None,
        research_data: Optional[Dict[str, Any]] = None,
    ) -> CompanyResearchReport:
        """Save a company research report."""
        db_report = CompanyResearchReport(
            company_id=company_id,
            summary=summary,
            full_report=research_data or {},
            created_at=datetime.utcnow(),
        )
        
        session.add(db_report)
        await session.commit()
        await session.refresh(db_report)
        return db_report
