"""Outreach router - outreach history and tracking."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models import OutreachHistory
from backend.app.services.outreach_service import (
    create_outreach_history,
    get_opportunity,
    get_proposal,
    get_contact,
    list_outreach_history,
    list_pending_followups,
)
from agents.outreach.outreach_agent import OutreachAgent
from agents.base.base_agent import AgentState, AgentStatus

router = APIRouter()


class OutreachResponse(BaseModel):
    id: str
    proposal_id: Optional[str]
    contact_id: Optional[str]
    opportunity_id: Optional[str]
    delivery_status: str
    message_id: Optional[str]
    opened_at: Optional[datetime] = None
    open_count: int
    replied_at: Optional[datetime] = None
    follow_up_scheduled_at: Optional[datetime] = None
    follow_up_sequence_step: int
    outcome: Optional[str] = None


class OutreachSendRequest(BaseModel):
    proposal_id: str
    follow_up_sequence_step: Optional[int] = 1


@router.get("", response_model=list[OutreachResponse])
async def list_outreach(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db)):
    """List outreach history."""
    rows = await list_outreach_history(db, skip=skip, limit=limit)
    return [
        OutreachResponse(
            id=str(r.id),
            proposal_id=str(r.proposal_id) if r.proposal_id else None,
            contact_id=str(r.contact_id) if r.contact_id else None,
            opportunity_id=str(r.opportunity_id) if r.opportunity_id else None,
            delivery_status=r.delivery_status or "pending",
            message_id=r.message_id,
            opened_at=r.opened_at,
            open_count=r.open_count or 0,
            replied_at=r.replied_at,
            follow_up_scheduled_at=r.follow_up_scheduled_at,
            follow_up_sequence_step=r.follow_up_sequence_step or 1,
            outcome=r.outcome,
        )
        for r in rows
    ]


@router.post("/send", response_model=OutreachResponse)
async def send_outreach(request: OutreachSendRequest, db: AsyncSession = Depends(get_db)):
    """Send outreach email for an approved proposal."""
    proposal = await get_proposal(db, request.proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    if proposal.status != "approved":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Proposal must be approved before sending")

    contact = await get_contact(db, str(proposal.contact_id))
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    opportunity = await get_opportunity(db, str(proposal.opportunity_id))
    if not opportunity:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Opportunity not found")

    agent = OutreachAgent()
    state: AgentState = {
        "status": AgentStatus.PENDING,
        "input_data": {
            "proposal": {
                "proposal_id": str(proposal.id),
                "subject": proposal.subject,
                "body": proposal.body,
            },
            "contact": {
                "id": str(contact.id),
                "email": contact.email,
                "first_name": contact.first_name,
                "last_name": contact.last_name,
                "title": contact.title,
            },
            "opportunity_id": str(opportunity.id),
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=result_state.get("error_message", "Outreach send failed"))

    output = result_state.get("output_data", {})
    outreach = await create_outreach_history(
        db,
        proposal_id=str(proposal.id),
        contact_id=str(contact.id),
        opportunity_id=str(opportunity.id),
        message_id=output.get("message_id", ""),
        delivery_status="delivered" if output.get("message_id") else "failed",
        follow_up_sequence_step=request.follow_up_sequence_step or 1,
    )

    return OutreachResponse(
        id=str(outreach.id),
        proposal_id=str(outreach.proposal_id) if outreach.proposal_id else None,
        contact_id=str(outreach.contact_id) if outreach.contact_id else None,
        opportunity_id=str(outreach.opportunity_id) if outreach.opportunity_id else None,
        delivery_status=outreach.delivery_status,
        message_id=outreach.message_id,
        opened_at=outreach.opened_at,
        open_count=outreach.open_count or 0,
        replied_at=outreach.replied_at,
        follow_up_scheduled_at=outreach.follow_up_scheduled_at,
        follow_up_sequence_step=outreach.follow_up_sequence_step or 1,
        outcome=outreach.outcome,
    )


@router.get("/pending-followups", response_model=list[OutreachResponse])
async def get_pending_followups(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db)):
    """Get pending follow-ups."""
    rows = await list_pending_followups(db, skip=skip, limit=limit)
    return [
        OutreachResponse(
            id=str(r.id),
            proposal_id=str(r.proposal_id) if r.proposal_id else None,
            contact_id=str(r.contact_id) if r.contact_id else None,
            opportunity_id=str(r.opportunity_id) if r.opportunity_id else None,
            delivery_status=r.delivery_status or "pending",
            message_id=r.message_id,
            opened_at=r.opened_at,
            open_count=r.open_count or 0,
            replied_at=r.replied_at,
            follow_up_scheduled_at=r.follow_up_scheduled_at,
            follow_up_sequence_step=r.follow_up_sequence_step or 1,
            outcome=r.outcome,
        )
        for r in rows
    ]


@router.get("/track")
async def track_email_open(
    proposal_id: str = Query(...),
    contact_id: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """Track open events for outreach emails."""
    result = await db.execute(
        select(OutreachHistory)
        .where(OutreachHistory.proposal_id == proposal_id)
        .where(OutreachHistory.contact_id == contact_id)
        .limit(1)
    )
    outreach = result.scalars().first()
    if not outreach:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Outreach record not found")

    outreach.open_count = (outreach.open_count or 0) + 1
    outreach.opened_at = datetime.utcnow()
    await db.commit()

    gif = (
        b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;"
    )

    return Response(content=gif, media_type="image/gif")
