"""Proposals router - proposal generation, editing, human review, and approval."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import Company, Contact, Opportunity, Proposal
from backend.app.services.proposal_service import (
    create_proposal,
    get_company,
    get_contact,
    get_opportunity,
    update_proposal_status,
)
from agents.base.base_agent import AgentStatus
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent

router = APIRouter()


class ProposalResponse(BaseModel):
    id: UUID
    opportunity_id: Optional[UUID] = None
    contact_id: Optional[UUID] = None
    type: Optional[str] = None
    subject: Optional[str] = None
    body: str
    tone: Optional[str] = "professional"
    word_count: Optional[int] = None
    generation_model: Optional[str] = None
    status: str = "draft"
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProposalCreate(BaseModel):
    opportunity_id: UUID
    contact_id: UUID
    type: str = "cold_email"
    subject: str
    body: str
    tone: str = "professional"


class ProposalUpdate(BaseModel):
    subject: Optional[str] = None
    body: Optional[str] = None
    tone: Optional[str] = None
    status: Optional[str] = None


class ProposalGenerateRequest(BaseModel):
    opportunity_id: UUID
    contact_id: UUID
    type: str = "cold_email"
    tone: str = "professional"


@router.get("", response_model=List[ProposalResponse])
async def list_proposals(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    opportunity_id: Optional[UUID] = None,
    contact_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """List proposals with filters."""
    query = select(Proposal)
    if status:
        query = query.where(Proposal.status == status)
    if opportunity_id:
        query = query.where(Proposal.opportunity_id == opportunity_id)
    if contact_id:
        query = query.where(Proposal.contact_id == contact_id)

    result = await db.execute(query.order_by(desc(Proposal.created_at)).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal_by_id(proposal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get proposal by ID."""
    proposal = await db.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return proposal


@router.post("", response_model=ProposalResponse, status_code=status.HTTP_201_CREATED)
async def create_manual_proposal(data: ProposalCreate, db: AsyncSession = Depends(get_db)):
    """Create a manual proposal."""
    words = len(data.body.split())
    proposal = await create_proposal(
        db,
        opportunity_id=str(data.opportunity_id),
        contact_id=str(data.contact_id),
        proposal_type=data.type,
        tone=data.tone,
        subject=data.subject,
        body=data.body,
        word_count=words,
        generation_model="manual",
    )
    return proposal


@router.post("/generate", response_model=ProposalResponse)
async def generate_proposal(
    request: ProposalGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate proposal using AI agent with RAG context."""
    opportunity = await get_opportunity(db, str(request.opportunity_id))
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    contact = await get_contact(db, str(request.contact_id))
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    company = await get_company(db, str(opportunity.company_id)) if opportunity.company_id else None

    agent = ProposalGenerationAgent()
    state = {
        "status": "pending",
        "input_data": {
            "opportunity_id": str(request.opportunity_id),
            "contact_id": str(request.contact_id),
            "type": request.type,
            "tone": request.tone,
            "opportunity_data": {
                "title": opportunity.title,
                "type": opportunity.type,
                "source_platform": opportunity.source_platform,
                "raw_description": opportunity.raw_description,
                "tech_required": opportunity.tech_required or [],
            },
            "contact_data": {
                "id": str(contact.id),
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "title": contact.title,
            },
            "company_data": {
                "id": str(company.id) if company else "",
                "name": company.name if company else "",
                "domain": company.domain if company else "",
                "industry": company.industry if company else "",
                "description": company.description if company else "",
                "tech_stack": company.tech_stack if company else [],
            },
        },
        "output_data": {},
        "messages": [],
        "current_step": "initialization",
        "steps_completed": [],
        "error_count": 0,
        "confidence_score": 1.0,
        "quality_checks_passed": True,
    }
    result_state = await agent.process(state)

    if result_state.get("status") != AgentStatus.SUCCESS:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result_state.get("error_message", "Proposal generation failed"),
        )

    output = result_state.get("output_data", {})
    proposal = await create_proposal(
        db,
        opportunity_id=str(request.opportunity_id),
        contact_id=str(request.contact_id),
        proposal_type=request.type,
        tone=request.tone,
        subject=output.get("subject", "Opportunity Collaboration from Ejicode"),
        body=output.get("body", ""),
        word_count=output.get("word_count", 0),
        generation_model=output.get("generation_model", "gemini-2.5-flash"),
        generation_prompt=output.get("generation_prompt", ""),
        rag_context={"items": output.get("rag_context", [])},
    )

    return proposal


@router.patch("/{proposal_id}", response_model=ProposalResponse)
async def update_proposal(
    proposal_id: UUID,
    data: ProposalUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Edit proposal subject, body, or status."""
    proposal = await db.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(proposal, field, value)

    if data.body:
        proposal.word_count = len(data.body.split())

    await db.commit()
    await db.refresh(proposal)
    return proposal


@router.patch("/{proposal_id}/approve")
async def approve_proposal(proposal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Approve proposal for outreach sending."""
    proposal = await update_proposal_status(db, str(proposal_id), "approved", approved_by="human_operator")
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return {"status": proposal.status, "id": proposal.id}


@router.patch("/{proposal_id}/reject")
async def reject_proposal(proposal_id: UUID, reason: str = Query("Rejected by reviewer"), db: AsyncSession = Depends(get_db)):
    """Reject proposal with feedback reason."""
    proposal = await update_proposal_status(db, str(proposal_id), "rejected", rejection_reason=reason)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return {"status": proposal.status, "id": proposal.id, "reason": reason}


@router.delete("/{proposal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_proposal(proposal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a proposal."""
    proposal = await db.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    await db.delete(proposal)
    await db.commit()
