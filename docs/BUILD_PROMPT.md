# EJICODE AI — BUILD PROMPT & SYSTEM SPECIFICATION

==================================================
CORE OBJECTIVE — INDIVIDUAL
===========================

The primary objective of the INDIVIDUAL version of EJICODE AI is:

**GET THE USER HIRED.**

EJICODE AI acts as an intelligent AI career agent that continuously works to market the individual professionally, discover relevant opportunities, position the individual against those opportunities, prepare personalized applications and outreach, track responses, learn from rejection, and continue searching until the user achieves a successful outcome.

The product must NOT feel like a normal job board.

The user must feel like they have an AI career team working for them 24/7.

The system helps the individual:
* Discover relevant opportunities
* Market their skills
* Improve their professional positioning
* Match themselves to companies
* Find companies that need their skills
* Identify relevant decision-makers
* Prepare personalized applications
* Prepare proposals
* Prepare professional outreach
* Track applications
* Track outreach
* Follow up intelligently
* Learn from rejection
* Find alternative opportunities
* Continuously search for better opportunities

The ultimate KPI for the individual experience is:

**HIRING SUCCESS**

Not: "Number of jobs scraped."
Not: "Number of searches completed."

The platform optimizes toward:
* Quality opportunities
* Relevant applications
* Positive responses
* Interviews
* Offers
* Successful placements

==================================================
SPEED + INTELLIGENCE
====================

The entire EJICODE AI system is designed for:

**FAST + ACCURATE + INTELLIGENT EXECUTION**

Agents must not unnecessarily wait for long periods.
When a workflow can safely execute quickly, execute it quickly.
When tasks genuinely depend on another task, enforce the dependency.

Use:
* Async processing (`asyncio`, FastAPI async endpoints)
* Background workers & task queues (Celery + Redis)
* Parallel processing where safe
* Caching (Redis key-value cache)
* Database indexes (PostgreSQL / SQLite optimized indexes)
* Efficient API calls (Batched LLM / HTTP requests)
* Concurrent source discovery where appropriate

However, NEVER sacrifice accuracy for speed.
The objective is: **Fast execution without corrupting data or producing low-quality results.**

==================================================
INTELLIGENT AGENT ORCHESTRATION
===============================

The AI understands dependencies between agents. Do NOT run every agent simultaneously.

Execution DAG Pipeline:

SOURCE DISCOVERY (Concurrent execution across 8 source categories)
Google ─────────┐
Company Sites ──┤
Job Boards ─────┤
GitHub ─────────┤
Reddit ─────────┤
Other Sources ──┘
       │
       ▼
MERGE RESULTS
       │
       ▼
EXTRACTION
       │
       ▼
VALIDATION (Anti-Scam & Safety Verification)
       │
       ▼
DEDUPLICATION (Cross-platform canonical merging)
       │
       ▼
RESEARCH (Company profiling & tech stack audit)
       │
       ▼
MATCHING (Candidate fit & transferable skills scoring)
       │
       ▼
CONTACT DISCOVERY (Decision-maker email verification)
       │
       ▼
APPLICATION / PROPOSAL GENERATION
       │
       ▼
HUMAN APPROVAL GATE (Safety verification)
       │
       ▼
OUTREACH DISPATCH
       │
       ▼
FOLLOW-UP SEQUENCING
       │
       ▼
MONITORING & REJECTION INTELLIGENCE

Each dependent stage waits for the previous required stage. Independent work executes concurrently.

==================================================
INDIVIDUAL AI CAREER AGENT & CANDIDATE PROFILE
==============================================

Create an Individual AI Career Agent that continuously manages the user's career opportunity pipeline.

Candidate Intelligence Profile Schema:
* Skills (Technical, Soft, Tools, Frameworks)
* Experience (Roles, Achievements, Durations, Technologies used)
* Projects (Name, Description, Tech Stack, Live Links, Impact)
* Education & Certifications
* Portfolio URL, GitHub URL, LinkedIn URL, CV/Resume Content
* Location & Remote Preference (Remote Worldwide, Remote Regional, Hybrid, On-site)
* Compensation Expectations (Min/Max Salary, Rate, Currency)
* Job Preferences & Career Goals
* Preferred Industries & Targeted Companies
* Availability & Professional Strengths

==================================================
AI SELF-MARKETING ENGINE
========================

The AI Self-Marketing Engine professionally markets the individual with tailored materials:
* Professional bio (Short, Medium, Full)
* Resume positioning & highlight optimization
* Portfolio positioning for targeted roles
* Highly tailored Cover letters & Job applications
* High-converting Freelance proposals
* Professional introduction & pitch messages
* Value propositions & Company-specific pitches
* Automated intelligent follow-up communications

TRUTHFULNESS DIRECTIVE:
Every message is personalized using the user's actual background.
NEVER fabricate: Experience, Jobs, Skills, Certifications, Achievements, Education, or Clients.
The AI markets the user strongly while remaining 100% truthful.

==================================================
OPPORTUNITY DISCOVERY & TRANSFERABLE SKILLS
===========================================

Do not only search for jobs matching the exact user title. Use intelligent semantic matching.
Example: For a "Software Engineer", evaluate:
* Backend Engineer, Full Stack Engineer, AI Engineer
* Python Developer, Go Developer, Platform Engineer
* Automation Engineer, ML Engineer, Software Developer

The AI maps transferable skills dynamically across domains and tech stacks.

==================================================
COMPANY-FIRST JOB DISCOVERY
===========================

Search for companies that need the user's skills even when a job listing is not posted on traditional job boards:
* Companies hiring similar roles or expanding engineering teams
* Companies launching new products or receiving funding rounds
* Companies with visible technical debt, tech stack alignment, or engineering vacancies

Produces a dedicated pipeline: **"Companies You Should Approach"**

==================================================
REJECTION INTELLIGENCE ENGINE
=============================

A rejection is NOT the end of the workflow. When an application is rejected:
1. Record rejection details and timestamp.
2. Categorize outcome: `Skill mismatch`, `Experience mismatch`, `Location issue`, `Compensation issue`, `Timing issue`, `Competition`, `Unknown reason`.
3. Analyze feedback content using LLM reasoning.
4. Update candidate opportunity intelligence and matching rules.
5. Search for better-fit opportunities and similar companies.
6. Continue the career search pipeline.
7. CRITICAL: Never re-contact organizations or individuals that explicitly request opt-out or reject further contact.

==================================================
CONTINUOUS CAREER SEARCH
========================

The AI career agent works continuously in the background (e.g. daily/weekly automated schedules):
* Monday: 20 opportunities discovered
* Tuesday: 15 new opportunities
* Wednesday: 10 target companies identified
* Thursday: 3 new relevant decision-maker contacts
* Friday: 5 new verified opportunities

Users configure: Search frequency, job types, locations, target salary, industries, skills, company lists, and remote preferences.

==================================================
RELIABLE OPPORTUNITY SOURCE ENGINE (8 CATEGORIES)
=================================================

Searches across 8 distinct source categories:

CATEGORY 1 — PROFESSIONAL / CORPORATE EMPLOYMENT
* LinkedIn Jobs, Indeed, Glassdoor, ZipRecruiter
* Direct Applicant Tracking Systems: Greenhouse, Lever, Ashby, Workday, SmartRecruiters

CATEGORY 2 — REMOTE-FIRST OPPORTUNITIES
* We Work Remotely, Remote OK, Remotive, Remote.co, Working Nomads, Himalayas, Jobspresso, Dynamite Jobs, FlexJobs, Virtual Vocations, JustRemote
* Prioritizes candidates with explicit eligibility: Worldwide, Africa, Nigeria, International.

CATEGORY 3 — STARTUP / TECHNOLOGY
* Wellfound, Arc, Turing, Andela, Dice, Landing.jobs, Authentic Jobs, YC Jobs / Y Combinator network, Funded Startups.

CATEGORY 4 — FREELANCE / CLIENT ACQUISITION
* Upwork, Contra, Freelancer, Fiverr, PeoplePerHour, Guru, Toptal, 99designs, Hubstaff Talent, Outsourcely, Gun.io, Flexiple, Arc.

CATEGORY 5 — DIRECT COMPANY OPPORTUNITIES
* Direct company website scraper scanning `/careers`, `/jobs`, `/about` pages.

CATEGORY 6 — GITHUB / OPEN-SOURCE / TECH SIGNALS
* Public repositories, hiring repos, organization activity signals, technology stack disclosures.

CATEGORY 7 — COMMUNITY SOURCES
* Reddit (`/r/forhire`, `/r/jobbit`), Hacker News ("Who is hiring?"), Developer communities. Extracted, validated, and assigned confidence scores.

CATEGORY 8 — NIGERIA / AFRICA REGIONAL
* Jobberman, Andela, Turing, African-focused remote portals, verified Nigerian tech companies (Lagos, Abuja, remote).

==================================================
SOURCE RELIABILITY & OPPORTUNITY QUALITY SCORES
===============================================

Every opportunity is scored:

1. **Source Reliability Score (0–100)**:
   * Official Company Career Page: 98/100
   * Verified Job Platform: 90/100
   * Established Freelance Marketplace: 88/100
   * Professional Network: 85/100
   * Community Source: 65/100
   * Unverified Source: 30/100

2. **Opportunity Quality Score (0–100)**:
   Formula: `Source Reliability (20%) + Job Freshness (15%) + Company Verification (15%) + Candidate Match (20%) + Salary Transparency (10%) + Location Eligibility (10%) + Contact Quality (10%)`
   Display: `92/100 — HIGH QUALITY`

3. **Job Freshness Status**:
   * `OPEN`, `RECENT` (< 3 days), `AGING` (3-14 days), `EXPIRED`, `REMOVED`, `UNKNOWN`

==================================================
JOB VERIFICATION & ANTI-SCAM ENGINE
===================================

Safety Verification Protocol:
* Verify company domain, website, active job URL, and candidate location eligibility.
* Anti-Scam Detection Flags:
  * Upfront payment or processing fee demands
  * Cryptocurrency payment requests
  * Fake or mismatched company domains
  * Suspicious non-corporate email domains (@gmail, @yahoo for enterprise roles)
  * Unrealistic or impossible salary claims ($500/hr for entry level)
  * Missing company credentials or broken websites
* Safety Status Classification:
  `SAFE` | `REVIEW` | `HIGH RISK` | `REJECTED`
* Always present result as **"Verification Confidence Score"** rather than absolute 100% guarantee.

==================================================
DEDUPLICATION & SOURCE PRIORITY
===============================

When the same opportunity appears across multiple platforms (e.g. LinkedIn + Indeed + Company Site), merge into ONE opportunity record.
Priority order:
1. Official Company Careers Page
2. Direct Company Source
3. Verified Employment Platform
4. Professional Network
5. Established Freelance Marketplace
6. Community Source

Preserve all original source URLs in the unified record.

==================================================
TWO DISTINCT PIPELINES
======================

INDIVIDUAL EMPLOYMENT (Jobs):
Discovery → Verification → Matching → Application → Interview → Offer → Hired

INDIVIDUAL FREELANCE (Client Projects):
Discovery → Client Intelligence → Matching → Proposal → Outreach → Response → Contract → Client

Keep these pipelines strictly separated in the UI and workflow states!

==================================================
SOURCE ADAPTER ARCHITECTURE
===========================

All scrapers extend `SourceAdapter` with standard interface methods:
* `search()`
* `fetch()`
* `parse()`
* `normalize()`
* `validate()`
* `deduplicate()`
* `health_check()`

Fail-safe Isolation:
If a single adapter fails or encounters rate limits:
Do NOT break the discovery workflow.
Mark `SOURCE_FAILED` for that adapter and continue processing healthy sources.

==================================================
UI / VISUAL DESIGN & RESPONSIVE GLASS SYSTEM
============================================

Visual Aesthetic:
* Glassmorphic transparent panels with `backdrop-filter: blur(12px)`
* Dark theme background with subtle glowing accents
* Clean typography, responsive grid layouts, soft borders (`border-white/10`)
* WCAG AA contrast compliance and reduced-motion support

Branding (`EJICODE_AI`):
* Prominent, un-distorted **EJICODE_AI** logo brand asset across Landing, Login, Registration, Individual Dashboard, Enterprise Dashboard, and Navbars.

Individual Dashboard Layout:
* Hero KPI: **Hiring Progress** (Discovered, Matched, Applied, Responses, Interviews, Offers)
* Visual Pipeline: `Discovered` → `Matched` → `Applied` → `Contacted` → `Responded` → `Interview` → `Offer`
* Real-Time **AI Activity Center** streaming live agent updates (e.g. "✓ Discovery Agent found 14 opportunities", "✓ Extraction Agent verified 87 records", "⏳ Proposal Agent preparing 3 applications").

Enterprise Experience:
* Completely separate dashboard, permissions, analytics, and talent search pipeline.
