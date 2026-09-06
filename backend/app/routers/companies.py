"""Companies router - full CRUD, search, filter, and relations."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import Company, CompanyResearchReport, Contact, Opportunity

router = APIRouter()


class CompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_org: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    funding_stage: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    fit_score: Optional[int] = 0
    fit_reasoning: Optional[str] = None
    status: Optional[str] = "discovered"


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_org: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    funding_stage: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    pain_points: Optional[List[str]] = None
    fit_score: Optional[int] = None
    fit_reasoning: Optional[str] = None
    status: Optional[str] = None


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    domain: Optional[str] = None
    website_url: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_org: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    funding_stage: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None
    tech_stack: Optional[List[str]] = []
    pain_points: Optional[List[str]] = []
    fit_score: int = 0
    fit_reasoning: Optional[str] = None
    status: str = "discovered"
    last_researched: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("", response_model=List[CompanyResponse])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    industry: Optional[str] = None,
    search: Optional[str] = None,
    min_score: Optional[int] = None,
    min_fit_score: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
):
    """List companies with search, filtering, and pagination."""
    query = select(Company)

    effective_min_score = min_fit_score if min_fit_score is not None else min_score

    if status:
        query = query.where(Company.status == status)
    if industry:
        query = query.where(Company.industry.ilike(f"%{industry}%"))
    if effective_min_score is not None:
        query = query.where(Company.fit_score >= effective_min_score)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Company.name.ilike(search_pattern))
            | (Company.domain.ilike(search_pattern))
            | (Company.description.ilike(search_pattern))
        )

    query = query.order_by(desc(Company.fit_score), desc(Company.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    """Create a new company."""
    if company.domain:
        existing = await db.execute(select(Company).where(Company.domain == company.domain))
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Company with domain '{company.domain}' already exists",
            )

    new_company = Company(
        name=company.name,
        domain=company.domain,
        website_url=company.website_url,
        linkedin_url=company.linkedin_url,
        github_org=company.github_org,
        industry=company.industry,
        company_size=company.company_size,
        funding_stage=company.funding_stage,
        location=company.location,
        description=company.description,
        tech_stack=company.tech_stack or [],
        pain_points=company.pain_points or [],
        fit_score=company.fit_score or 0,
        fit_reasoning=company.fit_reasoning,
        status=company.status or "discovered",
    )
    db.add(new_company)
    await db.commit()
    await db.refresh(new_company)
    return new_company


@router.get("/{company_id}", response_model=CompanyResponse)
async def get_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get company by ID."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


@router.patch("/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    company: CompanyUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update company details."""
    existing = await db.get(Company, company_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    update_data = company.model_dump(exclude_unset=True)
    if "domain" in update_data and update_data["domain"] != existing.domain:
        conflict = await db.execute(
            select(Company).where(Company.domain == update_data["domain"], Company.id != company_id)
        )
        if conflict.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Domain '{update_data['domain']}' already in use",
            )

    for field, value in update_data.items():
        setattr(existing, field, value)

    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a company and cascade to contacts and reports."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    await db.delete(company)
    await db.commit()


@router.get("/{company_id}/contacts")
async def get_company_contacts(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all contacts associated with a company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    result = await db.execute(select(Contact).where(Contact.company_id == company_id))
    return result.scalars().all()


@router.get("/{company_id}/opportunities")
async def get_company_opportunities(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get all opportunities associated with a company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    result = await db.execute(select(Opportunity).where(Opportunity.company_id == company_id))
    return result.scalars().all()


@router.get("/{company_id}/research")
async def get_company_research(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get research reports for a company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    result = await db.execute(
        select(CompanyResearchReport)
        .where(CompanyResearchReport.company_id == company_id)
        .order_by(desc(CompanyResearchReport.created_at))
    )
    return result.scalars().all()


@router.post("/{company_id}/research")
async def trigger_research(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Queue or execute research agent for a company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

    try:
        from backend.tasks.agent_tasks import run_research_agent
        task = run_research_agent.delay(str(company.id), company.domain or "")
        return {"status": "research_queued", "company_id": str(company_id), "task_id": task.id}
    except Exception:
        # Fallback to direct agent execution when Celery worker is offline
        from agents.research.research_agent import ResearchAgent
        agent = ResearchAgent()
        state = {
            "status": "pending",
            "input_data": {"company_id": str(company_id), "domain": company.domain or ""},
            "output_data": {},
        }
        res = await agent.process(state)
        return {"status": "research_executed", "company_id": str(company_id), "output": res.get("output_data")}
