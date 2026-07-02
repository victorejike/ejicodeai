"""Opportunities router with full CRUD operations."""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.schemas import (
    OpportunityCreate, OpportunityUpdate, Opportunity as OpportunitySchema,
    PaginatedResponse
)
from backend.app.services.crud_service import OpportunityService, CompanyService

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


@router.post(
    "",
    response_model=OpportunitySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new opportunity",
)
async def create_opportunity(
    opportunity_data: OpportunityCreate,
    session: AsyncSession = Depends(get_db),
):
    """Create a new opportunity."""
    try:
        # Validate company_id if provided
        if opportunity_data.company_id:
            company = await CompanyService.get(session, opportunity_data.company_id)
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Company with ID {opportunity_data.company_id} not found",
                )
        
        opportunity = await OpportunityService.create(session, opportunity_data)
        return opportunity
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create opportunity: {str(e)}",
        )


@router.get(
    "/{opportunity_id}",
    response_model=OpportunitySchema,
    summary="Get an opportunity by ID",
)
async def get_opportunity(
    opportunity_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get a specific opportunity by ID."""
    opportunity = await OpportunityService.get(session, opportunity_id)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity with ID {opportunity_id} not found",
        )
    return opportunity


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List all opportunities",
)
async def list_opportunities(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    company_id: Optional[int] = None,
    status: Optional[str] = None,
    source: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """List all opportunities with pagination and filtering."""
    try:
        opportunities, total = await OpportunityService.list_all(
            session,
            skip=skip,
            limit=limit,
            company_id=company_id,
            status=status,
            source=source,
        )
        return PaginatedResponse(
            items=opportunities,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + limit) < total,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list opportunities: {str(e)}",
        )


@router.put(
    "/{opportunity_id}",
    response_model=OpportunitySchema,
    summary="Update an opportunity",
)
async def update_opportunity(
    opportunity_id: int,
    opportunity_data: OpportunityUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Update a specific opportunity."""
    # Validate company_id if provided
    if opportunity_data.company_id:
        company = await CompanyService.get(session, opportunity_data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Company with ID {opportunity_data.company_id} not found",
            )
    
    opportunity = await OpportunityService.update(session, opportunity_id, opportunity_data)
    if not opportunity:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity with ID {opportunity_id} not found",
        )
    return opportunity


@router.delete(
    "/{opportunity_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an opportunity",
)
async def delete_opportunity(
    opportunity_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a specific opportunity."""
    success = await OpportunityService.delete(session, opportunity_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Opportunity with ID {opportunity_id} not found",
        )
