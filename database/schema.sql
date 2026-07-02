-- ============================================================
-- CORE TABLES - EJICODE BDP DATABASE SCHEMA v1.0
-- ============================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
-- Note: pgvector extension required for vector similarity search
-- Install with: CREATE EXTENSION IF NOT EXISTS "vector";
-- Requires postgres image with pgvector: pgvector/pgvector:pg16

-- ============================================================
-- COMPANIES
-- ============================================================
CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    domain          VARCHAR(255) UNIQUE,
    website_url     TEXT,
    linkedin_url    TEXT,
    github_org      TEXT,
    industry        VARCHAR(100),
    company_size    VARCHAR(50),
    funding_stage   VARCHAR(50),
    location        VARCHAR(255),
    description     TEXT,
    tech_stack      JSONB DEFAULT '[]',
    pain_points     JSONB DEFAULT '[]',
    fit_score       SMALLINT DEFAULT 0 CHECK (fit_score BETWEEN 0 AND 100),
    fit_reasoning   TEXT,
    status          VARCHAR(50) DEFAULT 'discovered',
    last_researched TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_companies_domain ON companies(domain);
CREATE INDEX idx_companies_fit_score ON companies(fit_score DESC);
CREATE INDEX idx_companies_status ON companies(status);
CREATE INDEX idx_companies_name_trgm ON companies USING GIN (name gin_trgm_ops);

-- ============================================================
-- CONTACTS
-- ============================================================
CREATE TABLE contacts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID REFERENCES companies(id) ON DELETE CASCADE,
    first_name      VARCHAR(100),
    last_name       VARCHAR(100),
    full_name       VARCHAR(255),
    email           VARCHAR(255),
    email_confidence VARCHAR(20) DEFAULT 'unverified',
    linkedin_url    TEXT,
    title           VARCHAR(255),
    role_category   VARCHAR(100),
    is_decision_maker BOOLEAN DEFAULT FALSE,
    source          VARCHAR(100),
    notes           TEXT,
    status          VARCHAR(50) DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contacts_company ON contacts(company_id);
CREATE INDEX idx_contacts_email ON contacts(email);
CREATE INDEX idx_contacts_decision_maker ON contacts(is_decision_maker) WHERE is_decision_maker = TRUE;

-- ============================================================
-- OPPORTUNITIES
-- ============================================================
CREATE TABLE opportunities (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID REFERENCES companies(id),
    title           VARCHAR(500) NOT NULL,
    type            VARCHAR(50) NOT NULL,
    source_platform VARCHAR(100),
    source_url      TEXT,
    raw_description TEXT,
    parsed_data     JSONB,
    location_type   VARCHAR(50),
    location        VARCHAR(255),
    salary_min      NUMERIC(12,2),
    salary_max      NUMERIC(12,2),
    salary_currency VARCHAR(10) DEFAULT 'USD',
    tech_required   JSONB DEFAULT '[]',
    score           SMALLINT DEFAULT 0 CHECK (score BETWEEN 0 AND 100),
    score_breakdown JSONB,
    rank            INTEGER,
    status          VARCHAR(50) DEFAULT 'new',
    posted_at       TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    discovered_at   TIMESTAMPTZ DEFAULT NOW(),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(source_url)
);

CREATE INDEX idx_opp_company ON opportunities(company_id);
CREATE INDEX idx_opp_type ON opportunities(type);
CREATE INDEX idx_opp_score ON opportunities(score DESC);
CREATE INDEX idx_opp_status ON opportunities(status);
CREATE INDEX idx_opp_posted_at ON opportunities(posted_at DESC);
CREATE INDEX idx_opp_tech ON opportunities USING GIN (tech_required jsonb_path_ops);

-- ============================================================
-- PROPOSALS
-- ============================================================
CREATE TABLE proposals (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    opportunity_id  UUID REFERENCES opportunities(id),
    contact_id      UUID REFERENCES contacts(id),
    type            VARCHAR(50),
    subject         TEXT,
    body            TEXT NOT NULL,
    tone            VARCHAR(50) DEFAULT 'professional',
    word_count      INTEGER,
    generation_model VARCHAR(100),
    generation_prompt TEXT,
    rag_context     JSONB,
    status          VARCHAR(50) DEFAULT 'draft',
    approved_by     VARCHAR(255),
    approved_at     TIMESTAMPTZ,
    rejection_reason TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_proposals_opportunity ON proposals(opportunity_id);
CREATE INDEX idx_proposals_status ON proposals(status);

-- ============================================================
-- OUTREACH HISTORY
-- ============================================================
CREATE TABLE outreach_history (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    proposal_id     UUID REFERENCES proposals(id),
    contact_id      UUID REFERENCES contacts(id),
    opportunity_id  UUID REFERENCES opportunities(id),
    sent_at         TIMESTAMPTZ,
    delivery_status VARCHAR(50) DEFAULT 'pending',
    message_id      VARCHAR(255),
    opened_at       TIMESTAMPTZ,
    open_count      INTEGER DEFAULT 0,
    replied_at      TIMESTAMPTZ,
    reply_content   TEXT,
    reply_classification VARCHAR(50),
    follow_up_scheduled_at TIMESTAMPTZ,
    follow_up_sequence_step INTEGER DEFAULT 1,
    outcome         VARCHAR(50),
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_outreach_proposal ON outreach_history(proposal_id);
CREATE INDEX idx_outreach_contact ON outreach_history(contact_id);
CREATE INDEX idx_outreach_sent_at ON outreach_history(sent_at DESC);
CREATE INDEX idx_outreach_follow_up ON outreach_history(follow_up_scheduled_at)
    WHERE follow_up_scheduled_at IS NOT NULL;

-- ============================================================
-- COMPANY RESEARCH REPORTS
-- ============================================================
CREATE TABLE company_research_reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID REFERENCES companies(id) ON DELETE CASCADE,
    version         INTEGER DEFAULT 1,
    report_type     VARCHAR(50) DEFAULT 'full',
    summary         TEXT,
    full_report     JSONB,
    sources_used    JSONB DEFAULT '[]',
    model_used      VARCHAR(100),
    embedding_id    VARCHAR(255),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_research_company ON company_research_reports(company_id);
CREATE INDEX idx_research_created ON company_research_reports(created_at DESC);

-- ============================================================
-- REPORTS
-- ============================================================
CREATE TABLE reports (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    type            VARCHAR(50),
    period_start    DATE,
    period_end      DATE,
    title           TEXT,
    summary         TEXT,
    content         JSONB,
    markdown        TEXT,
    metrics         JSONB,
    generated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AGENT RUNS
-- ============================================================
CREATE TABLE agent_runs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_name      VARCHAR(100) NOT NULL,
    trigger_type    VARCHAR(50),
    status          VARCHAR(50) DEFAULT 'running',
    started_at      TIMESTAMPTZ DEFAULT NOW(),
    completed_at    TIMESTAMPTZ,
    duration_ms     INTEGER,
    input_payload   JSONB,
    output_summary  JSONB,
    error_message   TEXT,
    items_processed INTEGER DEFAULT 0,
    items_created   INTEGER DEFAULT 0
);

CREATE INDEX idx_agent_runs_agent ON agent_runs(agent_name);
CREATE INDEX idx_agent_runs_status ON agent_runs(status);
CREATE INDEX idx_agent_runs_started ON agent_runs(started_at DESC);

-- ============================================================
-- SEARCH CONFIGURATIONS
-- ============================================================
CREATE TABLE search_configs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    type            VARCHAR(50),
    platform        VARCHAR(100),
    keywords        JSONB DEFAULT '[]',
    filters         JSONB DEFAULT '{}',
    is_active       BOOLEAN DEFAULT TRUE,
    run_frequency   VARCHAR(50) DEFAULT 'daily',
    last_run        TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SETTINGS
-- ============================================================
CREATE TABLE settings (
    key             VARCHAR(255) PRIMARY KEY,
    value           JSONB NOT NULL,
    description     TEXT,
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- Insert default settings
INSERT INTO settings (key, value, description) VALUES
('company_profile', '{
    "name": "Ejicode",
    "tagline": "empathy and engineering, inseparable",
    "services": ["AI Engineering", "Backend Development", "Full Stack", "API Development",
                 "Cloud Infrastructure", "Automation", "Enterprise Software"],
    "tech_stack": ["Go", "Python", "React", "Vue", "FastAPI", "PostgreSQL", "Docker"],
    "minimum_contract_value": 2000,
    "target_company_sizes": ["startup", "small", "mid"],
    "preferred_locations": ["remote", "UK", "US", "UAE"]
}', 'Ejicode company profile for proposal generation'),
('outreach_limits', '{
    "max_emails_per_day": 50,
    "min_send_interval_minutes": 5,
    "follow_up_interval_days": 5,
    "max_follow_ups": 3
}', 'Outreach rate limits');
