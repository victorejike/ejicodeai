"""Outreach router - outreach history, tracking, rate limiting, and suppression."""
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config import get_settings
from backend.app.dependencies import get_db
from backend.app.models import OutreachHistory, Contact
from backend.app.services.outreach_service import (
    create_outreach_history,
    get_opportunity,
    get_proposal,
    get_contact,
    get_outreach_by_proposal,
    get_daily_outreach_count,
    get_last_outreach_for_contact,
    mark_proposal_as_sent,
    suppress_contact,
    suppress_contact_by_email,
    unsuppress_contact,
    list_suppressed_contacts,
    handle_bounce,
    update_outreach_reply,
    list_outreach_history,
    list_pending_followups,
)
from backend.app.models.core import User
from backend.app.security import get_current_active_user
from agents.outreach.outreach_agent import OutreachAgent
from agents.reply_monitoring.reply_monitoring_agent import ReplyMonitoringAgent
from agents.base.base_agent import AgentState, AgentStatus

router = APIRouter()
settings = get_settings()


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


class UnsubscribeRequest(BaseModel):
    contact_id: Optional[str] = None
    email: Optional[str] = None


class BounceRequest(BaseModel):
    message_id: str
    reason: Optional[str] = "Undeliverable bounce"


class SuppressedContactResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str


@router.get("", response_model=list[OutreachResponse])
async def list_outreach(skip: int = 0, limit: int = 20, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
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
async def send_outreach(request: OutreachSendRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    """Send outreach email for an approved proposal with safety checks and rate limits."""
    proposal = await get_proposal(db, request.proposal_id)
    if not proposal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proposal not found")
    if proposal.status != "approved":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Proposal must be approved before sending. Current status: {proposal.status}",
        )

    # Double-sending prevention
    existing_outreach = await get_outreach_by_proposal(db, request.proposal_id)
    if existing_outreach and existing_outreach.delivery_status in ["delivered", "sent"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Outreach has already been sent for this proposal",
        )

    contact = await get_contact(db, str(proposal.contact_id))
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    # Suppression / unsubscribe check
    if contact.status in ["unsubscribed", "bounced", "invalid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Contact is suppressed/unsubscribed (status: {contact.status})",
        )

    # Daily rate limit check
    daily_count = await get_daily_outreach_count(db)
    if daily_count >= settings.max_emails_per_day:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Daily email limit reached ({settings.max_emails_per_day}/day). Please resume tomorrow.",
        )

    # Per-contact cooldown check
    last_outreach = await get_last_outreach_for_contact(db, str(contact.id))
    if last_outreach and last_outreach.sent_at:
        elapsed_seconds = (datetime.utcnow() - last_outreach.sent_at.replace(tzinfo=None)).total_seconds()
        min_seconds = settings.min_send_interval_minutes * 60
        if elapsed_seconds < min_seconds:
            remaining_minutes = int((min_seconds - elapsed_seconds) / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Contact cooldown active. Please wait {remaining_minutes} minute(s) before sending again.",
            )

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
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result_state.get("error_message", "Outreach send failed"),
        )

    output = result_state.get("output_data", {})
    delivery_status = output.get("delivery_status", "sent")

    outreach = await create_outreach_history(
        db,
        proposal_id=str(proposal.id),
        contact_id=str(contact.id),
        opportunity_id=str(opportunity.id),
        message_id=output.get("message_id", ""),
        delivery_status=delivery_status,
        follow_up_sequence_step=request.follow_up_sequence_step or 1,
    )

    # Transition proposal status to sent
    await mark_proposal_as_sent(db, str(proposal.id))

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
async def get_pending_followups(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
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


@router.get("/unsubscribe", response_class=HTMLResponse)
async def unsubscribe_get(
    contact_id: Optional[str] = Query(None),
    email: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Public unsubscribe link endpoint displaying confirmation HTML."""
    contact = None
    if contact_id:
        contact = await suppress_contact(db, contact_id)
    elif email:
        contact = await suppress_contact_by_email(db, email)

    email_display = contact.email if contact else (email or "your address")
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Unsubscribed - Ejicode AI</title>
        <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; background-color: #f8fafc; color: #1e293b; }}
            .card {{ background: white; padding: 2.5rem; border-radius: 12px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); max-width: 440px; text-align: center; }}
            h2 {{ color: #0f172a; margin-top: 0; }}
            p {{ color: #64748b; line-height: 1.6; font-size: 15px; }}
            .badge {{ display: inline-block; background: #ecfdf5; color: #059669; padding: 6px 14px; border-radius: 9999px; font-size: 13px; font-weight: 600; margin-bottom: 1rem; }}
        </style>
    </head>
    <body>
        <div class="card">
            <div class="badge">Unsubscribed</div>
            <h2>Preferences Updated</h2>
            <p><strong>{email_display}</strong> has been unsubscribed from all future communications.</p>
            <p style="font-size: 13px;">If this was a mistake, you can contact us to reactivate notifications.</p>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@router.post("/unsubscribe")
async def unsubscribe_post(request: UnsubscribeRequest, db: AsyncSession = Depends(get_db)):
    """API endpoint to unsubscribe / suppress a contact."""
    contact = None
    if request.contact_id:
        contact = await suppress_contact(db, request.contact_id)
    elif request.email:
        contact = await suppress_contact_by_email(db, request.email)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either contact_id or email is required")

    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    return {"status": "unsubscribed", "contact_id": str(contact.id), "email": contact.email}


@router.get("/suppression", response_model=List[SuppressedContactResponse])
async def list_suppression(skip: int = 0, limit: int = 50, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    """List all suppressed contacts."""
    contacts = await list_suppressed_contacts(db, skip=skip, limit=limit)
    return [
        SuppressedContactResponse(
            id=str(c.id),
            email=c.email,
            first_name=c.first_name,
            last_name=c.last_name,
            status=c.status,
        )
        for c in contacts
    ]


@router.delete("/suppression/{contact_id}")
async def remove_suppression(contact_id: str, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    """Reactivate a suppressed contact."""
    contact = await unsuppress_contact(db, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return {"status": "active", "contact_id": str(contact.id)}


@router.post("/bounce")
async def record_bounce(request: BounceRequest, db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    """Record an email bounce event."""
    outreach = await handle_bounce(db, request.message_id, request.reason or "Bounced")
    if not outreach:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message ID not found in outreach history")
    return {"status": "bounced", "message_id": request.message_id, "outreach_id": str(outreach.id)}


@router.post("/poll-replies")
async def trigger_reply_polling(db: AsyncSession = Depends(get_db), user: User = Depends(get_current_active_user)):
    """Trigger reply monitoring check and update outreach records."""
    agent = ReplyMonitoringAgent()
    state: AgentState = {
        "status": AgentStatus.PENDING,
        "input_data": {},
        "output_data": {},
        "messages": [],
        "current_step": "initialization",
        "steps_completed": [],
        "error_count": 0,
        "confidence_score": 1.0,
        "quality_checks_passed": True,
    }
    result_state = await agent.process(state)
    replies = result_state.get("output_data", {}).get("replies", [])

    matched = 0
    for reply in replies:
        in_reply_to = reply.get("in_reply_to") or reply.get("references")
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
            matched += 1

    return {
        "total_polled": len(replies),
        "matched_outreach": matched,
        "status": result_state.get("status"),
    }

