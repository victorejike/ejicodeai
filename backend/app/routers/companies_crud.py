"""Companies router with full CRUD operations."""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.schemas import (
    CompanyCreate, CompanyUpdate, Company as CompanySchema,
    PaginatedResponse, ErrorResponse
)
from backend.app.services.crud_service import CompanyService

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post(
    "",
    response_model=CompanySchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new company",
)
async def create_company(
    company_data: CompanyCreate,
    session: AsyncSession = Depends(get_db),
):
    """Create a new company."""
    try:
        # Check if company with same domain already exists
        if company_data.domain:
            existing = await CompanyService.get_by_domain(session, company_data.domain)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Company with domain '{company_data.domain}' already exists",
                )
        
        company = await CompanyService.create(session, company_data)
        return company
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create company: {str(e)}",
        )


@router.get(
    "/{company_id}",
    response_model=CompanySchema,
    summary="Get a company by ID",
)
async def get_company(
    company_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get a specific company by ID."""
    company = await CompanyService.get(session, company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )
    return company


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List all companies",
)
async def list_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    session: AsyncSession = Depends(get_db),
):
    """List all companies with pagination."""
    try:
        companies, total = await CompanyService.list_all(
            session,
            skip=skip,
            limit=limit,
            status=status,
        )
        return PaginatedResponse(
            items=companies,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + limit) < total,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list companies: {str(e)}",
        )


@router.put(
    "/{company_id}",
    response_model=CompanySchema,
    summary="Update a company",
)
async def update_company(
    company_id: int,
    company_data: CompanyUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Update a specific company."""
    company = await CompanyService.update(session, company_id, company_data)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )
    return company


@router.delete(
    "/{company_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a company",
)
async def delete_company(
    company_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a specific company."""
    success = await CompanyService.delete(session, company_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with ID {company_id} not found",
        )
