# Ejicode AI Product TODO

This list captures what needs to be done to move the project from scaffold/prototype to a working product. Treat the first section as the stabilization gate: do those before adding more features.

## P0 - Stabilize The Repository

- [ ] Normalize line endings to LF across the repo.
- [ ] Remove trailing whitespace across source, docs, config, and tests.
- [ ] Restore `.github/workflows/ci.yml` or create a new CI workflow.
- [ ] Reduce the massive working-tree churn so real code changes are reviewable.
- [ ] Decide whether the current modified files are intentional or accidental formatting changes.
- [ ] Add `.gitattributes` to enforce LF line endings for Python, TypeScript, YAML, SQL, Dockerfiles, Makefile, and Markdown.
- [ ] Remove or isolate temporary files such as `temp_pdf_extract.py` if no longer needed.
- [ ] Make `git diff --check` pass.

## P0 - Make The Project Boot

- [ ] Install or document Python dependency setup clearly.
- [ ] Add a reproducible Python environment path, such as `venv`, `pip-tools`, Poetry, or uv.
- [ ] Verify `python3 -m pytest -q` runs locally.
- [ ] Verify `python3 -m compileall backend agents` continues to pass.
- [ ] Install or document Node.js/npm requirements.
- [ ] Add `frontend/package-lock.json` or change the frontend Docker build away from `npm ci`.
- [ ] Verify `npm install` or `npm ci` works in `frontend/`.
- [ ] Verify `npm run build` works in `frontend/`.
- [ ] Verify `docker-compose build` works.
- [ ] Verify `docker-compose up` starts all required services.
- [ ] Add a single trusted quickstart path that actually works.

## P0 - Backend Runtime Fixes

- [ ] Fix `backend/app/database.py` to use SQLAlchemy `text("SELECT 1")`.
- [ ] Move `Base = declarative_base()` above any model import risk, or restructure database/model imports safely.
- [ ] Fix `backend/app/models/core.py`; it currently imports model classes from itself.
- [ ] Move ORM model definitions out of `backend/app/models/__init__.py` into `core.py`, or make `core.py` the canonical model module.
- [ ] Remove unused imports such as `event`, `UniqueConstraint`, and `Index` where appropriate.
- [ ] Ensure `backend.app.models` imports cleanly after dependencies are installed.
- [ ] Ensure `backend.app.main:app` imports cleanly.
- [ ] Make `/health` check real service connectivity instead of returning hardcoded values.
- [ ] Ensure startup does not create tables in production without migrations.
- [ ] Add proper shutdown cleanup with `close_db()`.

## P0 - Database And Migrations

- [ ] Add an `alembic.ini`.
- [ ] Add real Alembic revision files under `database/migrations/versions/`.
- [ ] Ensure migrations reflect the current ORM models.
- [ ] Decide whether `database/schema.sql` or Alembic is the source of truth.
- [ ] Remove the dependency on `CREATE EXTENSION vector` unless the Postgres image includes pgvector.
- [ ] Align ORM column types with SQL schema, especially dates and JSON/JSONB fields.
- [ ] Add indexes and constraints in migrations, not only in `schema.sql`.
- [ ] Add seed data for local development.
- [ ] Add a safe database reset/dev seed command.

## P0 - Authentication Contract

- [ ] Decide how the frontend authenticates users.
- [ ] Add a login page or remove auth from dashboard routes during local demo mode.
- [ ] Forward JWT tokens from Next API routes to FastAPI.
- [ ] Stop calling protected backend routes without `Authorization` headers.
- [ ] Add token refresh handling.
- [ ] Replace dev username/password auth before production.
- [ ] Hash stored passwords if real users are introduced.
- [ ] Add auth tests for protected API routes.

## P0 - Frontend Build Fixes

- [ ] Add `'use client'` to pages that use `useSWR`.
- [ ] Or convert pages to server components with server-side fetching.
- [ ] Fix all frontend API routes to handle backend errors gracefully.
- [ ] Avoid assuming backend error responses are valid successful JSON payloads.
- [ ] Add TypeScript types for dashboard, companies, contacts, and opportunities.
- [ ] Remove `any` usage in page rendering loops.
- [ ] Add loading states.
- [ ] Add empty states.
- [ ] Add error states with retry actions.
- [ ] Verify mobile layout.
- [ ] Verify desktop layout.

## P1 - Backend API Completeness

- [ ] Add create/list/detail/update flows consistently for companies.
- [ ] Add create/list/detail/update flows consistently for opportunities.
- [ ] Add create/list/detail/update flows consistently for contacts.
- [ ] Add proposal list/detail endpoints.
- [ ] Add outreach list/detail endpoints.
- [ ] Add agent run list/detail endpoints.
- [ ] Use shared Pydantic schemas instead of defining response models inside routers.
- [ ] Add request validation for status fields and enum-like values.
- [ ] Add pagination metadata.
- [ ] Add filtering and sorting for companies, contacts, opportunities, proposals, and outreach.
- [ ] Add consistent error response shape.
- [ ] Add API tests for all routers.

## P1 - Agent Workflow

- [ ] Fix supervisor state handling so outputs from each agent are preserved.
- [ ] Ensure Job Scout opportunities are not lost after Company Scout runs.
- [ ] Pass the correct opportunity list into Ranking Agent.
- [ ] Pass real company domain/company data into Research Agent.
- [ ] Persist discovered companies to the database.
- [ ] Persist discovered opportunities to the database.
- [ ] Persist research reports to the database.
- [ ] Persist discovered contacts to the database.
- [ ] Persist agent run status, timestamps, counts, and errors.
- [ ] Add retry behavior around failing agents.
- [ ] Add partial-success behavior when one scraper or agent fails.
- [ ] Add idempotency/deduplication keys for repeated daily runs.
- [ ] Add agent workflow tests without requiring live internet or Ollama.

## P1 - AI Engineering Work

- [ ] Replace hardcoded Research Agent analysis with real Ollama calls.
- [ ] Add structured LLM output parsing and validation.
- [ ] Add prompt templates for research, ranking, contact analysis, and proposal generation.
- [ ] Add model timeout handling.
- [ ] Add model unavailable fallback behavior.
- [ ] Add deterministic tests using mocked LLM responses.
- [ ] Track model name, prompt version, latency, and token-like usage where possible.
- [ ] Add quality gates for generated proposals.
- [ ] Add hallucination checks for company research summaries.
- [ ] Add confidence scoring based on real evidence, not static values.

## P1 - RAG And Knowledge Base

- [ ] Implement real ChromaDB client operations in `ChromaDBTool`.
- [ ] Create named collections for company research, Ejicode profile, case studies, and outreach history.
- [ ] Add embedding generation using the configured embedding model.
- [ ] Add document chunking.
- [ ] Add metadata filters.
- [ ] Add retrieval tests.
- [ ] Add RAG context into proposal generation.
- [ ] Persist embedding IDs on research reports or source documents.
- [ ] Add rebuild/reindex command.

## P1 - Scrapers And Discovery

- [ ] Replace demo RemoteOK parsing with robust API handling.
- [ ] Add source adapters for all intended platforms.
- [ ] Respect robots.txt, platform terms, and rate limits.
- [ ] Add retries with backoff.
- [ ] Add user-agent configuration.
- [ ] Add per-source timeout configuration.
- [ ] Add normalized opportunity schema.
- [ ] Add normalized company schema.
- [ ] Add deduplication by URL, company domain, title, and source.
- [ ] Add tests using saved fixtures.
- [ ] Avoid live network calls in unit tests.

## P1 - Celery And Background Jobs

- [ ] Register Celery tasks consistently.
- [ ] Remove duplicate or conflicting task definitions.
- [ ] Ensure scheduled task names match actual task functions.
- [ ] Add task result tracking in `agent_runs`.
- [ ] Add queues for discovery, research, proposals, outreach, and reporting.
- [ ] Add task retry policies.
- [ ] Add dead-letter/error handling strategy.
- [ ] Add Celery worker health checks.
- [ ] Add beat schedule documentation.

## P1 - Outreach Pipeline

- [ ] Keep automated outreach disabled by default.
- [ ] Require human approval before sending emails.
- [ ] Add proposal review UI.
- [ ] Add approve/reject/edit proposal workflow.
- [ ] Add SMTP send integration tests with mocks.
- [ ] Add daily send limit enforcement.
- [ ] Add per-contact cooldowns.
- [ ] Add unsubscribe/suppression list.
- [ ] Add bounce handling.
- [ ] Add reply monitoring with IMAP integration.
- [ ] Add follow-up scheduling.
- [ ] Add audit trail for every sent message.

## P1 - Frontend Product Experience

- [ ] Build a real login screen.
- [ ] Build dashboard summary connected to real data.
- [ ] Build companies table with search, filters, status, and fit score.
- [ ] Build company detail page with research reports, contacts, and opportunities.
- [ ] Build opportunities table with ranking and status workflow.
- [ ] Build opportunity detail page.
- [ ] Build contacts table and contact detail page.
- [ ] Build proposal queue.
- [ ] Build proposal editor/reviewer.
- [ ] Build outreach history screen.
- [ ] Build agent runs/monitoring screen.
- [ ] Add navigation active state.
- [ ] Add responsive mobile navigation.
- [ ] Add accessible form controls.
- [ ] Add consistent visual system.

## P2 - Observability

- [ ] Add structured logging.
- [ ] Add request IDs.
- [ ] Add agent run IDs across logs and database records.
- [ ] Avoid unbounded Prometheus labels such as raw request paths with IDs.
- [ ] Add metrics for agent success/failure/duration.
- [ ] Add metrics for discovered leads, proposals generated, emails sent, replies received.
- [ ] Add dashboard panels for Prometheus/Grafana.
- [ ] Add alerting thresholds.
- [ ] Add health checks for Postgres, Redis, Ollama, ChromaDB, Celery, and frontend.

## P2 - Security And Compliance

- [ ] Replace hardcoded Docker Compose passwords.
- [ ] Remove development secrets from committed config.
- [ ] Add secret management documentation.
- [ ] Restrict CORS in non-dev environments.
- [ ] Add rate limiting backed by Redis for multi-worker deployments.
- [ ] Add input sanitization where user content is rendered or emailed.
- [ ] Add SSRF protections for website scraping.
- [ ] Add allowlist/denylist controls for scraped domains.
- [ ] Add audit logs for auth, proposal approval, and email sending.
- [ ] Add data retention policy.
- [ ] Add privacy review for contact discovery and outreach.

## P2 - Testing Strategy

- [ ] Add unit tests for config loading.
- [ ] Add unit tests for security/token logic.
- [ ] Add API tests for every router.
- [ ] Add database integration tests.
- [ ] Add Celery task tests in eager mode.
- [ ] Add agent unit tests with mocked tools.
- [ ] Add scraper fixture tests.
- [ ] Add frontend component tests or Playwright smoke tests.
- [ ] Add Docker build test in CI.
- [ ] Add lint and format checks in CI.
- [ ] Add coverage reporting.

## P2 - Documentation

- [ ] Update README to reflect the real current state.
- [ ] Remove outdated phase-complete claims or mark them as aspirational.
- [ ] Add local development setup.
- [ ] Add Docker setup.
- [ ] Add environment variable reference.
- [ ] Add architecture diagram or concise architecture doc.
- [ ] Add API usage examples.
- [ ] Add agent workflow documentation.
- [ ] Add deployment guide.
- [ ] Add troubleshooting guide.

## P2 - Deployment Readiness

- [ ] Split development and production Docker Compose files.
- [ ] Add production-ready Dockerfiles.
- [ ] Add non-root users in containers.
- [ ] Add image health checks.
- [ ] Add environment-specific config.
- [ ] Add database backup/restore plan.
- [ ] Add migration run step.
- [ ] Add reverse proxy/TLS plan.
- [ ] Add resource sizing for Ollama models.
- [ ] Add deployment smoke tests.

## Product Milestones

- [ ] Milestone 1: Repo is clean, CI restored, backend/frontend build locally.
- [ ] Milestone 2: Authenticated dashboard shows real database counts.
- [ ] Milestone 3: CRUD works for companies, contacts, and opportunities.
- [ ] Milestone 4: Daily discovery persists real leads into Postgres.
- [ ] Milestone 5: Ranking and research produce stored reports with evidence.
- [ ] Milestone 6: Proposal generation uses RAG and requires human approval.
- [ ] Milestone 7: Outreach sends approved emails and tracks history.
- [ ] Milestone 8: Reply monitoring and follow-up workflow work.
- [ ] Milestone 9: Product is deployable with monitoring and backups.
