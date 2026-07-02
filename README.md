# Ejicode AI Business Development Platform

Autonomous multi-agent system for business development — discovers opportunities, researches companies, generates proposals, and manages outreach.

**Status**: Phase 1 & 2 complete (40%). Phases 3–5 in progress.

---





## How to Run

### Option 1 — Local (fastest, no Docker)

Uses SQLite. No external services needed.

```bash
cd /home/student/Ejicode-Ai

python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

cp .env.example .env

export PYTHONPATH=.
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Open:
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

Login at `POST /v1/auth/login` with `admin` / `admin`.

---

### Option 2 — Docker (full stack)

Runs PostgreSQL, Redis, Ollama, ChromaDB, Celery, Frontend, Prometheus, Grafana.

```bash
cp .env.example .env
docker-compose up -d
docker-compose ps   # verify all services are healthy
```

First time only — pull AI models (~20 GB):

```bash
docker-compose exec ollama ollama pull deepseek-r1:8b
docker-compose exec ollama ollama pull llama2:7b
docker-compose exec ollama ollama pull mistral:7b
docker-compose exec ollama ollama pull qwen2.5-coder:7b
docker-compose exec ollama ollama pull nomic-embed-text:latest
```


---

## Run Tests

```bash
export PYTHONPATH=.
pytest -q tests/unit/test_main.py tests/unit/test_auth.py
```

---

## Architecture

- **Backend API**: FastAPI + Python 3.12 (async)
- **Database**: PostgreSQL 16 + SQLite (dev fallback)
- **Cache / Queue**: Redis 7 + Celery + Beat
- **AI Models**: Ollama (local, open-source — zero inference cost)
- **Vector Store**: ChromaDB
- **Multi-Agent**: LangGraph orchestration
- **Frontend**: Next.js 14 + TailwindCSS
- **Monitoring**: Prometheus + Grafana

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI entry point
│   │   ├── config.py        # Settings (pydantic-settings)
│   │   ├── database.py      # Async SQLAlchemy engine
│   │   ├── security.py      # JWT auth
│   │   ├── dependencies.py  # get_db session dependency
│   │   ├── models/          # SQLAlchemy ORM (11 tables)
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   ├── routers/         # API route handlers
│   │   └── services/        # Business logic
│   └── tasks/               # Celery tasks
│
├── agents/
│   ├── base/                # BaseAgent + AgentState
│   ├── supervisor/          # Orchestrator
│   ├── job_scout/           # Job discovery
│   ├── company_scout/       # Company discovery
│   ├── research/            # Deep company analysis
│   ├── ranking/             # 6-factor scoring
│   ├── contact_discovery/   # Email finding + validation
│   ├── knowledge_base/      # RAG / ChromaDB management
│   ├── proposal_generation/ # LLM proposal writer
│   ├── outreach/            # SMTP sending
│   ├── reply_monitoring/    # IMAP reply tracking
│   └── tools/               # LLM, ChromaDB, email tools
│
├── frontend/                # Next.js 14 UI
├── database/
│   ├── schema.sql           # Reference schema
│   └── migrations/          # Alembic migrations
├── infrastructure/
│   ├── docker/              # Dockerfiles
│   ├── nginx/               # Reverse proxy config
│   ├── monitoring/          # Prometheus config
│   └── scripts/             # Helper scripts
└── tests/
    └── unit/
```

---


## 

---

## Development Commands

```bash
# Run migrations
python -m alembic upgrade head

# Run Celery worker
celery -A backend.tasks.celery_app worker -l info

# Run Celery beat scheduler
celery -A backend.tasks.celery_app beat -l info

# Lint
flake8 backend agents
black --check backend agents
```

---

## Known Issues Fixed

- `GUID.load_dialect_impl` was calling itself recursively — fixed to use `PG_UUID()`
- `companies_crud.py` referenced `get_db_session` which doesn't exist — fixed to `get_db`
- `crud_service.py` referenced `Opportunity.source` (wrong column) — fixed to `source_platform`
- `crud_service.py` referenced `Proposal.company_id` (column doesn't exist on ORM model) — removed
- `agent_persistence_service.py` same `Opportunity.source` bug — fixed

---

## Phase Checklist

- [x] Phase 1: Foundation (DB, FastAPI, Redis, Celery, Docker)
- [x] Phase 2: Core Agents (Job Scout, Company Scout, Research, Ranking, Contact Discovery, Knowledge Base, Supervisor)
- [ ] Phase 3: Outreach Pipeline (Proposal generation, SMTP sending, reply monitoring, follow-up)
- [ ] Phase 4: Frontend Dashboard (Login, real data tables, proposal reviewer, agent monitor)
- [ ] Phase 5: Production Hardening (Security audit, structured logging, alerting, deployment guides)

See [docs/implementation-roadmap.md](docs/implementation-roadmap.md) for the full plan.
