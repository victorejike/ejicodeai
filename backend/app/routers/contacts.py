"""Contacts router - full CRUD and decision maker management."""
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.models.core import Company, Contact

router = APIRouter()


class ContactCreate(BaseModel):
    company_id: UUID
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    role_category: Optional[str] = None
    is_decision_maker: Optional[bool] = False
    linkedin_url: Optional[str] = None
    email_confidence: Optional[str] = "unverified"
    source: Optional[str] = "manual"
    notes: Optional[str] = None
    status: Optional[str] = "active"


class ContactUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    role_category: Optional[str] = None
    is_decision_maker: Optional[bool] = None
    linkedin_url: Optional[str] = None
    email_confidence: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class ContactResponse(BaseModel):
    id: UUID
    company_id: Optional[UUID] = None
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    role_category: Optional[str] = None
    is_decision_maker: bool = False
    linkedin_url: Optional[str] = None
    email_confidence: str = "unverified"
    source: Optional[str] = None
    notes: Optional[str] = None
    status: str = "active"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


@router.get("", response_model=List[ContactResponse])
async def list_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    company_id: Optional[UUID] = None,
    is_decision_maker: Optional[bool] = None,
    role_category: Optional[str] = None,
    status: Optional[str] = None,
    email_confidence: Optional[str] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List contacts with filters and search."""
    query = select(Contact)

    if company_id:
        query = query.where(Contact.company_id == company_id)
    if is_decision_maker is not None:
        query = query.where(Contact.is_decision_maker == is_decision_maker)
    if role_category:
        query = query.where(Contact.role_category == role_category)
    if status:
        query = query.where(Contact.status == status)
    if email_confidence:
        query = query.where(Contact.email_confidence == email_confidence)
    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Contact.email.ilike(search_pattern))
            | (Contact.full_name.ilike(search_pattern))
            | (Contact.title.ilike(search_pattern))
        )

    query = query.order_by(desc(Contact.created_at)).offset(skip).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
async def create_contact(contact: ContactCreate, db: AsyncSession = Depends(get_db)):
    """Create a contact."""
    company = await db.get(Company, contact.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Linked company not found")

    full_name = contact.full_name or f"{contact.first_name or ''} {contact.last_name or ''}".strip() or contact.email

    new_contact = Contact(
        company_id=contact.company_id,
        email=contact.email,
        first_name=contact.first_name,
        last_name=contact.last_name,
        full_name=full_name,
        title=contact.title,
        role_category=contact.role_category,
        is_decision_maker=contact.is_decision_maker or False,
        linkedin_url=contact.linkedin_url,
        email_confidence=contact.email_confidence or "unverified",
        source=contact.source or "manual",
        notes=contact.notes,
        status=contact.status or "active",
    )
    db.add(new_contact)
    await db.commit()
    await db.refresh(new_contact)
    return new_contact


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(contact_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get contact details by ID."""
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return contact


@router.patch("/{contact_id}", response_model=ContactResponse)
async def update_contact(
    contact_id: UUID,
    data: ContactUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update contact attributes."""
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(contact, field, value)

    if data.first_name or data.last_name:
        contact.full_name = f"{contact.first_name or ''} {contact.last_name or ''}".strip()

    await db.commit()
    await db.refresh(contact)
    return contact


@router.delete("/{contact_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_contact(contact_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete a contact."""
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    await db.delete(contact)
    await db.commit()
