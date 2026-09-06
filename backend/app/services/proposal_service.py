from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models import Opportunity, Contact, Company, Proposal


def _to_uuid(value: Optional[str]) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


async def get_opportunity(session: AsyncSession, opportunity_id: str) -> Optional[Opportunity]:
    return await session.get(Opportunity, _to_uuid(opportunity_id))


async def get_contact(session: AsyncSession, contact_id: str) -> Optional[Contact]:
    return await session.get(Contact, _to_uuid(contact_id))


async def get_company(session: AsyncSession, company_id: str) -> Optional[Company]:
    return await session.get(Company, _to_uuid(company_id))


async def get_proposal(session: AsyncSession, proposal_id: str) -> Optional[Proposal]:
    return await session.get(Proposal, _to_uuid(proposal_id))


async def create_proposal(
    session: AsyncSession,
    opportunity_id: str,
    contact_id: str,
    proposal_type: str,
    tone: str,
    subject: str,
    body: str,
    word_count: int,
    generation_model: str = "manual",
    generation_prompt: Optional[str] = None,
    rag_context: Optional[dict] = None,
    initial_status: str = "draft",
) -> Proposal:
    proposal = Proposal(
        opportunity_id=_to_uuid(opportunity_id),
        contact_id=_to_uuid(contact_id),
        type=proposal_type,
        tone=tone,
        subject=subject,
        body=body,
        word_count=word_count,
        generation_model=generation_model,
        generation_prompt=generation_prompt,
        rag_context=rag_context,
        status=initial_status,
    )
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)
    return proposal


async def update_proposal_status(
    session: AsyncSession,
    proposal_id: str,
    status: str,
    approved_by: Optional[str] = None,
    rejection_reason: Optional[str] = None,
) -> Optional[Proposal]:
    proposal = await get_proposal(session, proposal_id)
    if not proposal:
        return None
    proposal.status = status
    if approved_by:
        proposal.approved_by = approved_by
        proposal.approved_at = datetime.utcnow()
    if rejection_reason:
        proposal.rejection_reason = rejection_reason
    await session.commit()
    await session.refresh(proposal)
    return proposal
