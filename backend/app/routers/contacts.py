"""Contacts router - CRUD endpoints for contacts."""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from uuid import UUID
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models import Contact

router = APIRouter()


class ContactCreate(BaseModel):
    """Contact creation schema."""
    company_id: UUID
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    title: Optional[str] = None


class ContactResponse(BaseModel):
    """Contact response schema."""
    id: UUID
    email: str
    full_name: Optional[str]
    title: Optional[str]
    is_decision_maker: bool
    email_confidence: str
    status: str


@router.get("", response_model=List[ContactResponse])
async def list_contacts(skip: int = 0, limit: int = 10, db: AsyncSession = Depends(get_db)):
    """List contacts."""
    result = await db.execute(select(Contact).offset(skip).limit(limit))
    return result.scalars().all()


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(contact: ContactCreate, db: AsyncSession = Depends(get_db)):
    """Create contact."""
    new_contact = Contact(
        company_id=contact.company_id,
        email=contact.email,
        first_name=contact.first_name,
        last_name=contact.last_name,
        full_name=f"{contact.first_name or ''} {contact.last_name or ''}".strip(),
        title=contact.title,
    )
    db.add(new_contact)
    await db.commit()
    await db.refresh(new_contact)
    return new_contact


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get contact details."""
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact
