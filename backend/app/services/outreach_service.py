from datetime import datetime, timedelta
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, func, desc, or_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models import OutreachHistory, Proposal, Contact, Opportunity


def _to_uuid(value: Optional[str]) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    try:
        return UUID(str(value))
    except (ValueError, TypeError):
        return None


async def create_outreach_history(
    session: AsyncSession,
    proposal_id: str,
    contact_id: str,
    opportunity_id: str,
    message_id: str,
    delivery_status: str = "pending",
    follow_up_sequence_step: int = 1,
) -> OutreachHistory:
    outreach = OutreachHistory(
        proposal_id=_to_uuid(proposal_id),
        contact_id=_to_uuid(contact_id),
        opportunity_id=_to_uuid(opportunity_id),
        sent_at=datetime.utcnow(),
        delivery_status=delivery_status,
        message_id=message_id,
        follow_up_sequence_step=follow_up_sequence_step,
    )
    session.add(outreach)
    await session.commit()
    await session.refresh(outreach)
    return outreach


async def get_outreach_history(session: AsyncSession, outreach_id: str) -> Optional[OutreachHistory]:
    uid = _to_uuid(outreach_id)
    if not uid:
        return None
    return await session.get(OutreachHistory, uid)


async def get_proposal(session: AsyncSession, proposal_id: str) -> Optional[Proposal]:
    uid = _to_uuid(proposal_id)
    if not uid:
        return None
    return await session.get(Proposal, uid)


async def get_contact(session: AsyncSession, contact_id: str) -> Optional[Contact]:
    uid = _to_uuid(contact_id)
    if not uid:
        return None
    return await session.get(Contact, uid)


async def get_opportunity(session: AsyncSession, opportunity_id: str) -> Optional[Opportunity]:
    uid = _to_uuid(opportunity_id)
    if not uid:
        return None
    return await session.get(Opportunity, uid)


async def get_outreach_by_proposal(session: AsyncSession, proposal_id: str) -> Optional[OutreachHistory]:
    pid = _to_uuid(proposal_id)
    if not pid:
        return None
    result = await session.execute(
        select(OutreachHistory).where(OutreachHistory.proposal_id == pid).limit(1)
    )
    return result.scalars().first()


async def list_outreach_history(session: AsyncSession, skip: int = 0, limit: int = 20):
    result = await session.execute(
        select(OutreachHistory).order_by(desc(OutreachHistory.created_at)).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def get_outreach_by_message_id(session: AsyncSession, message_id: str) -> Optional[OutreachHistory]:
    clean_id = message_id.strip().strip("<>").strip()
    result = await session.execute(
        select(OutreachHistory).where(
            or_(
                OutreachHistory.message_id == message_id,
                OutreachHistory.message_id == clean_id,
                OutreachHistory.message_id == f"<{clean_id}>",
            )
        ).limit(1)
    )
    return result.scalars().first()


async def get_daily_outreach_count(session: AsyncSession) -> int:
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    result = await session.execute(
        select(func.count(OutreachHistory.id)).where(OutreachHistory.sent_at >= today_start)
    )
    return result.scalar() or 0


async def get_last_outreach_for_contact(session: AsyncSession, contact_id: str) -> Optional[OutreachHistory]:
    cid = _to_uuid(contact_id)
    if not cid:
        return None
    result = await session.execute(
        select(OutreachHistory)
        .where(OutreachHistory.contact_id == cid)
        .order_by(desc(OutreachHistory.sent_at))
        .limit(1)
    )
    return result.scalars().first()


async def mark_proposal_as_sent(session: AsyncSession, proposal_id: str) -> Optional[Proposal]:
    proposal = await get_proposal(session, proposal_id)
    if proposal:
        proposal.status = "sent"
        await session.commit()
        await session.refresh(proposal)
    return proposal


async def suppress_contact(session: AsyncSession, contact_id: str) -> Optional[Contact]:
    contact = await get_contact(session, contact_id)
    if contact:
        contact.status = "unsubscribed"
        await session.commit()
        await session.refresh(contact)
    return contact


async def suppress_contact_by_email(session: AsyncSession, email: str) -> Optional[Contact]:
    result = await session.execute(
        select(Contact).where(func.lower(Contact.email) == email.strip().lower()).limit(1)
    )
    contact = result.scalars().first()
    if contact:
        contact.status = "unsubscribed"
        await session.commit()
        await session.refresh(contact)
    return contact


async def unsuppress_contact(session: AsyncSession, contact_id: str) -> Optional[Contact]:
    contact = await get_contact(session, contact_id)
    if contact:
        contact.status = "active"
        await session.commit()
        await session.refresh(contact)
    return contact


async def list_suppressed_contacts(session: AsyncSession, skip: int = 0, limit: int = 50) -> List[Contact]:
    result = await session.execute(
        select(Contact).where(Contact.status == "unsubscribed").offset(skip).limit(limit)
    )
    return result.scalars().all()


async def handle_bounce(session: AsyncSession, message_id: str, reason: str = "Bounced", bounce_reason: Optional[str] = None) -> Optional[OutreachHistory]:
    effective_reason = bounce_reason or reason
    outreach = await get_outreach_by_message_id(session, message_id)
    if not outreach:
        return None
    outreach.delivery_status = "bounced"
    outreach.outcome = f"Bounced: {effective_reason}"
    if outreach.contact_id:
        contact = await session.get(Contact, outreach.contact_id)
        if contact:
            contact.status = "bounced"
    await session.commit()
    await session.refresh(outreach)
    return outreach


async def update_outreach_reply(
    session: AsyncSession,
    message_id: str,
    reply_content: str,
    reply_classification: str,
    replied_at: Optional[str] = None,
    outcome: Optional[str] = None,
) -> Optional[OutreachHistory]:
    outreach = await get_outreach_by_message_id(session, message_id)
    if not outreach:
        return None

    outreach.replied_at = datetime.fromisoformat(replied_at) if replied_at else datetime.utcnow()
    outreach.reply_content = reply_content
    outreach.reply_classification = reply_classification
    outreach.delivery_status = "replied"
    outreach.outcome = outcome or reply_classification

    # Automatic suppression if reply is unsubscribe or negative request
    if reply_classification in ["UNSUBSCRIBE", "NOT_INTERESTED"]:
        if outreach.contact_id:
            contact = await session.get(Contact, outreach.contact_id)
            if contact and reply_classification == "UNSUBSCRIBE":
                contact.status = "unsubscribed"

    await session.commit()
    await session.refresh(outreach)
    return outreach


async def list_pending_followups(session: AsyncSession, skip: int = 0, limit: int = 50):
    result = await session.execute(
        select(OutreachHistory)
        .where(OutreachHistory.replied_at == None)
        .where(OutreachHistory.delivery_status.in_(["pending", "delivered", "sent"]))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

