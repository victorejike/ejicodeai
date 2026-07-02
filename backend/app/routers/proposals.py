"""Proposals router - proposal generation and management."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models import Proposal
from backend.app.services.proposal_service import (
    get_opportunity,
    get_contact,
    get_company,
    create_proposal,
    update_proposal_status,
)
from agents.base.base_agent import AgentStatus
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent

router = APIRouter()


class ProposalListResponse(BaseModel):
    id: UUID
    status: str
    subject: Optional[str]
    type: Optional[str]
    tone: Optional[str]
    word_count: Optional[int]
    opportunity_id: Optional[UUID]
    contact_id: Optional[UUID]


class ProposalResponse(BaseModel):
    """Proposal response."""
    id: UUID
    status: str
    subject: Optional[str]
    body: Optional[str]


class ProposalGenerateRequest(BaseModel):
    """Proposal generation request."""
    opportunity_id: UUID
    contact_id: UUID
    type: str = "cold_email"
    tone: str = "professional"


@router.get("", response_model=List[ProposalListResponse])
async def list_proposals(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List proposals with optional status filter."""
    query = select(Proposal)
    if status:
        query = query.where(Proposal.status == status)
    result = await db.execute(query.order_by(Proposal.created_at.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/{proposal_id}", response_model=ProposalResponse)
async def get_proposal_by_id(proposal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get proposal by ID."""
    proposal = await db.get(Proposal, proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return proposal


@router.post("/generate", response_model=ProposalResponse)
async def generate_proposal(
    request: ProposalGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Generate proposal using AI."""
    opportunity = await get_opportunity(db, str(request.opportunity_id))
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    contact = await get_contact(db, str(request.contact_id))
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    company = await get_company(db, str(opportunity.company_id))
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company metadata not found")

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
                "tech_required": opportunity.tech_required,
            },
            "contact_data": {
                "id": str(contact.id),
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "title": contact.title,
            },
            "company_data": {
                "id": str(company.id),
                "name": company.name,
                "domain": company.domain,
                "industry": company.industry,
                "description": company.description,
                "tech_stack": company.tech_stack,
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result_state.get("error_message", "Proposal generation failed"))

    output = result_state.get("output_data", {})
    proposal = await create_proposal(
        db,
        opportunity_id=str(request.opportunity_id),
        contact_id=str(request.contact_id),
        proposal_type=request.type,
        tone=request.tone,
        subject=output.get("subject", "Opportunity from Ejicode"),
        body=output.get("body", ""),
        word_count=output.get("word_count", 0),
        generation_model=output.get("generation_model", ""),
        generation_prompt=output.get("generation_prompt", ""),
        rag_context={"items": output.get("rag_context", [])},
    )

    return ProposalResponse(
        id=proposal.id,
        status=proposal.status,
        subject=proposal.subject,
        body=proposal.body,
    )


@router.patch("/{proposal_id}/approve")
async def approve_proposal(proposal_id: UUID, db: AsyncSession = Depends(get_db)):
    """Approve proposal for sending."""
    proposal = await update_proposal_status(db, str(proposal_id), "approved", approved_by="system")
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return {"status": proposal.status, "id": proposal.id}


@router.patch("/{proposal_id}/reject")
async def reject_proposal(proposal_id: UUID, reason: str, db: AsyncSession = Depends(get_db)):
    """Reject proposal."""
    proposal = await update_proposal_status(db, str(proposal_id), "rejected", rejection_reason=reason)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    return {"status": proposal.status, "id": proposal.id}
