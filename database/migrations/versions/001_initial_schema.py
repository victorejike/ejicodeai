"""Initial migration: Create all base tables matching ORM models.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-07-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa

revision = '001_initial_schema'
down_revision = None
branch_labels = None
depends_on = None

# Use server_default for UUIDs — works on both Postgres (gen_random_uuid) and SQLite (handled by ORM)
_uuid_col = lambda name, **kw: sa.Column(name, sa.String(36), **kw)


def upgrade() -> None:
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    uuid_default = sa.text("gen_random_uuid()") if is_pg else None

    def uuid_pk():
        return sa.Column("id", sa.String(36), primary_key=True,
                         server_default=uuid_default if is_pg else None)

    op.create_table(
        "companies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), unique=True),
        sa.Column("website_url", sa.Text),
        sa.Column("linkedin_url", sa.Text),
        sa.Column("github_org", sa.Text),
        sa.Column("industry", sa.String(100)),
        sa.Column("company_size", sa.String(50)),
        sa.Column("funding_stage", sa.String(50)),
        sa.Column("location", sa.String(255)),
        sa.Column("description", sa.Text),
        sa.Column("tech_stack", sa.JSON),
        sa.Column("pain_points", sa.JSON),
        sa.Column("fit_score", sa.Integer, server_default="0"),
        sa.Column("fit_reasoning", sa.Text),
        sa.Column("status", sa.String(50), server_default="discovered"),
        sa.Column("last_researched", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_companies_domain", "companies", ["domain"])
    op.create_index("ix_companies_fit_score", "companies", ["fit_score"])
    op.create_index("ix_companies_status", "companies", ["status"])

    op.create_table(
        "contacts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE")),
        sa.Column("first_name", sa.String(100)),
        sa.Column("last_name", sa.String(100)),
        sa.Column("full_name", sa.String(255)),
        sa.Column("email", sa.String(255)),
        sa.Column("email_confidence", sa.String(20), server_default="unverified"),
        sa.Column("linkedin_url", sa.Text),
        sa.Column("title", sa.String(255)),
        sa.Column("role_category", sa.String(100)),
        sa.Column("is_decision_maker", sa.Boolean, server_default="0"),
        sa.Column("source", sa.String(100)),
        sa.Column("notes", sa.Text),
        sa.Column("status", sa.String(50), server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_contacts_company_id", "contacts", ["company_id"])
    op.create_index("ix_contacts_email", "contacts", ["email"])

    op.create_table(
        "opportunities",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id")),
        sa.Column("title", sa.String(500), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("source_platform", sa.String(100)),
        sa.Column("source_url", sa.Text, unique=True),
        sa.Column("raw_description", sa.Text),
        sa.Column("parsed_data", sa.JSON),
        sa.Column("location_type", sa.String(50)),
        sa.Column("location", sa.String(255)),
        sa.Column("salary_min", sa.Float),
        sa.Column("salary_max", sa.Float),
        sa.Column("salary_currency", sa.String(10), server_default="USD"),
        sa.Column("tech_required", sa.JSON),
        sa.Column("score", sa.Integer, server_default="0"),
        sa.Column("score_breakdown", sa.JSON),
        sa.Column("rank", sa.Integer),
        sa.Column("status", sa.String(50), server_default="new"),
        sa.Column("posted_at", sa.DateTime(timezone=True)),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_opp_company", "opportunities", ["company_id"])
    op.create_index("ix_opp_score", "opportunities", ["score"])
    op.create_index("ix_opp_status", "opportunities", ["status"])

    op.create_table(
        "proposals",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id")),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id")),
        sa.Column("type", sa.String(50)),
        sa.Column("subject", sa.Text),
        sa.Column("body", sa.Text, nullable=False),
        sa.Column("tone", sa.String(50), server_default="professional"),
        sa.Column("word_count", sa.Integer),
        sa.Column("generation_model", sa.String(100)),
        sa.Column("generation_prompt", sa.Text),
        sa.Column("rag_context", sa.JSON),
        sa.Column("status", sa.String(50), server_default="draft"),
        sa.Column("approved_by", sa.String(255)),
        sa.Column("approved_at", sa.DateTime(timezone=True)),
        sa.Column("rejection_reason", sa.Text),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_proposals_status", "proposals", ["status"])

    op.create_table(
        "outreach_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(36), sa.ForeignKey("proposals.id")),
        sa.Column("contact_id", sa.String(36), sa.ForeignKey("contacts.id")),
        sa.Column("opportunity_id", sa.String(36), sa.ForeignKey("opportunities.id")),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("delivery_status", sa.String(50), server_default="pending"),
        sa.Column("message_id", sa.String(255)),
        sa.Column("opened_at", sa.DateTime(timezone=True)),
        sa.Column("open_count", sa.Integer, server_default="0"),
        sa.Column("replied_at", sa.DateTime(timezone=True)),
        sa.Column("reply_content", sa.Text),
        sa.Column("reply_classification", sa.String(50)),
        sa.Column("follow_up_scheduled_at", sa.DateTime(timezone=True)),
        sa.Column("follow_up_sequence_step", sa.Integer, server_default="1"),
        sa.Column("outcome", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_outreach_proposal", "outreach_history", ["proposal_id"])
    op.create_index("ix_outreach_contact", "outreach_history", ["contact_id"])

    op.create_table(
        "company_research_reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("company_id", sa.String(36), sa.ForeignKey("companies.id", ondelete="CASCADE")),
        sa.Column("version", sa.Integer, server_default="1"),
        sa.Column("report_type", sa.String(50), server_default="full"),
        sa.Column("summary", sa.Text),
        sa.Column("full_report", sa.JSON),
        sa.Column("sources_used", sa.JSON),
        sa.Column("model_used", sa.String(100)),
        sa.Column("embedding_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "reports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", sa.String(50)),
        sa.Column("period_start", sa.String(50)),
        sa.Column("period_end", sa.String(50)),
        sa.Column("title", sa.Text),
        sa.Column("summary", sa.Text),
        sa.Column("content", sa.JSON),
        sa.Column("markdown", sa.Text),
        sa.Column("metrics", sa.JSON),
        sa.Column("generated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_name", sa.String(100), nullable=False),
        sa.Column("trigger_type", sa.String(50)),
        sa.Column("status", sa.String(50), server_default="running"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer),
        sa.Column("input_payload", sa.JSON),
        sa.Column("output_summary", sa.JSON),
        sa.Column("error_message", sa.Text),
        sa.Column("items_processed", sa.Integer, server_default="0"),
        sa.Column("items_created", sa.Integer, server_default="0"),
    )
    op.create_index("ix_agent_runs_agent", "agent_runs", ["agent_name"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])

    op.create_table(
        "search_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("type", sa.String(50)),
        sa.Column("platform", sa.String(100)),
        sa.Column("keywords", sa.JSON),
        sa.Column("filters", sa.JSON),
        sa.Column("is_active", sa.Boolean, server_default="1"),
        sa.Column("run_frequency", sa.String(50), server_default="daily"),
        sa.Column("last_run", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "settings",
        sa.Column("key", sa.String(255), primary_key=True),
        sa.Column("value", sa.JSON, nullable=False),
        sa.Column("description", sa.Text),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for tbl in ["settings", "search_configs", "agent_runs", "reports",
                "company_research_reports", "outreach_history", "proposals",
                "opportunities", "contacts", "companies"]:
        op.drop_table(tbl)
