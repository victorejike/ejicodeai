"""Canonical SQLAlchemy ORM models for the backend supporting Individual and Enterprise platforms."""
from datetime import datetime
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.types import TypeDecorator, String as SAString
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship


class GUID(TypeDecorator):
    """Platform-independent UUID type. Uses PG UUID on PostgreSQL, String(36) on SQLite."""
    impl = SAString(36)
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            return dialect.type_descriptor(PG_UUID())
        return dialect.type_descriptor(SAString(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if not isinstance(value, uuid.UUID):
            return uuid.UUID(str(value))
        return value


from backend.app.database import Base


class Organization(Base):
    """Multi-tenant organization entity for enterprise recruitment & BDP."""

    __tablename__ = "organizations"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    domain = Column(String(255))
    plan = Column(String(50), default="pro")  # free, pro, enterprise
    billing_email = Column(String(255))
    settings = Column(JSON, default=dict)
    status = Column(String(50), default="active")  # active, suspended, trial
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def plan_tier(self) -> str:
        return self.plan or "pro"

    members = relationship("OrganizationMember", back_populates="organization", cascade="all, delete-orphan")
    candidates = relationship("Candidate", back_populates="organization", cascade="all, delete-orphan")


class OrganizationMember(Base):
    """Membership linking users to organizations with role-based permissions."""

    __tablename__ = "organization_members"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), default="member")  # owner, admin, recruiter, member
    permissions = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="members")
    user = relationship("User", back_populates="memberships")


class Document(Base):
    """Raw uploaded document (CV, resume, certificate, etc.)."""

    __tablename__ = "documents"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    filename = Column(String(255), nullable=False)
    file_type = Column(String(50), nullable=False)  # pdf, docx, txt
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256
    file_size = Column(Integer, default=0)
    storage_path = Column(Text)
    raw_text = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    extractions = relationship("CVExtraction", back_populates="document", cascade="all, delete-orphan")


class CVExtraction(Base):
    """Extracted intelligence from an uploaded CV with strict truthfulness & confidence scores."""

    __tablename__ = "cv_extractions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    document_id = Column(GUID(), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    extracted_skills = Column(JSON, default=list)  # [{"name": "...", "confidence": 0.95, "source": "..."}]
    extracted_experience = Column(JSON, default=list)  # [{"title": "...", "company": "...", "years": 2.5}]
    extracted_education = Column(JSON, default=list)
    extracted_certifications = Column(JSON, default=list)
    extracted_projects = Column(JSON, default=list)
    contact_info = Column(JSON, default=dict)
    raw_sections = Column(JSON, default=dict)
    confidence_score = Column(Float, default=0.0)
    extraction_metadata = Column(JSON, default=dict)
    status = Column(String(50), default="completed")  # completed, partial, failed
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    document = relationship("Document", back_populates="extractions")


class UserProfile(Base):
    """Detailed candidate profile for Individual users."""

    __tablename__ = "user_profiles"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    full_name = Column(String(255))
    title = Column(String(255))  # Headline / Target Role
    bio = Column(Text)
    skills = Column(JSON, default=list)  # ["Python", "FastAPI", "React", ...]
    experience_years = Column(Float, default=0.0)
    experience = Column(JSON, default=list)  # list of previous jobs/projects
    education = Column(JSON, default=list)  # list of degrees/institutions
    portfolio_url = Column(Text)
    github_url = Column(Text)
    linkedin_url = Column(Text)
    resume_url = Column(Text)
    avatar_url = Column(Text)
    certifications = Column(JSON, default=list)
    location = Column(String(255))
    preferred_locations = Column(JSON, default=list)
    remote_preference = Column(String(50), default="remote")  # remote, hybrid, onsite, any
    job_types = Column(JSON, default=lambda: ["contract", "full-time"])  # full-time, contract, freelance
    salary_min = Column(Float)
    salary_max = Column(Float)
    salary_currency = Column(String(10), default="USD")
    technologies = Column(JSON, default=list)
    projects = Column(JSON, default=list)
    preferred_industries = Column(JSON, default=list)
    preferred_companies = Column(JSON, default=list)
    availability = Column(String(100), default="Immediately")
    professional_strengths = Column(JSON, default=list)
    continuous_search_active = Column(Boolean, default=True)
    search_frequency = Column(String(50), default="daily")
    marketing_materials = Column(JSON, default=dict)
    career_goals = Column(Text)
    ai_candidate_summary = Column(JSON, default=dict)  # Generated by ProfileAnalyzerAgent
    visibility = Column(String(50), default="private")  # private, anonymous_discoverable, public_discoverable
    cv_document_id = Column(GUID(), ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="profile")
    cv_document = relationship("Document", foreign_keys=[cv_document_id])


class Candidate(Base):
    """Discovered candidate in Enterprise talent pipeline."""

    __tablename__ = "candidates"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), index=True)
    phone = Column(String(50))
    title = Column(String(255))
    skills = Column(JSON, default=list)
    experience_summary = Column(Text)
    location = Column(String(255))
    github_url = Column(Text)
    linkedin_url = Column(Text)
    portfolio_url = Column(Text)
    resume_text = Column(Text)
    status = Column(String(50), default="discovered")  # discovered, screening, interviewing, offered, rejected, hired
    match_score = Column(Integer, default=0)
    match_explanation = Column(Text)
    source = Column(String(100), default="ai_scout")  # ai_scout, github, linkedin, applicant
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    organization = relationship("Organization", back_populates="candidates")


class Company(Base):
    """Company model."""

    __tablename__ = "companies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True)
    website_url = Column(Text)
    linkedin_url = Column(Text)
    github_org = Column(Text)
    industry = Column(String(100))
    company_size = Column(String(50))
    funding_stage = Column(String(50))
    location = Column(String(255))
    description = Column(Text)
    tech_stack = Column(JSON, default=list)
    pain_points = Column(JSON, default=list)
    fit_score = Column(Integer, default=0)
    fit_reasoning = Column(Text)
    status = Column(String(50), default="discovered")
    last_researched = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    contacts = relationship("Contact", back_populates="company", cascade="all, delete-orphan")
    opportunities = relationship("Opportunity", back_populates="company")
    research_reports = relationship("CompanyResearchReport", back_populates="company")


class Contact(Base):
    """Contact model."""

    __tablename__ = "contacts"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    company_id = Column(GUID(), ForeignKey("companies.id", ondelete="CASCADE"))
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    full_name = Column(String(255))
    email = Column(String(255))
    email_confidence = Column(String(20), default="unverified")
    linkedin_url = Column(Text)
    title = Column(String(255))
    role_category = Column(String(100))
    is_decision_maker = Column(Boolean, default=False)
    source = Column(String(100))
    notes = Column(Text)
    status = Column(String(50), default="active")
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="contacts")


class Opportunity(Base):
    """Opportunity model.

    Scoping note: an opportunity row is *one user's view* of a posting - it
    carries that user's match score and breakdown. Two candidates who both find
    the same job each need their own row, so uniqueness is (user_id, source_url)
    rather than source_url alone. Rows with a NULL user_id belong to the shared
    business-development pipeline.
    """

    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint("user_id", "source_url", name="uq_opportunity_user_source_url"),
        Index("ix_opportunities_source_url", "source_url"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    company_id = Column(GUID(), ForeignKey("companies.id"))
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(500), nullable=False)
    type = Column(String(50), nullable=False)
    pipeline_type = Column(String(50), default="employment")  # employment | freelance
    source_platform = Column(String(100))
    source_url = Column(Text)
    all_sources = Column(JSON, default=list)  # [{"source": ..., "url": ...}]
    raw_description = Column(Text)
    parsed_data = Column(JSON)
    location_type = Column(String(50))
    location = Column(String(255))
    salary_min = Column(Float)
    salary_max = Column(Float)
    salary_currency = Column(String(10), default="USD")
    tech_required = Column(JSON, default=list)
    score = Column(Integer, default=0)
    score_breakdown = Column(JSON)
    quality_score = Column(Integer)
    source_reliability_score = Column(Integer)
    safety_status = Column(String(50))  # SAFE, REVIEW, HIGH RISK, REJECTED
    # Null until ValidationAgent has actually verified the posting. Never
    # pre-filled with an optimistic number - an unverified job must not look
    # verified to the user.
    verification_confidence = Column(Integer)
    freshness_status = Column(String(50))  # OPEN, RECENT, AGING, EXPIRED, REMOVED, UNKNOWN
    rank = Column(Integer)
    status = Column(String(50), default="new")
    posted_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    discovered_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    company = relationship("Company", back_populates="opportunities")


class Proposal(Base):
    """Proposal model."""

    __tablename__ = "proposals"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    opportunity_id = Column(GUID(), ForeignKey("opportunities.id"))
    contact_id = Column(GUID(), ForeignKey("contacts.id"))
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(50))
    subject = Column(Text)
    body = Column(Text, nullable=False)
    tone = Column(String(50), default="professional")
    word_count = Column(Integer)
    generation_model = Column(String(100))
    generation_prompt = Column(Text)
    rag_context = Column(JSON)
    status = Column(String(50), default="draft")
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))
    rejection_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class OutreachHistory(Base):
    """Outreach history model."""

    __tablename__ = "outreach_history"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    proposal_id = Column(GUID(), ForeignKey("proposals.id"))
    contact_id = Column(GUID(), ForeignKey("contacts.id"))
    opportunity_id = Column(GUID(), ForeignKey("opportunities.id"))
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    sent_at = Column(DateTime(timezone=True))
    delivery_status = Column(String(50), default="pending")
    message_id = Column(String(255))
    opened_at = Column(DateTime(timezone=True))
    open_count = Column(Integer, default=0)
    replied_at = Column(DateTime(timezone=True))
    reply_content = Column(Text)
    reply_classification = Column(String(50))
    follow_up_scheduled_at = Column(DateTime(timezone=True))
    follow_up_sequence_step = Column(Integer, default=1)
    outcome = Column(String(50))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class CompanyResearchReport(Base):
    """Company research report model."""

    __tablename__ = "company_research_reports"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    company_id = Column(GUID(), ForeignKey("companies.id", ondelete="CASCADE"))
    version = Column(Integer, default=1)
    report_type = Column(String(50), default="full")
    summary = Column(Text)
    full_report = Column(JSON)
    sources_used = Column(JSON, default=list)
    model_used = Column(String(100))
    embedding_id = Column(String(255))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    company = relationship("Company", back_populates="research_reports")


class Report(Base):
    """Report model."""

    __tablename__ = "reports"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    type = Column(String(50))
    period_start = Column(String(50))
    period_end = Column(String(50))
    title = Column(Text)
    summary = Column(Text)
    content = Column(JSON)
    markdown = Column(Text)
    metrics = Column(JSON)
    generated_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class AgentRun(Base):
    """Agent run model."""

    __tablename__ = "agent_runs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    agent_name = Column(String(100), nullable=False)
    trigger_type = Column(String(50))
    status = Column(String(50), default="running")
    started_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at = Column(DateTime(timezone=True))
    duration_ms = Column(Integer)
    input_payload = Column(JSON)
    output_summary = Column(JSON)
    error_message = Column(Text)
    items_processed = Column(Integer, default=0)
    items_created = Column(Integer, default=0)


class SearchConfig(Base):
    """Search configuration model."""

    __tablename__ = "search_configs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    type = Column(String(50))
    platform = Column(String(100))
    keywords = Column(JSON, default=list)
    filters = Column(JSON, default=dict)
    is_active = Column(Boolean, default=True)
    run_frequency = Column(String(50), default="daily")
    last_run = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Settings(Base):
    """Settings model."""

    __tablename__ = "settings"

    key = Column(String(255), primary_key=True)
    value = Column(JSON, nullable=False)
    description = Column(Text)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    """User account model for authentication, multi-tenancy, and RBAC."""

    __tablename__ = "users"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), default="")
    account_type = Column(String(50), default="individual")  # individual | enterprise
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    avatar_url = Column(Text)
    is_email_verified = Column(Boolean, default=False)
    roles = Column(JSON, default=lambda: ["user"])
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    profile = relationship("UserProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")
    memberships = relationship("OrganizationMember", back_populates="user", cascade="all, delete-orphan")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")


class RefreshToken(Base):
    """Stored refresh tokens for secure session rotation and revocation."""

    __tablename__ = "refresh_tokens"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    user = relationship("User", back_populates="refresh_tokens")


class PasswordResetToken(Base):
    """Secure password reset tokens with single-use expiration."""

    __tablename__ = "password_reset_tokens"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class Campaign(Base):
    """Outreach campaign definition."""

    __tablename__ = "campaigns"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    status = Column(String(50), default="draft")
    target_criteria = Column(JSON, default=dict)
    schedule = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class WorkflowExecution(Base):
    """Workflow execution state machine with atomic distributed locking."""

    __tablename__ = "workflow_executions"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workflow_type = Column(String(100), nullable=False)  # individual_career_engine, enterprise_talent_search, daily_discovery
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    status = Column(String(50), default="pending")  # pending, running, waiting, completed, failed, retrying, blocked, cancelled
    current_step = Column(String(100))
    lock_token = Column(String(255))
    input_params = Column(JSON, default=dict)
    output_summary = Column(JSON, default=dict)
    error_message = Column(Text)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)

    steps = relationship("WorkflowStep", back_populates="execution", cascade="all, delete-orphan")


class WorkflowStep(Base):
    """Individual stage step inside a sequential agent workflow."""

    __tablename__ = "workflow_steps"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    workflow_execution_id = Column(GUID(), ForeignKey("workflow_executions.id", ondelete="CASCADE"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False)
    step_index = Column(Integer, default=0)
    status = Column(String(50), default="waiting")  # waiting, running, completed, failed, retrying, blocked, cancelled
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    error_message = Column(Text)
    execution_logs = Column(JSON, default=list)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)

    execution = relationship("WorkflowExecution", back_populates="steps")


class RejectionLog(Base):
    """Persistent rejection recovery tracking to learn, discover alternative contacts, and search similar orgs."""

    __tablename__ = "rejection_logs"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    opportunity_id = Column(GUID(), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    contact_id = Column(GUID(), ForeignKey("contacts.id", ondelete="SET NULL"), nullable=True, index=True)
    rejection_source = Column(String(50), default="recipient_reply")  # recipient_reply, platform_status, manual
    rejection_reason = Column(Text)
    rejection_category = Column(String(100), default="Unknown reason")  # Skill mismatch, Experience mismatch, Location issue, Compensation issue, Timing issue, Competition, Unknown reason
    feedback_analysis = Column(JSON, default=dict)
    similar_search_triggered = Column(Boolean, default=False)
    similar_organizations_found = Column(JSON, default=list)
    alternate_contacts_found = Column(JSON, default=list)
    do_not_contact = Column(Boolean, default=False)  # Explicit rejection / opt-out
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)


class FollowUpSchedule(Base):
    """Intelligent automated follow-up sequence tracker."""

    __tablename__ = "follow_up_schedules"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    outreach_id = Column(GUID(), ForeignKey("outreach_history.id", ondelete="CASCADE"), nullable=False, index=True)
    contact_id = Column(GUID(), ForeignKey("contacts.id", ondelete="CASCADE"), nullable=False, index=True)
    proposal_id = Column(GUID(), ForeignKey("proposals.id", ondelete="SET NULL"), nullable=True)
    sequence_step = Column(Integer, default=1)  # 1 for Day 3, 2 for Day 7, 3 for Day 14
    delay_days = Column(Integer, default=3)
    scheduled_for = Column(DateTime(timezone=True), nullable=False)
    status = Column(String(50), default="scheduled")  # scheduled, sent, cancelled, skipped
    cancel_reason = Column(String(100))  # replied, unsubscribed, manual_cancel, opportunity_closed
    subject = Column(Text)
    body_draft = Column(Text)
    sent_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class TalentRequirement(Base):
    """Organization hiring or talent requirement for talent matching and headhunting."""

    __tablename__ = "talent_requirements"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    raw_description = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list)
    preferred_skills = Column(JSON, default=list)
    experience_level = Column(String(100), default="senior")  # junior, mid, senior, lead, principal, executive
    min_experience_years = Column(Float, default=0.0)
    max_experience_years = Column(Float)
    location_type = Column(String(50), default="remote")  # remote, hybrid, onsite, any
    location = Column(String(255))
    budget_currency = Column(String(10), default="USD")
    budget_min = Column(Float)
    budget_max = Column(Float)
    timeline = Column(String(100), default="immediate")
    engagement_type = Column(String(50), default="full-time")  # full-time, contract, freelance, fractional
    status = Column(String(50), default="active")  # draft, active, paused, fulfilled, closed
    ai_parsed_criteria = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AgentEvent(Base):
    """Persistent audit and real-time SSE event log."""

    __tablename__ = "agent_events"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    organization_id = Column(GUID(), ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(50), default="info")  # info, success, warning, error
    message = Column(Text, nullable=False)
    payload = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, index=True)


class GeneratedCV(Base):
    """An ATS-optimised CV built by CVBuilderAgent for one candidate.

    Stored per (user, opportunity) so a candidate keeps a tailored, auditable
    version per application, plus a base version when opportunity_id is NULL.
    The plain-text body is the source of truth - .docx/.pdf are rendered from it,
    which is also what makes the output verifiably machine-readable.
    """

    __tablename__ = "generated_cvs"
    __table_args__ = (
        Index("ix_generated_cvs_user_created", "user_id", "created_at"),
    )

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(GUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_id = Column(GUID(), ForeignKey("opportunities.id", ondelete="SET NULL"), nullable=True, index=True)
    version = Column(Integer, default=1)
    label = Column(String(255))  # e.g. "Senior Backend Engineer - Nova Labs"
    target_title = Column(String(255))
    target_company = Column(String(255))

    #: Canonical ATS-safe plain text. Renderers derive every other format.
    content_text = Column(Text, nullable=False)
    #: Section name -> rendered body, for editing individual sections in the UI.
    sections = Column(JSON, default=dict)
    cover_letter = Column(Text)

    ats_score = Column(Integer, default=0)
    ats_breakdown = Column(JSON, default=dict)  # keyword_coverage, format_safety, ...
    keywords_matched = Column(JSON, default=list)
    keywords_missing = Column(JSON, default=list)
    format_warnings = Column(JSON, default=list)

    generator = Column(String(50), default="template")  # ai | template
    ai_provider = Column(String(50))
    docx_path = Column(Text)
    pdf_path = Column(Text)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


__all__ = [
    "AgentEvent",
    "AgentRun",
    "Campaign",
    "Candidate",
    "Company",
    "CompanyResearchReport",
    "Contact",
    "CVExtraction",
    "Document",
    "FollowUpSchedule",
    "GeneratedCV",
    "Opportunity",
    "Organization",
    "OrganizationMember",
    "OutreachHistory",
    "PasswordResetToken",
    "Proposal",
    "RefreshToken",
    "RejectionLog",
    "Report",
    "SearchConfig",
    "Settings",
    "TalentRequirement",
    "User",
    "UserProfile",
    "WorkflowExecution",
    "WorkflowStep",
]
