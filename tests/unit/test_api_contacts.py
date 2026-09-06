"""Unit and integration tests for Contacts API router."""
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.app.models.core import Base, Company, Contact, User
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


def test_create_and_get_contact(client):
    c_res = client.post("/v1/companies", json={"name": "Org X", "domain": "orgx.com"})
    cid = c_res.json()["id"]

    res = client.post(
        "/v1/contacts",
        json={
            "company_id": cid,
            "first_name": "Elena",
            "last_name": "Rostova",
            "email": "elena@orgx.com",
            "title": "VP of Engineering",
            "role_category": "engineering_lead",
            "is_decision_maker": True,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["first_name"] == "Elena"
    assert data["is_decision_maker"] is True
    contact_id = data["id"]

    # Get by ID
    get_res = client.get(f"/v1/contacts/{contact_id}")
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "elena@orgx.com"


def test_list_contacts_filters(client):
    c_res = client.post("/v1/companies", json={"name": "Org Y", "domain": "orgy.com"})
    cid = c_res.json()["id"]

    client.post(
        "/v1/contacts",
        json={
            "company_id": cid,
            "first_name": "Marcus",
            "email": "marcus@orgy.com",
            "title": "CTO",
            "role_category": "executive",
            "is_decision_maker": True,
        },
    )
    client.post(
        "/v1/contacts",
        json={
            "company_id": cid,
            "first_name": "Lisa",
            "email": "lisa@orgy.com",
            "title": "Recruiter",
            "role_category": "talent",
            "is_decision_maker": False,
        },
    )

    # List all
    res = client.get("/v1/contacts")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2

    # Filter by is_decision_maker
    res_dm = client.get("/v1/contacts?is_decision_maker=true")
    assert res_dm.status_code == 200
    assert all(c["is_decision_maker"] is True for c in res_dm.json())

    # Filter by role_category
    res_exec = client.get("/v1/contacts?role_category=executive")
    assert res_exec.status_code == 200
    assert all(c["role_category"] == "executive" for c in res_exec.json())


def test_update_and_delete_contact(client):
    c_res = client.post("/v1/companies", json={"name": "Org Z", "domain": "orgz.com"})
    cid = c_res.json()["id"]

    res = client.post(
        "/v1/contacts",
        json={"company_id": cid, "first_name": "Tom", "email": "tom@orgz.com", "title": "Lead"},
    )
    contact_id = res.json()["id"]

    # Update
    patch_res = client.patch(
        f"/v1/contacts/{contact_id}",
        json={"title": "Chief Technology Officer", "is_decision_maker": True},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["title"] == "Chief Technology Officer"
    assert patch_res.json()["is_decision_maker"] is True

    # Delete
    del_res = client.delete(f"/v1/contacts/{contact_id}")
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(f"/v1/contacts/{contact_id}")
    assert get_res.status_code == 404
