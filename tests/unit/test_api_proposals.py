"""Unit and integration tests for Proposals API router."""
import os
import uuid
from unittest.mock import AsyncMock, patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.app.models.core import Base, Company, Opportunity, Contact, Proposal, User
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


def test_create_and_get_proposal(client):
    c_res = client.post("/v1/companies", json={"name": "Prop Co", "domain": "propco.com"})
    cid = c_res.json()["id"]

    o_res = client.post(
        "/v1/opportunities",
        json={"company_id": cid, "title": "Fullstack Role", "type": "contract", "source_url": "https://p.com/1"},
    )
    oid = o_res.json()["id"]

    con_res = client.post(
        "/v1/contacts",
        json={"company_id": cid, "first_name": "Amy", "email": "amy@propco.com"},
    )
    con_id = con_res.json()["id"]

    # Create proposal
    res = client.post(
        "/v1/proposals",
        json={
            "opportunity_id": oid,
            "contact_id": con_id,
            "type": "cold_email",
            "subject": "Collaboration proposal for Fullstack Role",
            "body": "Hi Amy, I saw your job opening and wanted to reach out.",
            "tone": "confident",
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["subject"] == "Collaboration proposal for Fullstack Role"
    assert data["status"] == "draft"
    pid = data["id"]

    # Get by ID
    get_res = client.get(f"/v1/proposals/{pid}")
    assert get_res.status_code == 200
    assert get_res.json()["subject"] == data["subject"]


def test_approve_and_reject_proposal(client):
    c_res = client.post("/v1/companies", json={"name": "Approval Co", "domain": "approvalco.com"})
    cid = c_res.json()["id"]
    o_res = client.post(
        "/v1/opportunities",
        json={"company_id": cid, "title": "Dev Role", "type": "job", "source_url": "https://a.com/1"},
    )
    oid = o_res.json()["id"]
    con_res = client.post(
        "/v1/contacts",
        json={"company_id": cid, "first_name": "Bob", "email": "bob@approvalco.com"},
    )
    con_id = con_res.json()["id"]

    p_res = client.post(
        "/v1/proposals",
        json={
            "opportunity_id": oid,
            "contact_id": con_id,
            "subject": "Subj",
            "body": "Body text",
            "tone": "professional",
        },
    )
    pid = p_res.json()["id"]

    # Approve
    app_res = client.patch(f"/v1/proposals/{pid}/approve")
    assert app_res.status_code == 200
    assert app_res.json()["status"] == "approved"

    # Reject
    rej_res = client.patch(f"/v1/proposals/{pid}/reject?reason=Tone+too+casual")
    assert rej_res.status_code == 200
    assert rej_res.json()["status"] == "rejected"
    assert rej_res.json()["reason"] == "Tone too casual"


def test_update_and_delete_proposal(client):
    c_res = client.post("/v1/companies", json={"name": "Crud Co", "domain": "crudco.com"})
    cid = c_res.json()["id"]
    o_res = client.post(
        "/v1/opportunities",
        json={"company_id": cid, "title": "Role", "type": "job", "source_url": "https://crud.com/1"},
    )
    oid = o_res.json()["id"]
    con_res = client.post(
        "/v1/contacts",
        json={"company_id": cid, "first_name": "Carl", "email": "carl@crudco.com"},
    )
    con_id = con_res.json()["id"]

    p_res = client.post(
        "/v1/proposals",
        json={
            "opportunity_id": oid,
            "contact_id": con_id,
            "subject": "Initial Subject",
            "body": "Initial Body with multiple words",
        },
    )
    pid = p_res.json()["id"]

    # Patch
    patch_res = client.patch(f"/v1/proposals/{pid}", json={"subject": "Updated Subject"})
    assert patch_res.status_code == 200
    assert patch_res.json()["subject"] == "Updated Subject"

    # Delete
    del_res = client.delete(f"/v1/proposals/{pid}")
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(f"/v1/proposals/{pid}")
    assert get_res.status_code == 404
