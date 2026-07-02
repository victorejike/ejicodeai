# Implementation Roadmap — Ejicode AI BDP

## Phase 1 — Foundation (Weeks 1–3) ✅ IN PROGRESS

### Completed
- [x] PostgreSQL schema with 11 core tables
- [x] FastAPI skeleton with config management
- [x] Pydantic v2 models and schemas
- [x] Redis + Celery configuration
- [x] ChromaDB vector store setup
- [x] Docker Compose (development)
- [x] Project folder structure
- [x] Environment configuration template
- [x] Database migration setup (Alembic)

### Remaining
- [ ] Database connection testing
- [ ] API route stubs implementation
- [ ] Authentication middleware (JWT)
- [ ] Celery worker configuration
- [ ] Ollama model downloading
- [ ] Initial logging setup
- [ ] Health check endpoints

**Deadline**: Week 3

---

## Phase 2 — Core Agents (Weeks 4–7)

### Job Scout Agent
- [ ] Web scraping setup (Playwright + BeautifulSoup)
- [ ] RemoteOK scraper
- [ ] WeWorkRemotely scraper
- [ ] LinkedIn jobs scraper
- [ ] HackerNews "Who Is Hiring" parser
- [ ] Opportunity deduplication (Bloom filter)
- [ ] Tech stack extraction
- [ ] Data validation

### Supervisor Agent
- [ ] LangGraph supervisor graph
- [ ] Agent routing logic
- [ ] State management
- [ ] Error recovery with retries
- [ ] Escalation workflow

### Opportunity Ranking Agent
- [ ] Scoring rubric implementation (0-100)
- [ ] Technology matching (25 pts)
- [ ] Company fit calculation (20 pts)
- [ ] Historical win rate analysis
- [ ] Redis priority queue
- [ ] Score explanation generation

### Research Agent
- [ ] Website scraping & parsing
- [ ] Tech stack detection (StackShare, Wappalyzer)
- [ ] Company intelligence analysis (DeepSeek-R1)
- [ ] ChromaDB embedding & storage
- [ ] Report generation

**Deadline**: Week 7

---

## Phase 3 — Outreach Pipeline (Weeks 8–10)

### Contact Discovery Agent
- [ ] Hunter.io integration (free tier)
- [ ] Email pattern generation
- [ ] SMTP validation
- [ ] LinkedIn profile scraping
- [ ] Website email extraction

### Proposal Generation Agent
- [ ] RAG retrieval from ChromaDB
- [ ] DeepSeek-R1 reasoning pass
- [ ] Llama 3.1 refinement pass
- [ ] Cold email template
- [ ] Cover letter generation
- [ ] Brand voice consistency

### Outreach Agent
- [ ] SMTP send implementation
- [ ] Email tracking pixels
- [ ] Bounce handling
- [ ] Rate limiting (50/day)
- [ ] Delivery status tracking

### Follow-Up Agent
- [ ] IMAP polling
- [ ] Reply classification (LLM)
- [ ] Auto-response detection
- [ ] Follow-up sequencing
- [ ] Escalation to human

**Deadline**: Week 10

---

## Phase 4 — Frontend Dashboard (Weeks 11–13)

### Pages
- [ ] Overview dashboard
- [ ] Opportunities (Kanban + table views)
- [ ] Companies (enriched profiles)
- [ ] Contacts (searchable directory)
- [ ] Outreach (timeline view)
- [ ] Reports (rendered markdown)
- [ ] Analytics (funnel, trends)
- [ ] Settings (configuration)

### Components
- [ ] API client (fetch wrapper)
- [ ] WebSocket real-time updates
- [ ] Data tables (TanStack Table)
- [ ] Charts (Recharts)
- [ ] Forms (React Hook Form)
- [ ] Modals & Dialogs

**Deadline**: Week 13

---

## Phase 5 — Production Hardening (Weeks 14–16)

### Monitoring & Observability
- [x] Prometheus metrics
- [ ] Grafana dashboards
- [ ] Loki log aggregation
- [ ] APScheduler health checks
- [ ] Alert rules

### Security
- [x] JWT authentication
- [x] Role-based access control (RBAC)
- [x] Rate limiting middleware
- [ ] Data encryption (at rest, in transit)
- [ ] DKIM/SPF email signing
- [ ] GDPR compliance (PII export)

### DevOps
- [x] GitHub Actions CI/CD pipeline
- [x] Automated testing (pytest)
- [ ] Code coverage reporting
- [ ] Database backup automation
- [ ] Disaster recovery plan

### Documentation
- [ ] API reference (auto-generated from OpenAPI)
- [ ] Agent playbooks (per-agent runbooks)
- [ ] Deployment guide
- [ ] Security audit checklist

**Deadline**: Week 16

---

## Phase 6 — Scale & Enterprise Readiness (Weeks 17–20)

### Scalability
- [ ] Multi-tenant architecture
- [ ] Horizontal agent fleet orchestration
- [ ] Autoscaling deployment templates
- [ ] Distributed caching for state and embeddings
- [ ] Database partitioning and read replicas

### Resilience
- [ ] Graceful shutdown and retry policies
- [ ] Circuit breakers for third-party APIs
- [ ] Disaster recovery playbook
- [ ] Backup and restore automation
- [ ] Canary deployment strategy

### Availability
- [ ] High-availability deployment on Kubernetes or managed cloud
- [ ] Service mesh / ingress routing
- [ ] Health checks and readiness probes
- [ ] Load testing and capacity planning

### Enterprise
- [ ] Advanced RBAC and audit logging
- [ ] Tenant isolation and data governance
- [ ] SLA monitoring and alerts
- [ ] Compliance documentation for security and privacy

**Deadline**: Week 20

---

## Scaling Roadmap

| Stage | Timeline | Targets | Infrastructure |
|-------|----------|---------|-----------------|
| Solo | Now | 50 opp/day | Single VPS |
| Small Team | 3 mo | 500 opp/day | Separate Ollama VPS |
| Growing | 12 mo | 2K opp/day | K3s cluster |
| Enterprise | 18 mo | 10K+ opp/day | Multi-tenant |

---

## Critical Path Items

1. **Database** → Migrations, schema validation
2. **FastAPI core** → Authentication, error handling
3. **Job Scout** → First discovery agent
4. **Supervisor** → Agent orchestration
5. **Frontend** → Dashboard UI
6. **Production hardening** → Monitoring, security

---

## Next Immediate Action

→ Start Phase 2: Implement Job Scout Agent + Supervisor Graph
