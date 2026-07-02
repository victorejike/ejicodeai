"""Canonical SQLAlchemy ORM models for the backend."""
from datetime import datetime
import uuid

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
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


class Company(Base):
    """Company model."""

    __tablename__ = "companies"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
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
    """Opportunity model."""

    __tablename__ = "opportunities"

    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    company_id = Column(GUID(), ForeignKey("companies.id"))
    title = Column(String(500), nullable=False)
    type = Column(String(50), nullable=False)
    source_platform = Column(String(100))
    source_url = Column(Text, unique=True)
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


__all__ = [
    "AgentRun",
    "Company",
    "CompanyResearchReport",
    "Contact",
    "Opportunity",
    "OutreachHistory",
    "Proposal",
    "Report",
    "SearchConfig",
    "Settings",
]
