"""Unit and integration tests for Companies API router."""
import os
import uuid
from unittest.mock import AsyncMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.app.models.core import Base, Company, Contact, Opportunity, CompanyResearchReport, User
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


def test_create_and_get_company(client):
    res = client.post(
        "/v1/companies",
        json={
            "name": "Alpha Technologies",
            "domain": "alphatech.io",
            "industry": "Software",
            "size": "50-200",
            "description": "B2B SaaS platform",
            "tech_stack": ["Python", "React", "PostgreSQL"],
            "fit_score": 88,
        },
    )
    assert res.status_code == 201
    data = res.json()
    assert data["name"] == "Alpha Technologies"
    assert data["domain"] == "alphatech.io"
    company_id = data["id"]

    # Get company by ID
    get_res = client.get(f"/v1/companies/{company_id}")
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Alpha Technologies"


def test_list_companies_filters(client):
    client.post("/v1/companies", json={"name": "Fintech One", "domain": "fintechone.com", "industry": "Finance", "fit_score": 92})
    client.post("/v1/companies", json={"name": "Health Plus", "domain": "healthplus.org", "industry": "Healthcare", "fit_score": 75})

    # List all
    res = client.get("/v1/companies")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 2

    # Filter by industry
    res_ind = client.get("/v1/companies?industry=Finance")
    assert res_ind.status_code == 200
    ind_items = res_ind.json()
    assert all(c["industry"] == "Finance" for c in ind_items)

    # Filter by min_fit_score
    res_fit = client.get("/v1/companies?min_fit_score=90")
    assert res_fit.status_code == 200
    fit_items = res_fit.json()
    assert all(c["fit_score"] >= 90 for c in fit_items)

    # Search query
    res_search = client.get("/v1/companies?search=Fintech")
    assert res_search.status_code == 200
    assert any("Fintech" in c["name"] for c in res_search.json())


def test_update_and_delete_company(client):
    res = client.post("/v1/companies", json={"name": "Old Name", "domain": "old.com"})
    company_id = res.json()["id"]

    # Update
    patch_res = client.patch(f"/v1/companies/{company_id}", json={"name": "New Name", "fit_score": 95})
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "New Name"
    assert patch_res.json()["fit_score"] == 95

    # Delete
    del_res = client.delete(f"/v1/companies/{company_id}")
    assert del_res.status_code == 204

    # Verify not found
    get_res = client.get(f"/v1/companies/{company_id}")
    assert get_res.status_code == 404


def test_company_subresources(client):
    # Create company
    c_res = client.post("/v1/companies", json={"name": "MegaCorp", "domain": "megacorp.com"})
    cid = c_res.json()["id"]

    # Add contact and research report directly to db
    async def add_related():
        async with client.factory() as session:
            con = Contact(company_id=uuid.UUID(cid), first_name="Sarah", last_name="Connor", email="sarah@megacorp.com")
            rep = CompanyResearchReport(company_id=uuid.UUID(cid), summary="Great company for AI automation", full_report={"strengths": ["Strong engineering"]})
            session.add_all([con, rep])
            await session.commit()

    __import__("asyncio").run(add_related())

    # Get company contacts
    con_res = client.get(f"/v1/companies/{cid}/contacts")
    assert con_res.status_code == 200
    assert len(con_res.json()) >= 1
    assert con_res.json()[0]["email"] == "sarah@megacorp.com"

    # Get company research
    rep_res = client.get(f"/v1/companies/{cid}/research")
    assert rep_res.status_code == 200
    assert rep_res.json()[0]["summary"] == "Great company for AI automation"
