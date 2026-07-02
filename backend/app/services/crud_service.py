"""Service layer for database operations."""
from typing import Optional, List
from datetime import datetime
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.models.core import (
    Company, Opportunity, Contact, Proposal, OutreachHistory,
    CompanyResearchReport, AgentRun, SearchConfig,
)
from backend.app.schemas import (
    CompanyCreate, CompanyUpdate,
    OpportunityCreate, OpportunityUpdate,
    ContactCreate, ContactUpdate,
    ProposalCreate, ProposalUpdate,
)


def _to_uuid(value) -> Optional[UUID]:
    if value is None:
        return None
    if isinstance(value, UUID):
        return value
    return UUID(str(value))


# ============================================================================
# Company Service
# ============================================================================

class CompanyService:

    @staticmethod
    async def create(session: AsyncSession, data: CompanyCreate) -> Company:
        db_company = Company(**data.model_dump())
        session.add(db_company)
        await session.commit()
        await session.refresh(db_company)
        return db_company

    @staticmethod
    async def get(session: AsyncSession, company_id) -> Optional[Company]:
        return await session.get(Company, _to_uuid(company_id))

    @staticmethod
    async def get_by_domain(session: AsyncSession, domain: str) -> Optional[Company]:
        result = await session.execute(select(Company).where(Company.domain == domain))
        return result.scalars().first()

    @staticmethod
    async def list_all(
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> tuple[List[Company], int]:
        query = select(Company)
        if status:
            query = query.where(Company.status == status)
        total = await session.scalar(select(func.count()).select_from(query.subquery()))
        result = await session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total or 0

    @staticmethod
    async def update(session: AsyncSession, company_id, data: CompanyUpdate) -> Optional[Company]:
        db_company = await CompanyService.get(session, company_id)
        if not db_company:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(db_company, field, value)
        db_company.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(db_company)
        return db_company

    @staticmethod
    async def delete(session: AsyncSession, company_id) -> bool:
        db_company = await CompanyService.get(session, company_id)
        if not db_company:
            return False
        await session.delete(db_company)
        await session.commit()
        return True


# ============================================================================
# Opportunity Service
# ============================================================================

class OpportunityService:

    @staticmethod
    async def create(session: AsyncSession, data: OpportunityCreate) -> Opportunity:
        db_opp = Opportunity(**data.model_dump())
        session.add(db_opp)
        await session.commit()
        await session.refresh(db_opp)
        return db_opp

    @staticmethod
    async def get(session: AsyncSession, opportunity_id) -> Optional[Opportunity]:
        return await session.get(Opportunity, _to_uuid(opportunity_id))

    @staticmethod
    async def list_all(
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        company_id=None,
        status: Optional[str] = None,
        source: Optional[str] = None,
    ) -> tuple[List[Opportunity], int]:
        query = select(Opportunity)
        conditions = []
        if company_id:
            conditions.append(Opportunity.company_id == _to_uuid(company_id))
        if status:
            conditions.append(Opportunity.status == status)
        if source:
            conditions.append(Opportunity.source_platform == source)
        if conditions:
            query = query.where(and_(*conditions))
        total = await session.scalar(select(func.count()).select_from(query.subquery()))
        result = await session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total or 0

    @staticmethod
    async def update(session: AsyncSession, opportunity_id, data: OpportunityUpdate) -> Optional[Opportunity]:
        db_opp = await OpportunityService.get(session, opportunity_id)
        if not db_opp:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(db_opp, field, value)
        db_opp.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(db_opp)
        return db_opp

    @staticmethod
    async def delete(session: AsyncSession, opportunity_id) -> bool:
        db_opp = await OpportunityService.get(session, opportunity_id)
        if not db_opp:
            return False
        await session.delete(db_opp)
        await session.commit()
        return True


# ============================================================================
# Contact Service
# ============================================================================

class ContactService:

    @staticmethod
    async def create(session: AsyncSession, data: ContactCreate) -> Contact:
        db_contact = Contact(**data.model_dump())
        session.add(db_contact)
        await session.commit()
        await session.refresh(db_contact)
        return db_contact

    @staticmethod
    async def get(session: AsyncSession, contact_id) -> Optional[Contact]:
        return await session.get(Contact, _to_uuid(contact_id))

    @staticmethod
    async def get_by_email(session: AsyncSession, email: str) -> Optional[Contact]:
        result = await session.execute(select(Contact).where(Contact.email == email))
        return result.scalars().first()

    @staticmethod
    async def list_all(
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        company_id=None,
        status: Optional[str] = None,
    ) -> tuple[List[Contact], int]:
        query = select(Contact)
        conditions = []
        if company_id:
            conditions.append(Contact.company_id == _to_uuid(company_id))
        if status:
            conditions.append(Contact.status == status)
        if conditions:
            query = query.where(and_(*conditions))
        total = await session.scalar(select(func.count()).select_from(query.subquery()))
        result = await session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total or 0

    @staticmethod
    async def update(session: AsyncSession, contact_id, data: ContactUpdate) -> Optional[Contact]:
        db_contact = await ContactService.get(session, contact_id)
        if not db_contact:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(db_contact, field, value)
        db_contact.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(db_contact)
        return db_contact

    @staticmethod
    async def delete(session: AsyncSession, contact_id) -> bool:
        db_contact = await ContactService.get(session, contact_id)
        if not db_contact:
            return False
        await session.delete(db_contact)
        await session.commit()
        return True


# ============================================================================
# Proposal Service
# ============================================================================

class ProposalService:

    @staticmethod
    async def create(session: AsyncSession, data: ProposalCreate) -> Proposal:
        db_proposal = Proposal(**data.model_dump())
        session.add(db_proposal)
        await session.commit()
        await session.refresh(db_proposal)
        return db_proposal

    @staticmethod
    async def get(session: AsyncSession, proposal_id) -> Optional[Proposal]:
        return await session.get(Proposal, _to_uuid(proposal_id))

    @staticmethod
    async def list_all(
        session: AsyncSession,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
    ) -> tuple[List[Proposal], int]:
        query = select(Proposal)
        if status:
            query = query.where(Proposal.status == status)
        total = await session.scalar(select(func.count()).select_from(query.subquery()))
        result = await session.execute(query.offset(skip).limit(limit))
        return result.scalars().all(), total or 0

    @staticmethod
    async def update(session: AsyncSession, proposal_id, data: ProposalUpdate) -> Optional[Proposal]:
        db_proposal = await ProposalService.get(session, proposal_id)
        if not db_proposal:
            return None
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(db_proposal, field, value)
        db_proposal.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(db_proposal)
        return db_proposal

    @staticmethod
    async def approve(session: AsyncSession, proposal_id, approved_by: str = "system") -> Optional[Proposal]:
        db_proposal = await ProposalService.get(session, proposal_id)
        if not db_proposal:
            return None
        db_proposal.status = "approved"
        db_proposal.approved_by = approved_by
        db_proposal.approved_at = datetime.utcnow()
        db_proposal.updated_at = datetime.utcnow()
        await session.commit()
        await session.refresh(db_proposal)
        return db_proposal

    @staticmethod
    async def delete(session: AsyncSession, proposal_id) -> bool:
        db_proposal = await ProposalService.get(session, proposal_id)
        if not db_proposal:
            return False
        await session.delete(db_proposal)
        await session.commit()
        return True
