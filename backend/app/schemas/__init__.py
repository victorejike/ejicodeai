"""Pydantic schemas for request/response validation."""
from datetime import datetime
from typing import Optional, List, Dict, Any, Union
from uuid import UUID
from enum import Enum

from pydantic import BaseModel, Field, EmailStr, HttpUrl


# ============================================================================
# Enums
# ============================================================================

class CompanyStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    ARCHIVED = "archived"


class OpportunityStatus(str, Enum):
    DISCOVERED = "discovered"
    CONTACTED = "contacted"
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"
    ARCHIVED = "archived"


class ContactStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    UNSUBSCRIBED = "unsubscribed"


class ProposalStatus(str, Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    SENT = "sent"


class OutreachStatus(str, Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENT = "sent"
    BOUNCED = "bounced"
    OPENED = "opened"
    REPLIED = "replied"


class AgentRunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ============================================================================
# Search Config Schemas
# ============================================================================

class SearchConfigBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    keywords: Optional[List[str]] = Field(None, description="Search keywords")
    platforms: Optional[List[str]] = Field(None, description="Platforms to search")


class SearchConfigCreate(SearchConfigBase):
    pass


class SearchConfigUpdate(BaseModel):
    name: Optional[str] = None
    keywords: Optional[List[str]] = None
    platforms: Optional[List[str]] = None


class SearchConfig(SearchConfigBase):
    id: Union[UUID, str, int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Company Schemas
# ============================================================================

class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    domain: Optional[str] = Field(None, max_length=255)
    website_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = Field(None, max_length=100)
    company_size: Optional[str] = Field(None, max_length=50)
    location: Optional[str] = Field(None, max_length=255)
    fit_score: Optional[float] = Field(None, ge=0, le=100)
    status: CompanyStatus = CompanyStatus.ACTIVE
    linkedin_url: Optional[str] = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    website_url: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    location: Optional[str] = None
    fit_score: Optional[float] = None
    status: Optional[CompanyStatus] = None
    linkedin_url: Optional[str] = None


class Company(CompanyBase):
    id: Union[UUID, str, int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Opportunity Schemas
# ============================================================================

class OpportunityBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    raw_description: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: Optional[str] = Field(None, max_length=100)
    company_id: Optional[Union[UUID, str, int]] = None
    type: Optional[str] = Field(None, max_length=50)
    score: Optional[float] = Field(None, ge=0, le=100)
    status: OpportunityStatus = OpportunityStatus.DISCOVERED


class OpportunityCreate(OpportunityBase):
    pass


class OpportunityUpdate(BaseModel):
    title: Optional[str] = None
    raw_description: Optional[str] = None
    source_url: Optional[str] = None
    source_platform: Optional[str] = None
    company_id: Optional[Union[UUID, str, int]] = None
    type: Optional[str] = None
    score: Optional[float] = None
    status: Optional[OpportunityStatus] = None


class Opportunity(OpportunityBase):
    id: Union[UUID, str, int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Contact Schemas
# ============================================================================

class ContactBase(BaseModel):
    email: EmailStr
    first_name: Optional[str] = Field(None, max_length=100)
    last_name: Optional[str] = Field(None, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)
    title: Optional[str] = Field(None, max_length=255)
    company_id: Optional[Union[UUID, str, int]] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = Field(None, max_length=100)
    status: ContactStatus = ContactStatus.ACTIVE


class ContactCreate(ContactBase):
    pass


class ContactUpdate(BaseModel):
    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    full_name: Optional[str] = None
    title: Optional[str] = None
    company_id: Optional[Union[UUID, str, int]] = None
    linkedin_url: Optional[str] = None
    source: Optional[str] = None
    status: Optional[ContactStatus] = None


class Contact(ContactBase):
    id: Union[UUID, str, int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Company Research Report Schemas
# ============================================================================

class CompanyResearchReportBase(BaseModel):
    company_id: Union[UUID, str, int]
    summary: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    team_size: Optional[str] = Field(None, max_length=50)
    funding_status: Optional[str] = Field(None, max_length=100)
    key_metrics: Optional[Dict[str, Any]] = None
    research_data: Optional[Dict[str, Any]] = None


class CompanyResearchReportCreate(CompanyResearchReportBase):
    pass


class CompanyResearchReportUpdate(BaseModel):
    summary: Optional[str] = None
    tech_stack: Optional[List[str]] = None
    team_size: Optional[str] = None
    funding_status: Optional[str] = None
    key_metrics: Optional[Dict[str, Any]] = None
    research_data: Optional[Dict[str, Any]] = None


class CompanyResearchReport(CompanyResearchReportBase):
    id: Union[UUID, str, int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Proposal Schemas
# ============================================================================

class ProposalBase(BaseModel):
    opportunity_id: Optional[Union[UUID, str, int]] = None
    contact_id: Optional[Union[UUID, str, int]] = None
    subject: str = Field(..., min_length=1, max_length=500)
    body: str = Field(..., min_length=1)
    type: Optional[str] = Field(None, max_length=50)
    tone: Optional[str] = Field(None, max_length=50)
    status: ProposalStatus = ProposalStatus.DRAFT
    approved_by: Optional[str] = None


class ProposalCreate(ProposalBase):
    pass


class ProposalUpdate(BaseModel):
    opportunity_id: Optional[Union[UUID, str, int]] = None
    contact_id: Optional[Union[UUID, str, int]] = None
    subject: Optional[str] = None
    body: Optional[str] = None
    type: Optional[str] = None
    tone: Optional[str] = None
    status: Optional[ProposalStatus] = None


class ProposalApprove(BaseModel):
    approved_by: str = Field(..., description="Username approving the proposal")


class Proposal(ProposalBase):
    id: Union[UUID, str, int]
    approved_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Outreach History Schemas
# ============================================================================

class OutreachHistoryBase(BaseModel):
    proposal_id: Optional[Union[UUID, str, int]] = None
    contact_id: Union[UUID, str, int]
    company_id: Optional[Union[UUID, str, int]] = None
    email_to: EmailStr
    email_from: EmailStr
    subject: str = Field(..., min_length=1, max_length=255)
    body: str = Field(..., min_length=1)
    status: OutreachStatus = OutreachStatus.DRAFT
    sent_at: Optional[datetime] = None
    opened: Optional[bool] = None
    opened_at: Optional[datetime] = None
    replied: Optional[bool] = None
    replied_at: Optional[datetime] = None
    reply_body: Optional[str] = None
    bounce_type: Optional[str] = Field(None, max_length=50)
    metadata_: Optional[Dict[str, Any]] = None


class OutreachHistoryCreate(OutreachHistoryBase):
    pass


class OutreachHistoryUpdate(BaseModel):
    status: Optional[OutreachStatus] = None
    opened: Optional[bool] = None
    opened_at: Optional[datetime] = None
    replied: Optional[bool] = None
    replied_at: Optional[datetime] = None
    reply_body: Optional[str] = None
    bounce_type: Optional[str] = None
    metadata_: Optional[Dict[str, Any]] = None


class OutreachHistory(OutreachHistoryBase):
    id: Union[UUID, str, int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Agent Run Schemas
# ============================================================================

class AgentRunBase(BaseModel):
    run_id: str = Field(..., max_length=255)
    agent_name: str = Field(..., max_length=100)
    status: AgentRunStatus = AgentRunStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    input_data: Optional[Dict[str, Any]] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: int = Field(0, ge=0)
    parent_run_id: Optional[str] = Field(None, max_length=255)
    metadata_: Optional[Dict[str, Any]] = None


class AgentRunCreate(AgentRunBase):
    pass


class AgentRunUpdate(BaseModel):
    status: Optional[AgentRunStatus] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    output_data: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    retry_count: Optional[int] = None
    metadata_: Optional[Dict[str, Any]] = None


class AgentRun(AgentRunBase):
    id: Union[UUID, str, int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ============================================================================
# Pagination and Response Schemas
# ============================================================================

class PaginationParams(BaseModel):
    skip: int = Field(0, ge=0)
    limit: int = Field(10, ge=1, le=100)
    sort_by: Optional[str] = None
    sort_order: str = Field("asc", pattern="^(asc|desc)$")


class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    skip: int
    limit: int
    has_more: bool


class ErrorResponse(BaseModel):
    detail: str
    error_code: Optional[str] = None
    request_id: Optional[str] = None


# ============================================================================
# Dashboard Schemas
# ============================================================================

class DashboardCounts(BaseModel):
    companies: int = 0
    opportunities: int = 0
    contacts: int = 0
    proposals: int = 0
    outreach_history: int = 0
    reports: int = 0
    active_agents: int = 0


class DashboardData(BaseModel):
    status: str = "healthy"
    counts: DashboardCounts
    latest_opportunities: List[Opportunity] = []
    recent_agent_runs: List[AgentRun] = []
    timestamp: datetime = Field(default_factory=datetime.utcnow)