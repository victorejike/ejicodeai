"""Contacts router with full CRUD operations."""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.schemas import (
    ContactCreate, ContactUpdate, Contact as ContactSchema,
    PaginatedResponse
)
from backend.app.services.crud_service import ContactService, CompanyService

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.post(
    "",
    response_model=ContactSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new contact",
)
async def create_contact(
    contact_data: ContactCreate,
    session: AsyncSession = Depends(get_db),
):
    """Create a new contact."""
    try:
        # Check if contact with same email already exists
        existing = await ContactService.get_by_email(session, contact_data.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Contact with email '{contact_data.email}' already exists",
            )
        
        # Validate company_id if provided
        if contact_data.company_id:
            company = await CompanyService.get(session, contact_data.company_id)
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Company with ID {contact_data.company_id} not found",
                )
        
        contact = await ContactService.create(session, contact_data)
        return contact
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create contact: {str(e)}",
        )


@router.get(
    "/{contact_id}",
    response_model=ContactSchema,
    summary="Get a contact by ID",
)
async def get_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get a specific contact by ID."""
    contact = await ContactService.get(session, contact_id)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found",
        )
    return contact


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List all contacts",
)
async def list_contacts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    company_id: Optional[int] = None,
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """List all contacts with pagination and filtering."""
    try:
        contacts, total = await ContactService.list_all(
            session,
            skip=skip,
            limit=limit,
            company_id=company_id,
            status=status,
        )
        return PaginatedResponse(
            items=contacts,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + limit) < total,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list contacts: {str(e)}",
        )


@router.put(
    "/{contact_id}",
    response_model=ContactSchema,
    summary="Update a contact",
)
async def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Update a specific contact."""
    # Validate company_id if provided
    if contact_data.company_id:
        company = await CompanyService.get(session, contact_data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Company with ID {contact_data.company_id} not found",
            )
    
    contact = await ContactService.update(session, contact_id, contact_data)
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found",
        )
    return contact


@router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a contact",
)
async def delete_contact(
    contact_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a specific contact."""
    success = await ContactService.delete(session, contact_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with ID {contact_id} not found",
        )
