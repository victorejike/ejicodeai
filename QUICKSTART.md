# Ejicode AI - Local Development Quickstart

This guide will help you set up and run the Ejicode AI Business Development Platform locally.

## Prerequisites

- **Python 3.12+** (with `pip` and `venv`)
- **Node.js 20+** and **npm**
- **Docker** and **Docker Compose** (optional, for full stack)
- **PostgreSQL 16** (or use Docker)
- **Redis 7** (or use Docker)

## Option 1: Local Python + SQLite Development (Fastest)

### 1. Set up Python environment

```bash
# Create virtual environment
python3.12 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip

# Install dependencies
pip install -r requirements.txt
```

### 2. Initialize the database

```bash
# Run migrations (creates SQLite database)
alembic upgrade head

# Or manually initialize (for development)
python -c "from backend.app.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 3. Start the backend

```bash
# Set environment variables (optional, defaults are configured)
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
export REDIS_URL="redis://localhost:6379/0"

# Start backend server
uvicorn backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend will be available at: **http://localhost:8000**  
API documentation at: **http://localhost:8000/docs**

### 4. Set up frontend (in another terminal)

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

Frontend will be available at: **http://localhost:3000**

---

## Option 2: Full Docker Compose Stack (Complete)

### 1. Set up environment

```bash
# Copy example environment
cp .env.example .env

# Create data directories
mkdir -p data/{postgres,redis,ollama,chroma}
```

### 2. Start all services

```bash
# Build and start all services
docker-compose up -d

# Wait for services to be healthy (check logs)
docker-compose logs -f

# Initialize database
docker-compose exec backend alembic upgrade head
```

### 3. Access services

| Service | URL |
|---------|-----|
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Frontend | http://localhost:3000 |
| Grafana | http://localhost:3001 (admin/admin) |
| Prometheus | http://localhost:9090 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |
| Ollama | http://localhost:11434 |

---

## Verification Checklist

### Backend

```bash
# Test imports
python -c "from backend.app import main; print('✓ Backend imports')"

# Run tests
pytest -v tests/unit/

# Check API health
curl http://localhost:8000/health
```

Expected output:
```json
{
  "status": "ok",
  "service": "backend",
  "environment": "development",
  "database": "ok"
}
```

### Frontend

```bash
# Build frontend
cd frontend
npm run build

# Start development
npm run dev
```

---

## Database Management

### Alembic Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new table"

# Run pending migrations
alembic upgrade head

# Rollback last migration
alembic downgrade -1
```

---

## Common Issues

### 1. Port Already in Use

```bash
# Find and kill process using port 8000
lsof -i :8000
kill -9 <PID>

# Or change port
uvicorn backend.app.main:app --port 8001
```

### 2. Database Connection Error

```bash
# Check SQLite database exists
ls -la dev.db

# Reset database
rm dev.db
python -c "from backend.app.database import init_db; import asyncio; asyncio.run(init_db())"
```

### 3. Module Import Error

```bash
# Ensure virtual environment is activated
source .venv/bin/activate

# Reinstall requirements
pip install -r requirements.txt --force-reinstall
```

### 4. Frontend npm issues

```bash
# Clear npm cache
npm cache clean --force

# Remove node_modules and reinstall
rm -rf node_modules package-lock.json
npm install
```

---

## Development Workflows

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/unit/test_crud_services.py -v

# Run with coverage
pytest --cov=backend --cov-report=html tests/
```

### Code Quality

```bash
# Format code
black backend/ agents/

# Sort imports
isort backend/ agents/

# Lint
flake8 backend/ agents/

# Type checking
mypy backend/
```

---

## Environment Variables

Create a `.env` file or set these:

```bash
# Database
DATABASE_URL=sqlite+aiosqlite:///./dev.db
REDIS_URL=redis://localhost:6379/0

# API
API_URL=http://localhost:8000
DEBUG=True
SECRET_KEY=dev-secret-key-change-in-production

# Features
ENABLE_PROPOSAL_AUTO_GENERATION=True
ENABLE_AUTOMATED_OUTREACH=False
ENABLE_REPLY_MONITORING=False

# Logging
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_MAX_REQUESTS=200
RATE_LIMIT_WINDOW_SECONDS=60
```

---

## Next Steps

1. **Explore API Documentation**: Visit http://localhost:8000/docs
2. **Read Architecture**: See `/docs/ARCHITECTURE_BLUEPRINT_v1.0.md`
3. **Agent Playbooks**: See `/docs/agent-playbooks.md`
