"""Unit tests for public statistics and individual candidate API endpoints."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-long!!")

from backend.app.main import app
from backend.app.dependencies import get_db
from backend.app.models.core import Base, User, UserProfile, Opportunity, Company, Contact, RejectionLog, FollowUpSchedule


@pytest.fixture
async def test_db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.fixture
def client(test_db_session):
    async def override_get_db():
        yield test_db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_public_statistics_endpoint(client):
    """Test public statistics returns real (never fabricated) metric counts,
    10 data sources, and 14 workflow stages. On a fresh database, the counts
    must be the true value of zero rather than a padded placeholder, and the
    computed rates must be None until there is real data to compute them from.
    """
    response = client.get("/v1/public/statistics")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "metrics" in data["data"]
    assert data["data"]["metrics"]["total_opportunities_indexed"] == 0
    assert data["data"]["metrics"]["total_companies_verified"] == 0
    assert data["data"]["metrics"]["contacts_discovered"] == 0
    assert data["data"]["metrics"]["rejection_recovery_rate"] is None
    assert data["data"]["metrics"]["data_extraction_accuracy"] is None
    assert data["data"]["metrics"]["active_sources_count"] == 10
    assert data["data"]["metrics"]["workflow_stages_count"] == 14
    assert len(data["data"]["sources"]) == 10
    assert len(data["data"]["workflow_stages"]) == 14


def test_individual_profile_and_dashboard_stats(client):
    """Test individual registration, profile retrieval, updates, resume parsing, and dashboard stats."""
    # Register individual user
    reg_payload = {
        "email": "alex.morgan@test.com",
        "password": "Password123!",
        "full_name": "Alex Morgan",
        "title": "Senior AI Software Engineer",
        "skills": ["Python", "FastAPI", "PostgreSQL", "LangChain"],
        "location": "London, UK",
        "remote_preference": "remote",
    }
    reg_res = client.post("/v1/auth/register/individual", json=reg_payload)
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get profile
    prof_res = client.get("/v1/individual/profile", headers=headers)
    assert prof_res.status_code == 200
    prof_data = prof_res.json()["profile"]
    assert prof_data["full_name"] == "Alex Morgan"
    assert prof_data["completion_percentage"] >= 50

    # Update profile
    update_payload = {
        "bio": "Specialized in distributed AI systems and autonomous agents.",
        "skills": ["Python", "FastAPI", "PostgreSQL", "LangChain", "Docker", "Kubernetes", "PyTorch"],
        "experience_years": 6.5,
        "salary_min": 120000,
        "salary_max": 180000,
        "career_goals": "Principal AI Engineer or Tech Lead",
    }
    put_res = client.put("/v1/individual/profile", json=update_payload, headers=headers)
    assert put_res.status_code == 200
    assert put_res.json()["status"] == "success"
    assert put_res.json()["completion_percentage"] >= 70

    # Parse resume
    resume_payload = {
        "resume_text": "Alex Morgan. 7 years experience building high-performance microservices and AI pipelines with Python, PyTorch, Docker, and Redis."
    }
    parse_res = client.post("/v1/individual/profile/resume-parse", json=resume_payload, headers=headers)
    assert parse_res.status_code == 200
    parse_data = parse_res.json()
    assert parse_data["status"] == "success"
    assert "extracted_skills" in parse_data

    # Check dashboard stats
    stats_res = client.get("/v1/individual/dashboard-stats", headers=headers)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()["data"]
    assert stats_data["profile_completion_percentage"] >= 70
    assert stats_data["candidate_name"] == "Alex Morgan"


@pytest.mark.asyncio
async def test_individual_matching_apply_and_rejection_recovery(client, test_db_session):
    """Test full career lifecycle: seed opportunity -> matching -> apply -> rejection recovery."""
    # Register candidate
    reg_payload = {
        "email": "dev.candidate@domain.com",
        "password": "Password123!",
        "full_name": "Dev Candidate",
        "title": "Backend Python Architect",
        "skills": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "location": "Remote",
    }
    reg_res = client.post("/v1/auth/register/individual", json=reg_payload)
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Seed company & opportunity in test DB
    company = Company(
        name="Apex AI Labs",
        domain="apexailabs.com",
        industry="Artificial Intelligence",
        location="Remote",
    )
    test_db_session.add(company)
    await test_db_session.commit()
    await test_db_session.refresh(company)

    opportunity = Opportunity(
        company_id=company.id,
        title="Senior Python Platform Engineer",
        type="full-time",
        location_type="remote",
        location="Remote",
        salary_min=130000,
        salary_max=170000,
        tech_required=["Python", "FastAPI", "Docker", "PostgreSQL"],
        status="new",
    )
    test_db_session.add(opportunity)
    await test_db_session.commit()
    await test_db_session.refresh(opportunity)

    # Trigger search & matching
    search_res = client.post("/v1/individual/search", headers=headers)
    assert search_res.status_code == 200
    assert search_res.json()["status"] == "success"
    assert search_res.json()["opportunities_evaluated"] >= 1

    # Fetch ranked matches
    matches_res = client.get("/v1/individual/matches?min_score=50", headers=headers)
    assert matches_res.status_code == 200
    matches = matches_res.json()["matches"]
    assert len(matches) >= 1
    assert matches[0]["score"] >= 60

    # Apply to opportunity (triggers outreach + 3/7/14 day follow-ups)
    opp_id = str(opportunity.id)
    apply_res = client.post("/v1/individual/apply", json={"opportunity_id": opp_id, "custom_note": "Great fit for my background"}, headers=headers)
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["status"] == "success"
    assert len(apply_data["follow_up_schedules"]) == 3  # Day 3, Day 7, Day 14

    # Rejection Recovery: Candidate receives rejection -> triggers continuous lookalike recovery
    rejection_payload = {
        "opportunity_id": opp_id,
        "rejection_reason": "Role filled internally, but your Python & distributed systems profile was strong.",
        "rejection_source": "recipient_reply",
    }
    reject_res = client.post("/v1/individual/rejections", json=rejection_payload, headers=headers)
    assert reject_res.status_code == 200
    reject_data = reject_res.json()
    assert reject_data["status"] == "success"
    assert len(reject_data["lookalike_companies"]) >= 2
    assert "feedback_analysis" in reject_data

    # Verify rejection history endpoint
    hist_res = client.get("/v1/individual/rejections", headers=headers)
    assert hist_res.status_code == 200
    history = hist_res.json()["rejections"]
    assert len(history) == 1
    assert len(history[0]["lookalike_companies"]) >= 2
