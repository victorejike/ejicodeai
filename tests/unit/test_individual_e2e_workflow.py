"""End-to-end workflow test for the Individual Candidate journey.

Verifies:
1. Candidate Registration -> Authentication & JWT validation
2. Profile onboarding & Resume parsing extraction
3. AI 6-Factor Opportunity Matching & Score explanation
4. Application submission -> Outreach record & 3-Touch Follow-up Sequence scheduling (Days 3, 7, 14)
5. Rejection handling -> Autonomous Rejection Recovery (feedback analysis, lookalike discovery, alternate contacts)
6. Comprehensive Dashboard telemetry updating in real-time
"""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-long!!")

from backend.app.main import app
from backend.app.dependencies import get_db
from backend.app.models.core import (
    Base,
    Company,
    Contact,
    Opportunity,
    OutreachHistory,
    FollowUpSchedule,
    RejectionLog,
    User,
    UserProfile,
)


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


@pytest.mark.asyncio
async def test_individual_complete_e2e_workflow(client, test_db_session):
    # =========================================================================
    # STEP 1: Registration and Authentication
    # =========================================================================
    reg_payload = {
        "email": "candidate.elena@gmail.com",
        "password": "SecurePassword123!",
        "full_name": "Elena V. Rostova",
        "title": "Lead Distributed Systems Engineer",
        "skills": ["Python", "Distributed Systems", "PostgreSQL", "Kafka", "Kubernetes"],
        "location": "Remote",
        "remote_preference": "remote",
    }
    reg_res = client.post("/v1/auth/register/individual", json=reg_payload)
    assert reg_res.status_code == 201, reg_res.text
    token_data = reg_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify identity via /v1/auth/me
    me_res = client.get("/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "candidate.elena@gmail.com"
    assert me_data["account_type"] == "individual"
    assert me_data["full_name"] == "Elena V. Rostova"

    # =========================================================================
    # STEP 2: Profile Query, Resume Parsing & Profile Enrichment
    # =========================================================================
    # Fetch initial profile
    prof_res = client.get("/v1/individual/profile", headers=headers)
    assert prof_res.status_code == 200
    initial_profile = prof_res.json()["profile"]
    assert initial_profile["full_name"] == "Elena V. Rostova"
    assert initial_profile["completion_percentage"] >= 50

    # Parse raw resume
    raw_resume = """
    Elena V. Rostova - Principal Infrastructure & Cloud Engineer
    Experience: 8 years building resilient backends, fault-tolerant event streams, and microservices.
    Core Tech: Python, Go, Rust, Apache Kafka, Docker, Kubernetes, AWS, Terraform, Distributed Consensus (Raft).
    Education: M.S. Computer Science.
    Target compensation: $170,000 - $220,000.
    """
    resume_res = client.post(
        "/v1/individual/profile/resume-parse",
        json={"resume_text": raw_resume},
        headers=headers,
    )
    assert resume_res.status_code == 200
    parsed_skills = resume_res.json().get("extracted_skills", [])
    assert len(parsed_skills) > 0

    # Update profile with parsed attributes & target preferences
    update_res = client.put(
        "/v1/individual/profile",
        json={
            "bio": "Specializing in high-throughput streaming systems, Raft consensus, and cloud-native backends.",
            "skills": ["Python", "Go", "Kafka", "Kubernetes", "PostgreSQL", "Docker", "AWS", "Distributed Systems"],
            "experience_years": 8.0,
            "salary_min": 160000,
            "salary_max": 220000,
            "career_goals": "Staff / Principal Distributed Systems Architect",
        },
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["completion_percentage"] >= 80

    # =========================================================================
    # STEP 3: Seed Target Opportunity & Company, then Run 6-Factor Matching
    # =========================================================================
    target_company = Company(
        name="NovaStream Technologies",
        domain="novastream.io",
        industry="Cloud Data Streaming",
        description="Next-generation streaming platform and real-time processing engine.",
    )
    test_db_session.add(target_company)
    await test_db_session.commit()
    await test_db_session.refresh(target_company)

    target_contact = Contact(
        company_id=target_company.id,
        full_name="Marcus Vance",
        email="marcus.vance@novastream.io",
        title="Head of Engineering",
    )
    test_db_session.add(target_contact)
    await test_db_session.commit()
    await test_db_session.refresh(target_contact)

    target_opp = Opportunity(
        title="Senior / Staff Distributed Systems Engineer",
        type="job",
        raw_description="Looking for an experienced engineer in Python, Go, Kafka, Kubernetes, and distributed architecture.",
        source_url="https://novastream.io/careers/staff-distributed-systems",
        company_id=target_company.id,
        source_platform="direct_career_page",
        salary_min=165000,
        salary_max=215000,
        location="Remote",
        location_type="remote",
        tech_required=["Python", "Go", "Kafka", "Kubernetes", "PostgreSQL"],
    )
    test_db_session.add(target_opp)
    await test_db_session.commit()
    await test_db_session.refresh(target_opp)

    # Run 6-Factor AI Matching Search
    search_res = client.post("/v1/individual/search", headers=headers)
    assert search_res.status_code == 200
    search_data = search_res.json()
    assert search_data["status"] == "success"
    assert search_data["opportunities_evaluated"] >= 1
    top_matches = search_data["top_matches"]
    assert len(top_matches) >= 1
    assert top_matches[0]["score"] >= 80
    assert len(top_matches[0]["explanation"]) > 10

    # Fetch 6-Factor AI Matches list
    match_res = client.get("/v1/individual/matches", headers=headers)
    assert match_res.status_code == 200
    match_data = match_res.json()
    assert match_data["status"] == "success"
    assert match_data["count"] >= 1

    matched_opp = next((m for m in match_data["matches"] if m["id"] == str(target_opp.id)), None)
    assert matched_opp is not None
    # Verify 6-factor score and breakdown
    assert matched_opp["score"] >= 80
    assert "score_breakdown" in matched_opp

    # =========================================================================
    # STEP 4: Submit Application -> Trigger Outreach & 3-Touch Follow-Up
    # =========================================================================
    apply_payload = {
        "opportunity_id": str(target_opp.id),
        "custom_note": "Thrilled by NovaStream's work on low-latency event processing.",
    }
    apply_res = client.post("/v1/individual/apply", json=apply_payload, headers=headers)
    assert apply_res.status_code == 200
    apply_data = apply_res.json()
    assert apply_data["status"] == "success"
    assert "follow_up_schedules" in apply_data
    assert len(apply_data["follow_up_schedules"]) == 3  # Day 3, Day 7, Day 14

    # Verify DB records for Outreach and FollowUpSchedule
    outreach_records = (await test_db_session.execute(select(OutreachHistory))).scalars().all()
    assert len(outreach_records) >= 1
    assert outreach_records[0].opportunity_id == target_opp.id

    schedules = (await test_db_session.execute(select(FollowUpSchedule))).scalars().all()
    assert len(schedules) == 3
    touch_steps = [s.sequence_step for s in schedules]
    assert touch_steps == [1, 2, 3]

    # =========================================================================
    # STEP 5: Rejection Handling & Autonomous Recovery Workflow
    # =========================================================================
    reject_payload = {
        "opportunity_id": str(target_opp.id),
        "rejection_reason": "Team chose a candidate with more Rust experience, but praised architecture background.",
    }
    reject_res = client.post("/v1/individual/rejections", json=reject_payload, headers=headers)
    assert reject_res.status_code == 200
    reject_data = reject_res.json()
    assert reject_data["status"] == "success"

    # Verify lookalike discovery & recovery action plan
    assert "lookalike_companies" in reject_data
    assert len(reject_data["lookalike_companies"]) >= 2
    assert "feedback_analysis" in reject_data
    assert "recovery_strategy" in reject_data

    # Verify rejection log was persisted in DB
    rejection_records = (await test_db_session.execute(select(RejectionLog))).scalars().all()
    assert len(rejection_records) >= 1
    assert rejection_records[0].opportunity_id == target_opp.id
    assert rejection_records[0].rejection_reason == reject_payload["rejection_reason"]

    # =========================================================================
    # STEP 6: Verify Candidate Dashboard Statistics Telemetry
    # =========================================================================
    stats_res = client.get("/v1/individual/dashboard-stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()["data"]
    assert stats["applications_sent"] >= 1
    assert stats["scheduled_follow_ups"] >= 3
    assert stats["rejections_recovered"] >= 1
    assert stats["profile_completion_percentage"] >= 80
    assert stats["candidate_name"] == "Elena V. Rostova"
