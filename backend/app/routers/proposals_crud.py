"""Proposals router with full CRUD operations."""
from typing import Optional
from fastapi import APIRouter, HTTPException, status, Depends, Query

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.dependencies import get_db
from backend.app.schemas import (
    ProposalCreate, ProposalUpdate, ProposalApprove, Proposal as ProposalSchema,
    PaginatedResponse
)
from backend.app.services.crud_service import ProposalService, OpportunityService, CompanyService, ContactService

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.post(
    "",
    response_model=ProposalSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new proposal",
)
async def create_proposal(
    proposal_data: ProposalCreate,
    session: AsyncSession = Depends(get_db),
):
    """Create a new proposal."""
    try:
        # Validate foreign keys
        if proposal_data.opportunity_id:
            opportunity = await OpportunityService.get(session, proposal_data.opportunity_id)
            if not opportunity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Opportunity with ID {proposal_data.opportunity_id} not found",
                )
        
        if proposal_data.company_id:
            company = await CompanyService.get(session, proposal_data.company_id)
            if not company:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Company with ID {proposal_data.company_id} not found",
                )
        
        if proposal_data.contact_id:
            contact = await ContactService.get(session, proposal_data.contact_id)
            if not contact:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Contact with ID {proposal_data.contact_id} not found",
                )
        
        proposal = await ProposalService.create(session, proposal_data)
        return proposal
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create proposal: {str(e)}",
        )


@router.get(
    "/{proposal_id}",
    response_model=ProposalSchema,
    summary="Get a proposal by ID",
)
async def get_proposal(
    proposal_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Get a specific proposal by ID."""
    proposal = await ProposalService.get(session, proposal_id)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal with ID {proposal_id} not found",
        )
    return proposal


@router.get(
    "",
    response_model=PaginatedResponse,
    summary="List all proposals",
)
async def list_proposals(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    company_id: Optional[int] = None,
    session: AsyncSession = Depends(get_db),
):
    """List all proposals with pagination and filtering."""
    try:
        proposals, total = await ProposalService.list_all(
            session,
            skip=skip,
            limit=limit,
            status=status,
            company_id=company_id,
        )
        return PaginatedResponse(
            items=proposals,
            total=total,
            skip=skip,
            limit=limit,
            has_more=(skip + limit) < total,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list proposals: {str(e)}",
        )


@router.put(
    "/{proposal_id}",
    response_model=ProposalSchema,
    summary="Update a proposal",
)
async def update_proposal(
    proposal_id: int,
    proposal_data: ProposalUpdate,
    session: AsyncSession = Depends(get_db),
):
    """Update a specific proposal."""
    # Validate foreign keys if provided
    if proposal_data.opportunity_id:
        opportunity = await OpportunityService.get(session, proposal_data.opportunity_id)
        if not opportunity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Opportunity with ID {proposal_data.opportunity_id} not found",
            )
    
    if proposal_data.company_id:
        company = await CompanyService.get(session, proposal_data.company_id)
        if not company:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Company with ID {proposal_data.company_id} not found",
            )
    
    if proposal_data.contact_id:
        contact = await ContactService.get(session, proposal_data.contact_id)
        if not contact:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Contact with ID {proposal_data.contact_id} not found",
            )
    
    proposal = await ProposalService.update(session, proposal_id, proposal_data)
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal with ID {proposal_id} not found",
        )
    return proposal


@router.post(
    "/{proposal_id}/approve",
    response_model=ProposalSchema,
    summary="Approve a proposal",
)
async def approve_proposal(
    proposal_id: int,
    approval_data: ProposalApprove,
    session: AsyncSession = Depends(get_db),
):
    """Approve a proposal for sending."""
    proposal = await ProposalService.approve(
        session, 
        proposal_id, 
        approval_data.approved_by
    )
    if not proposal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal with ID {proposal_id} not found",
        )
    return proposal


@router.delete(
    "/{proposal_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a proposal",
)
async def delete_proposal(
    proposal_id: int,
    session: AsyncSession = Depends(get_db),
):
    """Delete a specific proposal."""
    success = await ProposalService.delete(session, proposal_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Proposal with ID {proposal_id} not found",
        )
