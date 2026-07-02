# Agent Playbooks — Per-Agent Operation Runbooks

## Agent Execution Model

All agents follow this lifecycle:
1. **Input Validation** — Verify required parameters
2. **Execution** — Perform agent task
3. **Output Validation** — Verify output quality
4. **Error Handling** — Retry logic + escalation
5. **Audit Trail** — Log to agent_runs table

---

## Job Scout Agent

**Mission**: Discover job and contract opportunities across platforms

**Trigger**: Daily 06:00 UTC (APScheduler)

**Inputs**:
- trigger_type: "scheduled" or "manual"
- keywords: Optional custom search terms

**Process**:
1. Initialize scrapers (RemoteOK, WeWorkRemotely, LinkedIn, HackerNews, Upwork, Contra)
2. Scrape each platform concurrently (httpx + Playwright)
3. Parse job postings (Qwen2.5-Coder via Ollama)
4. Deduplicate by URL (Bloom filter + DB lookup)
5. Filter by relevance (tech stack, location)
6. Normalize to OpportunitySchema
7. Store to opportunities table

**Outputs**:
- List of Opportunity records
- Count of unique opportunities found
- Count by platform

**Success Criteria**:
- Score > 0 for at least 1 opportunity
- No fatal scraping errors

**Failure Handling**:
- Retry failed platforms: up to 3 times with exponential backoff
- Mark source as DEGRADED if consistent failures
- Log raw HTML for manual review

**Escalation**:
- If no opportunities found for 3+ days
- If all scrapers fail

---

## Company Scout Agent

**Mission**: Discover companies needing Ejicode services

**Trigger**: Daily 12:00 UTC

**Inputs**:
- trigger_type: "scheduled" or "manual"

**Process**:
1. Search ProductHunt for new launches
2. Scrape Crunchbase for recently funded companies
3. Search LinkedIn company pages
4. Extract company metadata (size, stage, industry)
5. Classify fit score using LLM (Mistral 7B)
6. Deduplicate by domain

**Outputs**:
- List of Company records
- Count of companies discovered

**Success Criteria**:
- Score > 0 for at least 1 company

**Failure Handling**:
- Retry individual sources: up to 2 times
- Continue with partial results

---

## Research Agent

**Mission**: Perform deep analysis on discovered companies

**Trigger**: 
- Auto-triggered for companies with fit_score > 60
- Manual trigger via API

**Inputs**:
- company_id: UUID
- domain: str (website domain)

**Process**:
1. Scrape company website (homepage, about, services, careers, blog)
2. Extract text content from each page
3. Detect tech stack (Wappalyzer signals + keyword matching)
4. Analyze with DeepSeek-R1:
   - Core business model
   - Engineering team size estimate
   - Pain points from job descriptions
   - Ejicode service fit (0-100)
   - Recommended outreach angle
5. Embed report in ChromaDB
6. Store CompanyResearchReport record

**Outputs**:
- Structured company research report
- Updated companies record with fit_score + fit_reasoning
- Embedding ID for RAG retrieval

**Success Criteria**:
- confidence_score >= 0.65
- All sections populated

**Failure Handling**:
- Retry website scrape: up to 2 times
- Store partial report with confidence < 0.65
- Escalate to human if < 0.5

**Escalation Threshold**:
- confidence_score < 0.5
- Cannot reach website (404, timeout)
- Insufficient data for analysis

---

## Ranking Agent

**Mission**: Score and prioritize opportunities

**Trigger**: Auto-triggered after opportunity discovery

**Inputs**:
- opportunities: List of Opportunity records
- companies: Dict of Company records

**Scoring Rubric** (100 points total):
- Technology Match (25 pts): % overlap with Ejicode tech stack
- Company Fit (20 pts): Size + funding stage preference
- Contact Availability (15 pts): Verified email + decision maker
- Compensation (15 pts): Meets minimum ($2k/month contract, $50k/year job)
- Response Probability (15 pts): Historical win rate by type
- Urgency Signal (10 pts): Posted < 3 days, "urgent" keywords

**Process**:
1. Calculate score for each opportunity
2. Generate score_breakdown JSON
3. Sort by score descending
4. Assign rank based on sort order
5. Store scores to opportunities table
6. Update Redis priority queue

**Outputs**:
- Updated opportunities with score, rank, score_breakdown
- Ranked priority queue in Redis

**Success Criteria**:
- All opportunities scored
- No errors in calculation

---

## Contact Discovery Agent

**Mission**: Find decision-maker contact information

**Trigger**:
- Auto-triggered for companies with fit_score > 60
- Manual trigger via API

**Inputs**:
- company_id: UUID
- domain: str
- company_name: str

**Process**:
1. Scrape website for email addresses
2. Search LinkedIn company page
3. Validate emails via SMTP (RCPT TO without sending)
4. Classify confidence level:
   - "verified": SMTP validation passed
   - "probable": Pattern match (e.g., firstname@domain)
   - "unverified": Not validated
5. Identify decision makers (CTO, VP Engineering, Founder)
6. Store to contacts table

**Outputs**:
- List of Contact records
- Confidence scores per contact

**Success Criteria**:
- At least 1 contact with email_confidence >= "probable"

**Failure Handling**:
- Continue with partial results
- Store unverified contacts with note
- Escalate if 0 contacts found

---

## Proposal Generation Agent

**Mission**: Generate personalized outreach messages (Phase 3)

**Trigger**: Manual (human selects opportunity for outreach)

**Inputs**:
- opportunity_id: UUID
- contact_id: UUID
- type: "cold_email" | "cover_letter" | "project_proposal"
- tone: "professional" | "friendly" | "technical"

**Process** (Two-Pass LLM):
1. Retrieve RAG context (similar proposals, company intel, Ejicode capabilities)
2. Pass 1 (DeepSeek-R1 Reasoning):
   - Analyze company pain points
   - Map Ejicode services to needs
   - Identify strongest angle
3. Pass 2 (Llama 3.1 Refinement):
   - Draft subject line (3 variants)
   - Draft email body (150-300 words)
   - Apply Ejicode brand voice

**Outputs**:
- Proposal record (status: draft)
- Subject line + body
- Word count, reading time

**Success Criteria**:
- No generic phrases
- Personalization score > 0.7
- Readability score > 70

---

## Outreach Agent

**Mission**: Send approved emails with tracking (Phase 3)

**Trigger**: Manual approval of proposal

**Inputs**:
- proposal_id: UUID (status must be "approved")

**Process**:
1. Validate SMTP configuration
2. Generate unique tracking pixel URL
3. Inject tracking pixel into email body
4. Send via SMTP (Brevo/Mailgun free or self-hosted)
5. Log to outreach_history (delivery_status = "pending")
6. Schedule tracking pixel load poll

**Outputs**:
- outreach_history record with message_id
- Email delivered to recipient

**Success Criteria**:
- SMTP send returns success
- message_id captured

**Failure Handling**:
- Retry up to 3 times with exponential backoff
- Log error + email for manual retry
- Mark as FAILED if 3 retries exhausted

**Rate Limiting**:
- Max 50 emails/day per SMTP account
- Min 5-minute spacing between sends

---

## Follow-Up Agent

**Mission**: Monitor responses and execute follow-up sequences (Phase 3)

**Trigger**: Scheduled (every 6 hours)

**Process**:
1. Poll IMAP inbox for new replies
2. Match replies to sent outreach (by message_id)
3. Classify reply with LLM:
   - INTERESTED: Positive signal, request meeting
   - NOT_INTERESTED: Negative, close opportunity
   - REQUEST_INFO: Questions about service, generate answer draft
   - AUTO_REPLY: Out-of-office detection, mark for later
   - BOUNCE: Undeliverable, mark contact invalid, find alternate
4. Trigger follow-up sequences based on rules:
   - No reply after 5 days: Send follow-up #2
   - No reply after 10 days: Send follow-up #3
   - No reply after 15 days: Mark COLD, archive

**Outputs**:
- Updated outreach_history (reply_content, reply_classification)
- New proposal records for follow-ups
- Status transitions in opportunities

---

## Reporting Agent

**Mission**: Generate daily & weekly intelligence reports

**Trigger**: 
- Daily: 18:00 UTC
- Weekly: Sunday 08:00 UTC

**Process**:
1. Query all metrics from database
2. Calculate funnel metrics (discovery → outreach → response → meeting)
3. Trend analysis vs. previous period
4. Identify anomalies
5. Generate markdown report
6. Store to reports table
7. Send email digest (if configured)

**Daily Report Contents**:
- Opportunities discovered (count + by type/source)
- Companies researched
- Outreach sent/opened/replied
- Top 5 priority opportunities
- Agent health summary

**Weekly Report Contents**:
- Conversion funnel metrics
- Response rate by opportunity type
- Top performing outreach templates
- Pipeline value (estimated revenue)

---

## Supervisor Agent

**Mission**: Orchestrate all sub-agents

**Trigger**: Manual (daily_discovery) or event-driven

**Workflows**:

**daily_discovery**:
1. Job Scout → Company Scout
2. Rank opportunities
3. Research top 5
4. Discover contacts for researched
5. Sync knowledge base

**manual_research**:
1. Research specific company
2. Discover contacts
3. Update knowledge base

**manual_outreach_trigger**:
1. Validate opportunity + contact
2. Generate proposal
3. Queue for human approval

**Error Recovery**:
- Retry failed agents: up to 3 times
- Escalate on third failure
- Dead-letter queue for manual replay

**Escalation Criteria**:
- confidence_score < 0.65
- Agent timeout (> 10 min)
- Data quality failure
- Multiple retries exhausted

---

## Monitoring & Health Checks

**Agent Health Indicators**:
- Last run timestamp
- Success/failure rate (rolling 30-day)
- Average execution time
- Error count

**Alerts**:
- Agent down for > 24 hours
- Failure rate > 50% (last 24 hours)
- Execution timeout (> configured limit)
- Database connection issues

**Dashboard Metrics**:
- All agents status (green/yellow/red)
- Recent runs with errors
- Agent execution timeline

---

## Testing Agents Locally

```bash
# Test Job Scout
python -c "
import asyncio
from agents.job_scout.job_scout_agent import JobScoutAgent
from agents.base.base_agent import AgentState

agent = JobScoutAgent()
state = {'status': 'pending', 'input_data': {}, 'output_data': {}}
result = asyncio.run(agent.process(state))
print(f\"Found {result.get('output_data', {}).get('count')} opportunities\")
"

# Test Ranking
python -c "
import asyncio
from agents.ranking.ranking_agent import RankingAgent

agent = RankingAgent()
state = {
    'status': 'pending',
    'input_data': {'opportunities': [], 'companies': {}},
    'output_data': {}
}
result = asyncio.run(agent.process(state))
print(f\"Ranked {len(result.get('output_data', {}).get('opportunities', []))} opportunities\")
"
```

