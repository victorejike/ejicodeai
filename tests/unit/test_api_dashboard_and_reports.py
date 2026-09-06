"""Unit and integration tests for Dashboard and Reports API routers."""
import os
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.app.models.core import Base, Company, Opportunity, Contact, Proposal, OutreachHistory, User, Report
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


def test_dashboard_summary_and_analytics(client):
    # Seed sample entities
    async def seed():
        async with client.factory() as session:
            c = Company(name="Dash Co", domain="dashco.com", fit_score=88)
            session.add(c)
            await session.commit()
            opp = Opportunity(company_id=c.id, title="AI Eng", type="job", score=90, status="contacted")
            con = Contact(company_id=c.id, first_name="Dave", email="dave@dashco.com")
            session.add_all([opp, con])
            await session.commit()
            prop = Proposal(opportunity_id=opp.id, contact_id=con.id, body="Hi Dave", status="approved")
            session.add(prop)
            await session.commit()
            out = OutreachHistory(proposal_id=prop.id, contact_id=con.id, opportunity_id=opp.id, delivery_status="delivered")
            session.add(out)
            await session.commit()

    __import__("asyncio").run(seed())

    # Test summary
    res = client.get("/v1/dashboard/summary")
    assert res.status_code == 200
    summary = res.json()
    assert summary["counts"]["companies"] >= 1
    assert summary["counts"]["opportunities"] >= 1
    assert summary["counts"]["proposals"] >= 1

    # Test analytics
    analytics_res = client.get("/v1/dashboard/analytics")
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert "opportunity_discovery" in analytics
    assert "company_growth" in analytics
    assert "outreach_success" in analytics


def test_reports_endpoints(client):
    # Create a report directly in db
    async def seed_report():
        async with client.factory() as session:
            r = Report(
                type="weekly",
                title="Weekly AI Summary",
                summary="High activity week",
                content={"total_leads": 42},
                markdown="# Summary\nHigh activity",
            )
            session.add(r)
            await session.commit()
            return str(r.id)

    rep_id = __import__("asyncio").run(seed_report())

    # List reports
    list_res = client.get("/v1/reports")
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # Get report by ID
    get_res = client.get(f"/v1/reports/{rep_id}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Weekly AI Summary"

    # Get weekly reports
    weekly_res = client.get("/v1/reports/weekly")
    assert weekly_res.status_code == 200
    assert any(r["id"] == rep_id for r in weekly_res.json())
