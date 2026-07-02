"""Opportunities router - CRUD endpoints for opportunities."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models import Opportunity, Company

router = APIRouter()


class OpportunityCreate(BaseModel):
    """Opportunity creation schema."""
    title: str
    type: str
    company_id: Optional[UUID] = None
    source_platform: Optional[str] = None
    location: Optional[str] = None


class OpportunityResponse(BaseModel):
    """Opportunity response schema."""
    id: UUID
    title: str
    type: str
    score: int
    status: str
    source_platform: Optional[str]
    location: Optional[str]


@router.get("", response_model=List[OpportunityResponse])
async def list_opportunities(
    skip: int = 0,
    limit: int = 10,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List opportunities."""
    query = select(Opportunity)
    if status:
        query = query.where(Opportunity.status == status)
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(opportunity_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get single opportunity."""
    opportunity = await db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    return opportunity


@router.patch("/{opportunity_id}/status")
async def update_opportunity_status(opportunity_id: UUID, new_status: str, db: AsyncSession = Depends(get_db)):
    """Update opportunity status."""
    opportunity = await db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    opportunity.status = new_status
    await db.commit()
    await db.refresh(opportunity)
    return {"status": "updated", "opportunity_id": str(opportunity.id)}


@router.post("/{opportunity_id}/trigger-research")
async def trigger_research(opportunity_id: UUID, db: AsyncSession = Depends(get_db)):
    """Manually trigger research for opportunity."""
    opportunity = await db.get(Opportunity, opportunity_id)
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")
    company = await db.get(Company, opportunity.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    try:
        from backend.tasks.agent_tasks import run_research_agent
        run_research_agent.delay(str(company.id), company.domain or "")
    except Exception:
        pass  # Celery not running in dev — fire and forget
    return {"status": "research_queued", "opportunity_id": str(opportunity_id)}
