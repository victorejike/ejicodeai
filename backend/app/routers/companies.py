"""Companies router - full CRUD + research trigger."""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models import Company

router = APIRouter()


class CompanyCreate(BaseModel):
    name: str
    domain: Optional[str] = None
    industry: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    company_size: Optional[str] = None
    location: Optional[str] = None


class CompanyResponse(BaseModel):
    id: UUID
    name: str
    domain: Optional[str]
    industry: Optional[str]
    website_url: Optional[str]
    fit_score: int
    status: str


@router.get("", response_model=list[CompanyResponse])
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List companies with optional status filter."""
    query = select(Company)
    if status:
        query = query.where(Company.status == status)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.post("", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    """Create a new company."""
    if company.domain:
        existing = await db.execute(select(Company).where(Company.domain == company.domain))
        if existing.scalars().first():
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Company with this domain already exists")

    new_company = Company(
        name=company.name,
        domain=company.domain,
        industry=company.industry,
        website_url=company.website_url,
        description=company.description,
        company_size=company.company_size,
        location=company.location,
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
async def update_company(company_id: UUID, company: CompanyCreate, db: AsyncSession = Depends(get_db)):
    """Update company fields."""
    existing = await db.get(Company, company_id)
    if not existing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    for field, value in company.model_dump(exclude_unset=True).items():
        setattr(existing, field, value)
    await db.commit()
    await db.refresh(existing)
    return existing


@router.delete("/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    await db.delete(company)
    await db.commit()


@router.post("/{company_id}/research")
async def trigger_research(company_id: UUID, db: AsyncSession = Depends(get_db)):
    """Queue research agent for a company."""
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    try:
        from backend.tasks.agent_tasks import run_research_agent
        task = run_research_agent.delay(str(company.id), company.domain or "")
        return {"status": "research_queued", "company_id": str(company_id), "task_id": task.id}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
