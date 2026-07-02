from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models import OutreachHistory, Proposal, Contact, Opportunity


def _to_uuid(value: Optional[str]) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


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
    return await session.get(OutreachHistory, _to_uuid(outreach_id))


async def get_proposal(session: AsyncSession, proposal_id: str) -> Optional[Proposal]:
    return await session.get(Proposal, _to_uuid(proposal_id))


async def get_contact(session: AsyncSession, contact_id: str) -> Optional[Contact]:
    return await session.get(Contact, _to_uuid(contact_id))


async def get_opportunity(session: AsyncSession, opportunity_id: str) -> Optional[Opportunity]:
    return await session.get(Opportunity, _to_uuid(opportunity_id))


async def list_outreach_history(session: AsyncSession, skip: int = 0, limit: int = 20):
    result = await session.execute(
        select(OutreachHistory).offset(skip).limit(limit)
    )
    return result.scalars().all()


async def get_outreach_by_message_id(session: AsyncSession, message_id: str) -> Optional[OutreachHistory]:
    result = await session.execute(
        select(OutreachHistory).where(OutreachHistory.message_id == message_id).limit(1)
    )
    return result.scalars().first()


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
    await session.commit()
    await session.refresh(outreach)
    return outreach


async def list_pending_followups(session: AsyncSession, skip: int = 0, limit: int = 50):
    result = await session.execute(
        select(OutreachHistory)
        .where(OutreachHistory.replied_at == None)
        .where(OutreachHistory.delivery_status.in_(["pending", "delivered"]))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
