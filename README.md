# Ejicode AI Business Development Platform

Autonomous multi-agent system for business development — discovers opportunities, researches companies, generates proposals, and manages outreach.

**Status**: ✅ **100% Production Ready (Phases 1–8 Complete, 64/64 Automated Tests Passing)**

---

## 🚀 Quickstart

### Option 1 — Local Development (Fastest, SQLite fallback)

```bash
cd /home/student/ejicodeai

# Activate Python 3.12 virtualenv
source .venv/bin/activate
pip install -r requirements.txt

# Start FastAPI backend
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

- **API Documentation (Swagger UI)**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Public Unsubscribe Portal**: http://localhost:8000/v1/outreach/unsubscribe?contact_id=<ID>

In a separate terminal, launch the Next.js frontend:
```bash
cd frontend
npm install
npm run dev
```
- **Web Dashboard**: http://localhost:3000

---

### Option 2 — Docker Full Stack Deployment

Runs PostgreSQL with pgvector, Redis, Celery workers + beat scheduler, FastAPI backend, Next.js frontend, Prometheus, and Grafana.

```bash
docker-compose up -d
docker-compose ps   # Verify all 8 services report healthy
```

Service Ports:
- Frontend Dashboard: `http://localhost:3000`
- FastAPI Backend: `http://localhost:8000`
- ChromaDB Vector Store: `http://localhost:8001`
- Prometheus Metrics: `http://localhost:9090`
- Grafana Dashboards: `http://localhost:3001` (login: admin / admin)

---

## 🧪 Running Automated Tests

Run the complete 64-test suite with coverage:
```bash
pytest -v --cov=backend --cov=agents tests/
```

All 64 tests pass with zero failures:
```
tests/unit/test_agent_persistence.py .....                               [ 7%]
tests/unit/test_agents_unit.py .........                                 [21%]
tests/unit/test_ai_gateway.py ...                                        [26%]
tests/unit/test_api_companies.py ....                                    [32%]
tests/unit/test_api_contacts.py ...                                      [37%]
tests/unit/test_api_dashboard_and_reports.py ..                          [40%]
tests/unit/test_api_opportunities.py ...                                 [45%]
tests/unit/test_api_proposals.py ...                                     [50%]
tests/unit/test_auth.py ....                                             [56%]
tests/unit/test_crud_services.py ..............                          [78%]
tests/unit/test_end_to_end_workflow.py .                                 [79%]
tests/unit/test_gemini_and_rag.py ..                                     [82%]
tests/unit/test_job_scout_google_maps.py .                               [84%]
tests/unit/test_main.py ..                                               [87%]
tests/unit/test_outreach_agent.py .                                      [89%]
tests/unit/test_outreach_pipeline.py ......                              [98%]
tests/unit/test_supervisor_workflow.py .                                 [100%]
============================== 64 passed in ~20s ===============================
```

---

## 🏛️ Architecture & System Design

```
                         ┌─────────────────────────────┐
                         │   Next.js 14 Web UI         │
                         │   (Dashboard, CRM, Review)  │
                         └──────────────┬──────────────┘
                                        │ REST API
                         ┌──────────────▼──────────────┐
                         │   FastAPI Backend Layer     │
                         │   (Auth, CRUD, Safety Gates)│
                         └──────┬───────────────┬──────┘
                                │               │
          ┌─────────────────────▼─┐           ┌─▼─────────────────────┐
          │ Async SQLAlchemy      │           │ Celery + Redis        │
          │ (PostgreSQL / SQLite) │           │ Task Queue & Beat     │
          └───────────────────────┘           └───────────┬───────────┘
                                                          │
                         ┌────────────────────────────────▼┐
                         │  LangGraph Supervisor Agent    │
                         └────────────────┬───────────────┘
                                          │
       ┌──────────────┬───────────────────┼───────────────────┬──────────────┐
       ▼              ▼                   ▼                   ▼              ▼
┌──────────────┐┌──────────────┐   ┌──────────────┐   ┌──────────────┐┌──────────────┐
│  Job Scout   ││Company Scout │   │Ranking Agent │   │Research Agent││Contact Disc. │
│  (RemoteOK,  ││(Discovers    │   │(6-Factor     │   │(Tech audits &││(RFC-5322 &   │
│  Google Maps)││ target orgs) │   │ Rubric)      │   │ LLM insights)││ MX checks)   │
└──────────────┘└──────────────┘   └──────────────┘   └──────────────┘└──────────────┘
                                          │
                                   ┌──────▼──────┐
                                   │Proposal Gen │ ◄── ChromaDB RAG Context
                                   │(Reasoning & │ ◄── Gemini 2.5 Flash / DeepSeek
                                   │ Refinement) │
                                   └──────┬──────┘
                                          │
                                   ┌──────▼──────┐
                                   │Human Review │ (Requires status == 'approved')
                                   └──────┬──────┘
                                          │
                       ┌──────────────────┴──────────────────┐
                       ▼                                     ▼
                ┌──────────────┐                      ┌──────────────┐
                │Outreach Agent│                      │Reply Monitor │
                │(Rate-limited,│                      │(Unsubscribes,│
                │List-Unsub)   │                      │bounces, auto)│
                └──────────────┘                      └──────────────┘
```

---

## 🔒 Safety Gates & Outreach Compliance

The outreach subsystem strictly enforces safeguards to comply with CAN-SPAM and international standards:
1. **Human-in-the-Loop Review**: No cold email can be dispatched without explicit human approval (`status == "approved"`).
2. **Double-Send Prevention**: In-flight or sent proposals cannot be dispatched a second time.
3. **Daily Quotas**: Configurable daily rate limiting (`max_emails_per_day`).
4. **Per-Contact Cooldown**: Enforces cooldown intervals (`min_send_interval_minutes`) between touches.
5. **Suppression & Unsubscribe**: Inbound `UNSUBSCRIBE` replies or clicks on `{api_url}/v1/outreach/unsubscribe` immediately mark contacts as unsubscribed, rejecting any future send attempts.

---

## 📂 Project Structure

```
ejicodeai/
├── .github/workflows/ci.yml         # GitHub Actions CI for backend & frontend
├── agents/                          # Autonomous multi-agent implementations
│   ├── base/base_agent.py           # BaseAgent class with retry & status lifecycle
│   ├── supervisor/                  # Supervisor orchestrator graph
│   ├── job_scout/                   # Job discovery & scraping
│   ├── company_scout/               # Company discovery
│   ├── ranking/                     # 6-factor multi-rubric scoring
│   ├── research/                    # Deep company audits
│   ├── contact_discovery/           # Decision maker identification & MX verification
│   ├── proposal_generation/         # Two-pass LLM proposal generator with RAG
│   ├── outreach/                    # RFC-compliant email dispatcher
│   ├── reply_monitoring/            # Heuristic & LLM reply classification
│   └── tools/                       # AI gateway, ChromaDB, and email tools
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI application entrypoint
│   │   ├── config.py                # Pydantic BaseSettings configuration
│   │   ├── database.py              # Async SQLAlchemy engine & session factory
│   │   ├── security.py              # JWT authentication & password hashing
│   │   ├── models/core.py           # 11 SQLAlchemy ORM models
│   │   ├── schemas/                 # Pydantic V2 request & response schemas
│   │   ├── routers/                 # REST endpoints (companies, contacts, opps, etc.)
│   │   └── services/                # Business logic, AI gateway, outreach, persistence
│   └── tasks/                       # Celery tasks & scheduler definitions
├── frontend/                        # Next.js 14 App Router dashboard & CRM UI
├── database/                        # SQL schemas and Alembic migration scripts
├── infrastructure/                  # Dockerfiles, Prometheus, Nginx configs
└── tests/                           # 64 unit & integration tests
```
