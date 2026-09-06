"""Unit and integration tests for Opportunities API router."""
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.app.models.core import Base, Company, Opportunity, User
from backend.app import main
from backend.app.dependencies import get_db
from backend.app.security import get_current_active_user


@pytest.fixture
def client():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def init_test_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    __import__("asyncio").run(init_test_schema())
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    async def override_current_user():
        return User(
            id=uuid.uuid4(),
            email="admin@ejicode.ai",
            full_name="Admin",
            roles=["admin"],
            is_active=True,
        )

    app = main.create_app()
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_active_user] = override_current_user

    client = TestClient(app)
    client.factory = factory
    return client


def test_create_and_get_opportunity(client):
    # First create company
    c_res = client.post("/v1/companies", json={"name": "Tech Corp", "domain": "techcorp.com"})
    cid = c_res.json()["id"]

    res = client.post(
        "/v1/opportunities",
        json={
            "company_id": cid,
            "title": "Lead AI Architect",
            "type": "full_time",
            "source_platform": "linkedin",
            "source_url": "https://linkedin.com/jobs/123",
            "location_type": "remote",
            "salary_min": 150000,
            "salary_max": 220000,
            "tech_required": ["Python", "PyTorch", "FastAPI"],
            "score": 90,
            "rank": 1,
            "status": "new",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Lead AI Architect"
    assert data["company_id"] == cid
    opp_id = data["id"]

    # Get by ID
    get_res = client.get(f"/v1/opportunities/{opp_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Lead AI Architect"


def test_list_opportunities_filters(client):
    c_res = client.post("/v1/companies", json={"name": "Filter Corp", "domain": "filtercorp.com"})
    cid = c_res.json()["id"]

    client.post(
        "/v1/opportunities",
        json={
            "company_id": cid,
            "title": "Backend Python Dev",
            "type": "contract",
            "source_url": "https://upwork.com/jobs/991",
            "status": "contacted",
            "score": 85,
        },
    )
    client.post(
        "/v1/opportunities",
        json={
            "company_id": cid,
            "title": "Frontend React Dev",
            "type": "full_time",
            "source_url": "https://indeed.com/jobs/992",
            "status": "new",
            "score": 70,
        },
    )

    # List all
    res = client.get("/v1/opportunities")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2

    # Filter by status
    res_status = client.get("/v1/opportunities?status=contacted")
    assert res_status.status_code == 200
    assert all(o["status"] == "contacted" for o in res_status.json())

    # Filter by type
    res_type = client.get("/v1/opportunities?type=contract")
    assert res_type.status_code == 200
    assert all(o["type"] == "contract" for o in res_type.json())


def test_update_and_delete_opportunity(client):
    c_res = client.post("/v1/companies", json={"name": "Edit Corp", "domain": "editcorp.com"})
    cid = c_res.json()["id"]

    res = client.post(
        "/v1/opportunities",
        json={
            "company_id": cid,
            "title": "Junior Dev",
            "type": "contract",
            "source_url": "https://example.com/j1",
        },
    )
    opp_id = res.json()["id"]

    # Update
    patch_res = client.patch(f"/v1/opportunities/{opp_id}", json={"status": "pursuing", "score": 95, "rank": 2})
    assert patch_res.status_code == 200
    assert patch_res.json()["status"] == "pursuing"
    assert patch_res.json()["score"] == 95

    # Delete
    del_res = client.delete(f"/v1/opportunities/{opp_id}")
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(f"/v1/opportunities/{opp_id}")
    assert get_res.status_code == 404
