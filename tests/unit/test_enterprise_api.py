"""Unit tests for enterprise multi-tenancy, candidate talent pipeline, team RBAC, and analytics."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-32-chars-long!!")

from backend.app.main import app
from backend.app.dependencies import get_db
from backend.app.models.core import Base, User, Organization, OrganizationMember, Candidate


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


def test_enterprise_organization_and_team(client):
    """Test enterprise organization lifecycle, team invites, and member permissions."""
    # Register enterprise account
    reg_payload = {
        "email": "sarah.vp@acmecorp.com",
        "password": "Password123!",
        "full_name": "Sarah Connor",
        "organization_name": "Acme Global Technologies",
        "domain": "acmecorp.com",
        "plan_tier": "scale",
    }
    reg_res = client.post("/v1/auth/register/enterprise", json=reg_payload)
    assert reg_res.status_code == 201
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Get organization details
    org_res = client.get("/v1/enterprise/organization", headers=headers)
    assert org_res.status_code == 200
    org_data = org_res.json()["organization"]
    assert org_data["name"] == "Acme Global Technologies"
    assert org_data["domain"] == "acmecorp.com"
    assert org_data["plan_tier"] == "scale"

    # Update organization details
    up_res = client.put("/v1/enterprise/organization", json={"name": "Acme Global Corp"}, headers=headers)
    assert up_res.status_code == 200

    # Verify team has the owner
    team_res = client.get("/v1/enterprise/team", headers=headers)
    assert team_res.status_code == 200
    team = team_res.json()["team"]
    assert len(team) == 1
    assert team[0]["role"] == "owner"

    # Invite new team member
    invite_payload = {
        "email": "recruiter.john@acmecorp.com",
        "full_name": "John Doe",
        "role": "recruiter",
    }
    invite_res = client.post("/v1/enterprise/team", json=invite_payload, headers=headers)
    assert invite_res.status_code == 200
    invited_user_id = invite_res.json()["user_id"]

    # Verify team now has 2 members
    team_res2 = client.get("/v1/enterprise/team", headers=headers)
    assert len(team_res2.json()["team"]) == 2

    # Remove team member
    del_res = client.delete(f"/v1/enterprise/team/{invited_user_id}", headers=headers)
    assert del_res.status_code == 200

    # Verify team is back to 1
    team_res3 = client.get("/v1/enterprise/team", headers=headers)
    assert len(team_res3.json()["team"]) == 1


def test_enterprise_talent_pipeline_and_isolation(client):
    """Test candidate talent search, stage advancement, and multi-tenant boundary isolation."""
    # Org A
    org_a_payload = {
        "email": "admin@orga.com",
        "password": "Password123!",
        "full_name": "Admin Org A",
        "organization_name": "Alpha Corp",
        "domain": "orga.com",
    }
    res_a = client.post("/v1/auth/register/enterprise", json=org_a_payload)
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Org B
    org_b_payload = {
        "email": "admin@orgb.com",
        "password": "Password123!",
        "full_name": "Admin Org B",
        "organization_name": "Beta Industries",
        "domain": "orgb.com",
    }
    res_b = client.post("/v1/auth/register/enterprise", json=org_b_payload)
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Org A searches for candidates
    search_payload = {
        "role_title": "Full Stack AI Engineer",
        "required_skills": ["Python", "React", "Docker"],
        "min_experience_years": 4.0,
        "location": "Remote",
    }
    search_res = client.post("/v1/enterprise/search-candidates", json=search_payload, headers=headers_a)
    assert search_res.status_code == 200
    candidates_a = search_res.json()["candidates"]
    assert len(candidates_a) >= 2

    cand_id = candidates_a[0]["id"]

    # Org A advances candidate from discovered -> interviewing
    stage_res = client.patch(
        f"/v1/enterprise/candidates/{cand_id}/stage",
        json={"stage": "interviewing", "notes": "Completed initial tech screen successfully"},
        headers=headers_a,
    )
    assert stage_res.status_code == 200
    assert stage_res.json()["stage"] == "interviewing"

    # Org A dashboard stats
    stats_res = client.get("/v1/enterprise/dashboard-stats", headers=headers_a)
    assert stats_res.status_code == 200
    stats_data = stats_res.json()["data"]
    assert stats_data["total_candidates"] >= 2
    assert stats_data["stage_distribution"]["interviewing"] >= 1

    # MULTI-TENANT ISOLATION: Org B must see 0 candidates
    b_cands = client.get("/v1/enterprise/candidates", headers=headers_b)
    assert b_cands.status_code == 200
    assert len(b_cands.json()["candidates"]) == 0

    # Org B cannot modify Org A's candidate
    b_attempt = client.patch(
        f"/v1/enterprise/candidates/{cand_id}/stage",
        json={"stage": "hired"},
        headers=headers_b,
    )
    assert b_attempt.status_code == 404
