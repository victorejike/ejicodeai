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
-- USERS & AUTH
-- ============================================================
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    username        VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name       VARCHAR(255) DEFAULT '',
    roles           JSONB DEFAULT '["user"]',
    is_active       BOOLEAN DEFAULT TRUE,
    is_superuser    BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_username ON users(username);

CREATE TABLE refresh_tokens (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash      VARCHAR(255) UNIQUE NOT NULL,
    expires_at      TIMESTAMPTZ NOT NULL,
    revoked         BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
CREATE INDEX idx_refresh_tokens_hash ON refresh_tokens(token_hash);

-- ============================================================
-- CAMPAIGNS
-- ============================================================
CREATE TABLE campaigns (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    description     TEXT,
    status          VARCHAR(50) DEFAULT 'draft',
    target_criteria JSONB DEFAULT '{}',
    schedule        JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
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
}', 'Outreach rate limits')
ON CONFLICT (key) DO NOTHING;

-- ============================================================
-- ORGANIZATIONS (MULTI-TENANCY)
-- ============================================================
CREATE TABLE IF NOT EXISTS organizations (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(255) NOT NULL,
    slug            VARCHAR(255) UNIQUE NOT NULL,
    domain          VARCHAR(255),
    plan            VARCHAR(50) DEFAULT 'pro',
    billing_email   VARCHAR(255),
    settings        JSONB DEFAULT '{}',
    status          VARCHAR(50) DEFAULT 'active',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_organizations_slug ON organizations(slug);

CREATE TABLE IF NOT EXISTS organization_members (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    user_id         UUID REFERENCES users(id) ON DELETE CASCADE,
    role            VARCHAR(50) DEFAULT 'member',
    permissions     JSONB DEFAULT '[]',
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_org_members_org ON organization_members(organization_id);
CREATE INDEX IF NOT EXISTS idx_org_members_user ON organization_members(user_id);

-- ============================================================
-- USER PROFILES (INDIVIDUAL USERS)
-- ============================================================
CREATE TABLE IF NOT EXISTS user_profiles (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id             UUID REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    full_name           VARCHAR(255),
    title               VARCHAR(255),
    bio                 TEXT,
    skills              JSONB DEFAULT '[]',
    experience_years    NUMERIC(4,1) DEFAULT 0.0,
    experience          JSONB DEFAULT '[]',
    education           JSONB DEFAULT '[]',
    portfolio_url       TEXT,
    github_url          TEXT,
    linkedin_url        TEXT,
    resume_url          TEXT,
    certifications      JSONB DEFAULT '[]',
    location            VARCHAR(255),
    preferred_locations JSONB DEFAULT '[]',
    remote_preference   VARCHAR(50) DEFAULT 'remote',
    job_types           JSONB DEFAULT '["contract", "full-time"]',
    salary_min          NUMERIC(12,2),
    salary_max          NUMERIC(12,2),
    salary_currency     VARCHAR(10) DEFAULT 'USD',
    technologies        JSONB DEFAULT '[]',
    career_goals        TEXT,
    ai_candidate_summary JSONB DEFAULT '{}',
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_user_profiles_user ON user_profiles(user_id);

-- ============================================================
-- CANDIDATES (ENTERPRISE TALENT PIPELINE)
-- ============================================================
CREATE TABLE IF NOT EXISTS candidates (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    organization_id     UUID REFERENCES organizations(id) ON DELETE CASCADE,
    full_name           VARCHAR(255) NOT NULL,
    email               VARCHAR(255),
    phone               VARCHAR(50),
    title               VARCHAR(255),
    skills              JSONB DEFAULT '[]',
    experience_summary  TEXT,
    location            VARCHAR(255),
    github_url          TEXT,
    linkedin_url        TEXT,
    portfolio_url       TEXT,
    resume_text         TEXT,
    status              VARCHAR(50) DEFAULT 'discovered',
    match_score         INTEGER DEFAULT 0,
    match_explanation   TEXT,
    source              VARCHAR(100) DEFAULT 'ai_scout',
    notes               TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_candidates_org ON candidates(organization_id);
CREATE INDEX IF NOT EXISTS idx_candidates_status ON candidates(status);

-- ============================================================
-- WORKFLOW EXECUTIONS & AGENT LOCKING
-- ============================================================
CREATE TABLE IF NOT EXISTS workflow_executions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_type   VARCHAR(100) NOT NULL,
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    status          VARCHAR(50) DEFAULT 'pending',
    current_step    VARCHAR(100),
    lock_token      VARCHAR(255),
    input_params    JSONB DEFAULT '{}',
    output_summary  JSONB DEFAULT '{}',
    error_message   TEXT,
    started_at      TIMESTAMPTZ,
    completed_at    TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wf_exec_status ON workflow_executions(status);
CREATE INDEX IF NOT EXISTS idx_wf_exec_user ON workflow_executions(user_id);
CREATE INDEX IF NOT EXISTS idx_wf_exec_org ON workflow_executions(organization_id);

CREATE TABLE IF NOT EXISTS workflow_steps (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    workflow_execution_id   UUID REFERENCES workflow_executions(id) ON DELETE CASCADE,
    agent_name              VARCHAR(100) NOT NULL,
    step_index              INTEGER DEFAULT 0,
    status                  VARCHAR(50) DEFAULT 'waiting',
    input_data              JSONB DEFAULT '{}',
    output_data             JSONB DEFAULT '{}',
    retry_count             INTEGER DEFAULT 0,
    max_retries             INTEGER DEFAULT 3,
    error_message           TEXT,
    execution_logs          JSONB DEFAULT '[]',
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_wf_step_exec ON workflow_steps(workflow_execution_id);
CREATE INDEX IF NOT EXISTS idx_wf_step_status ON workflow_steps(status);

-- ============================================================
-- REJECTION LOGS (PERSISTENT LEARNING)
-- ============================================================
CREATE TABLE IF NOT EXISTS rejection_logs (
    id                          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id                     UUID REFERENCES users(id) ON DELETE SET NULL,
    opportunity_id              UUID REFERENCES opportunities(id) ON DELETE SET NULL,
    contact_id                  UUID REFERENCES contacts(id) ON DELETE SET NULL,
    rejection_source            VARCHAR(50) DEFAULT 'recipient_reply',
    rejection_reason            TEXT,
    feedback_analysis           JSONB DEFAULT '{}',
    similar_search_triggered    BOOLEAN DEFAULT FALSE,
    similar_organizations_found JSONB DEFAULT '[]',
    alternate_contacts_found    JSONB DEFAULT '[]',
    created_at                  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_rejection_logs_user ON rejection_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_rejection_logs_opp ON rejection_logs(opportunity_id);

-- ============================================================
-- FOLLOW-UP SCHEDULES
-- ============================================================
CREATE TABLE IF NOT EXISTS follow_up_schedules (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    outreach_id     UUID REFERENCES outreach_history(id) ON DELETE CASCADE,
    contact_id      UUID REFERENCES contacts(id) ON DELETE CASCADE,
    proposal_id     UUID REFERENCES proposals(id) ON DELETE SET NULL,
    sequence_step   INTEGER DEFAULT 1,
    delay_days      INTEGER DEFAULT 3,
    scheduled_for   TIMESTAMPTZ NOT NULL,
    status          VARCHAR(50) DEFAULT 'scheduled',
    cancel_reason   VARCHAR(100),
    subject         TEXT,
    body_draft      TEXT,
    sent_at         TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_followup_sched_outreach ON follow_up_schedules(outreach_id);
CREATE INDEX IF NOT EXISTS idx_followup_sched_status ON follow_up_schedules(status);

-- ============================================================
-- PASSWORD RESET TOKENS
-- ============================================================
CREATE TABLE IF NOT EXISTS password_reset_tokens (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id     UUID REFERENCES users(id) ON DELETE CASCADE,
    token_hash  VARCHAR(255) UNIQUE NOT NULL,
    expires_at  TIMESTAMPTZ NOT NULL,
    used        BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_pwd_reset_tokens_user ON password_reset_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_pwd_reset_tokens_hash ON password_reset_tokens(token_hash);


