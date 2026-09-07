"""End-to-end workflow test for the Enterprise Talent Pipeline & Multi-Tenancy journey.

Verifies:
1. Enterprise Registration -> Org Creation -> Owner JWT Issuance
2. Team RBAC -> Recruiter Invitation & Member Management
3. AI Talent Scouting -> Multi-factor matching & prospect scoring
4. Manual Candidate Ingestion -> Pipeline tracking
5. Kanban Stage Advancement -> Discovered to Screening to Interviewing to Offered to Hired
6. Real-time hiring funnel conversion metrics & stage distribution telemetry
7. Strict Multi-Tenant Isolation -> Zero data cross-contamination between Organizations A and B
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
    Candidate,
    Organization,
    OrganizationMember,
    User,
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
async def test_enterprise_complete_e2e_workflow(client, test_db_session):
    # =========================================================================
    # STEP 1: Enterprise Organization Registration & Owner Auth
    # =========================================================================
    org_a_reg = {
        "email": "sarah.head@apexsystems.com",
        "password": "ApexPassword2026!",
        "full_name": "Sarah Connor",
        "organization_name": "Apex Systems Corp",
        "domain": "apexsystems.com",
        "plan_tier": "enterprise_scale",
    }
    reg_res_a = client.post("/v1/auth/register/enterprise", json=org_a_reg)
    assert reg_res_a.status_code == 201, reg_res_a.text
    token_a = reg_res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Verify Organization profile
    org_res = client.get("/v1/enterprise/organization", headers=headers_a)
    assert org_res.status_code == 200
    org_data = org_res.json()["organization"]
    assert org_data["name"] == "Apex Systems Corp"
    assert org_data["plan_tier"] == "enterprise_scale"
    org_a_id = org_data["id"]

    # =========================================================================
    # STEP 2: Team RBAC Management & Recruiter Invitation
    # =========================================================================
    # Verify initial team has owner
    team_res = client.get("/v1/enterprise/team", headers=headers_a)
    assert team_res.status_code == 200
    team_members = team_res.json()["team"]
    assert len(team_members) == 1
    assert team_members[0]["role"] == "owner"

    # Invite recruiter to Org A
    invite_payload = {
        "email": "marcus.recruiter@apexsystems.com",
        "full_name": "Marcus Vance",
        "role": "recruiter",
    }
    invite_res = client.post("/v1/enterprise/team", json=invite_payload, headers=headers_a)
    assert invite_res.status_code == 200
    assert invite_res.json()["status"] == "success"
    recruiter_user_id = invite_res.json()["user_id"]

    # Verify team now has 2 members
    team_res2 = client.get("/v1/enterprise/team", headers=headers_a)
    assert len(team_res2.json()["team"]) == 2

    # =========================================================================
    # STEP 3: Autonomous AI Candidate Talent Scout
    # =========================================================================
    scout_payload = {
        "role_title": "Principal Distributed Systems Engineer",
        "required_skills": ["Go", "Kubernetes", "Kafka", "PostgreSQL", "Raft"],
        "min_experience_years": 6.0,
        "location": "Remote",
    }
    scout_res = client.post("/v1/enterprise/search-candidates", json=scout_payload, headers=headers_a)
    assert scout_res.status_code == 200
    scout_data = scout_res.json()
    assert scout_data["status"] == "success"
    assert scout_data["candidates_discovered"] >= 3
    discovered_cands = scout_data["candidates"]
    for c in discovered_cands:
        assert c["status"] == "discovered"
        assert c["match_score"] >= 75
        assert len(c["match_explanation"]) > 10

    lead_cand_id = discovered_cands[0]["id"]

    # =========================================================================
    # STEP 4: Manual Candidate Creation
    # =========================================================================
    manual_cand_payload = {
        "full_name": "Sophia Rodriguez",
        "email": "sophia.rodriguez@externaldev.io",
        "title": "Senior Cloud Infrastructure Architect",
        "skills": ["Terraform", "AWS", "Python", "Kubernetes", "CI/CD"],
        "experience_summary": "7+ years deploying cloud native architectures for Fortune 500 enterprises.",
        "location": "Remote",
        "notes": "Direct referral from engineering director.",
    }
    manual_res = client.post("/v1/enterprise/candidates", json=manual_cand_payload, headers=headers_a)
    assert manual_res.status_code == 200
    manual_cand_id = manual_res.json()["candidate_id"]

    # Total candidates in Org A should now be discovered + 1 manual
    all_cands_res = client.get("/v1/enterprise/candidates", headers=headers_a)
    assert all_cands_res.status_code == 200
    assert len(all_cands_res.json()["candidates"]) >= 4

    # =========================================================================
    # STEP 5: Kanban Stage Progression Across the Hiring Funnel
    # =========================================================================
    # Advance lead candidate: discovered -> screening
    stage_screen = client.patch(
        f"/v1/enterprise/candidates/{lead_cand_id}/stage",
        json={"stage": "screening", "notes": "Passed automated resume screening and code portfolio review."},
        headers=headers_a,
    )
    assert stage_screen.status_code == 200
    assert stage_screen.json()["stage"] == "screening"

    # Advance lead candidate: screening -> interviewing
    stage_interview = client.patch(
        f"/v1/enterprise/candidates/{lead_cand_id}/stage",
        json={"stage": "interviewing", "notes": "Technical system design loop completed with unanimous hire recommendation."},
        headers=headers_a,
    )
    assert stage_interview.status_code == 200
    assert stage_interview.json()["stage"] == "interviewing"

    # Advance lead candidate: interviewing -> offered
    stage_offer = client.patch(
        f"/v1/enterprise/candidates/{lead_cand_id}/stage",
        json={"stage": "offered", "notes": "Sent competitive package offer with equity grant."},
        headers=headers_a,
    )
    assert stage_offer.status_code == 200
    assert stage_offer.json()["stage"] == "offered"

    # Advance lead candidate: offered -> hired
    stage_hired = client.patch(
        f"/v1/enterprise/candidates/{lead_cand_id}/stage",
        json={"stage": "hired", "notes": "Offer accepted! Candidate starts in 2 weeks."},
        headers=headers_a,
    )
    assert stage_hired.status_code == 200
    assert stage_hired.json()["stage"] == "hired"

    # Advance manual candidate: discovered -> screening
    stage_manual = client.patch(
        f"/v1/enterprise/candidates/{manual_cand_id}/stage",
        json={"stage": "screening", "notes": "Initial recruiter sync booked."},
        headers=headers_a,
    )
    assert stage_manual.status_code == 200
    assert stage_manual.json()["stage"] == "screening"

    # =========================================================================
    # STEP 6: Enterprise Telemetry & Conversion Metrics Verification
    # =========================================================================
    stats_res = client.get("/v1/enterprise/dashboard-stats", headers=headers_a)
    assert stats_res.status_code == 200
    metrics = stats_res.json()["data"]
    assert metrics["organization_name"] == "Apex Systems Corp"
    assert metrics["total_candidates"] >= 4
    assert metrics["stage_distribution"]["hired"] >= 1
    assert metrics["stage_distribution"]["screening"] >= 1
    assert metrics["team_members_count"] == 2
    assert metrics["average_match_score"] >= 75.0

    # =========================================================================
    # STEP 7: Strict Multi-Tenant Boundary Isolation Test
    # =========================================================================
    # Register Org B (Quantum Dynamics)
    org_b_reg = {
        "email": "admin@quantumdynamics.org",
        "password": "QuantumSecurePass456!",
        "full_name": "Elena Fisher",
        "organization_name": "Quantum Dynamics",
        "domain": "quantumdynamics.org",
        "plan_tier": "scale",
    }
    reg_res_b = client.post("/v1/auth/register/enterprise", json=org_b_reg)
    assert reg_res_b.status_code == 201
    token_b = reg_res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Org B must see 0 candidates in its pipeline
    b_cands_res = client.get("/v1/enterprise/candidates", headers=headers_b)
    assert b_cands_res.status_code == 200
    assert len(b_cands_res.json()["candidates"]) == 0

    # Org B stats must reflect 0 candidates and 1 team member
    b_stats = client.get("/v1/enterprise/dashboard-stats", headers=headers_b).json()["data"]
    assert b_stats["organization_name"] == "Quantum Dynamics"
    assert b_stats["total_candidates"] == 0
    assert b_stats["team_members_count"] == 1

    # Org B must NOT be able to view, access, or mutate Org A's candidate
    b_tamper_attempt = client.patch(
        f"/v1/enterprise/candidates/{lead_cand_id}/stage",
        json={"stage": "rejected"},
        headers=headers_b,
    )
    assert b_tamper_attempt.status_code == 404

    # Org B must NOT be able to remove Org A's team member
    b_remove_attempt = client.delete(
        f"/v1/enterprise/team/{recruiter_user_id}",
        headers=headers_b,
    )
    assert b_remove_attempt.status_code == 404

    # Org A candidate state remains intact and hired
    a_verify = client.get("/v1/enterprise/candidates", headers=headers_a)
    hired_cand = next((c for c in a_verify.json()["candidates"] if c["id"] == lead_cand_id), None)
    assert hired_cand is not None
    assert hired_cand["status"] == "hired"
    assert "Offer accepted!" in hired_cand["notes"]
