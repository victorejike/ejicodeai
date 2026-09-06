"""Opportunities router - full CRUD, scoring, filters, and research triggers."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import Company, Opportunity

router = APIRouter()


class OpportunityCreate(BaseModel):
    title: str
    type: str
    company_id: Optional[UUID] = None
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    raw_description: Optional[str] = None
    location_type: Optional[str] = "remote"
    location: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "USD"
    tech_required: Optional[List[str]] = None
    score: Optional[int] = 0
    rank: Optional[int] = None
    status: Optional[str] = "new"


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    type: Optional[str] = None
    company_id: Optional[UUID] = None
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    raw_description: Optional[str] = None
    location_type: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = None
    tech_required: Optional[List[str]] = None
    score: Optional[int] = None
    rank: Optional[int] = None
    status: Optional[str] = None


class OpportunityResponse(BaseModel):
    id: UUID
    title: str
    type: str
    company_id: Optional[UUID] = None
    source_platform: Optional[str] = None
    source_url: Optional[str] = None
    raw_description: Optional[str] = None
    location_type: Optional[str] = None
    location: Optional[str] = None
    salary_min: Optional[float] = None
    salary_max: Optional[float] = None
    salary_currency: Optional[str] = "USD"
    tech_required: Optional[List[str]] = []
    score: int = 0
    rank: Optional[int] = None
    status: str = "new"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("", response_model=List[OpportunityResponse])
async def list_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    type: Optional[str] = None,
    company_id: Optional[UUID] = None,
    min_score: Optional[int] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List opportunities with filters and search."""
    query = select(Opportunity)

    if status:
        query = query.where(Opportunity.status == status)
    if type:
        query = query.where(Opportunity.type == type)
    if company_id:
        query = query.where(Opportunity.company_id == company_id)
    if min_score is not None:
        query = query.where(Opportunity.score >= min_score)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Opportunity.title.ilike(search_pattern))
            | (Opportunity.raw_description.ilike(search_pattern))
            | (Opportunity.location.ilike(search_pattern))
        )

    query = query.order_by(desc(Opportunity.score), desc(Opportunity.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=OpportunityResponse, status_code=status.HTTP_201_CREATED)
async def create_opportunity(data: OpportunityCreate, db: AsyncSession = Depends(get_db)):
    """Create a new opportunity."""
    if data.source_url:
        existing = await db.execute(select(Opportunity).where(Opportunity.source_url == data.source_url))
        if existing.scalars().first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Opportunity with this source URL already exists",
            )

    opp = Opportunity(
        title=data.title,
        type=data.type,
        company_id=data.company_id,
        source_platform=data.source_platform,
        source_url=data.source_url,
        raw_description=data.raw_description,
        location_type=data.location_type,
        location=data.location,
        salary_min=data.salary_min,
        salary_max=data.salary_max,
        salary_currency=data.salary_currency or "USD",
        tech_required=data.tech_required or [],
        score=data.score or 0,
        rank=data.rank,
        status=data.status or "new",
    )
    db.add(opp)
    await db.commit()
    await db.refresh(opp)
    return opp


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(opportunity_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get single opportunity by ID."""
    opportunity = await db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return opportunity


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
async def update_opportunity(
    opportunity_id: UUID,
    data: OpportunityUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update opportunity attributes."""
    opportunity = await db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(opportunity, field, value)

    await db.commit()
    await db.refresh(opportunity)
    return opportunity


@router.patch("/{opportunity_id}/status")
async def update_opportunity_status(
    opportunity_id: UUID,
    new_status: str = Query(..., description="Target status"),
    db: AsyncSession = Depends(get_db),
):
    """Update opportunity status."""
    opportunity = await db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    opportunity.status = new_status
    await db.commit()
    await db.refresh(opportunity)
    return {"status": "updated", "opportunity_id": str(opportunity.id), "new_status": new_status}


@router.delete("/{opportunity_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opportunity(opportunity_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete an opportunity."""
    opp = await db.get(Opportunity, opportunity_id)
    if not opp:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    await db.delete(opp)
    await db.commit()


@router.post("/{opportunity_id}/trigger-research")
async def trigger_research(opportunity_id: UUID, db: AsyncSession = Depends(get_db)):
    """Trigger research for opportunity company."""
    opportunity = await db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    if not opportunity.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Opportunity has no linked company")

    company = await db.get(Company, opportunity.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked company not found")

    try:
        from backend.tasks.agent_tasks import run_research_agent
        task = run_research_agent.delay(str(company.id), company.domain or "")
        return {"status": "research_queued", "opportunity_id": str(opportunity_id), "task_id": task.id}
    except Exception:
        from agents.research.research_agent import ResearchAgent
        agent = ResearchAgent()
        res = await agent.process({
            "status": "pending",
            "input_data": {"company_id": str(company.id), "domain": company.domain or ""},
            "output_data": {},
        })
        return {"status": "research_executed", "opportunity_id": str(opportunity_id), "output": res.get("output_data")}
