"""Unit tests for AgentPersistenceService with async SQLAlchemy."""
import pytest
from unittest.mock import patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from backend.app.models.core import (
    Base,
    Company,
    Opportunity,
    Contact,
    CompanyResearchReport,
    AgentRun,
)
from backend.app.services.agent_persistence import AgentPersistenceService


@pytest.fixture
async def test_session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_record_run_lifecycle(test_session_factory):
    with patch("backend.app.services.agent_persistence.async_session", test_session_factory):
        run_id = await AgentPersistenceService.record_run_start(
            agent_name="job_scout",
            trigger_type="cron",
            input_payload={"platforms": ["remoteok"]},
        )
        assert run_id is not None

        # Verify record created
        async with test_session_factory() as session:
            run = await session.get(AgentRun, run_id)
            assert run is not None
            assert run.agent_name == "job_scout"
            assert run.status == "running"
            assert run.input_payload == {"platforms": ["remoteok"]}

        # Complete run
        await AgentPersistenceService.record_run_completion(
            run_id=run_id,
            status="completed",
            duration_ms=1250,
            items_processed=10,
            items_created=4,
            output_summary={"found": 4},
        )

        async with test_session_factory() as session:
            run = await session.get(AgentRun, run_id)
            assert run.status == "completed"
            assert run.duration_ms == 1250
            assert run.items_processed == 10
            assert run.items_created == 4
            assert run.output_summary == {"found": 4}
            assert run.completed_at is not None


@pytest.mark.asyncio
async def test_save_companies_create_and_deduplicate(test_session_factory):
    with patch("backend.app.services.agent_persistence.async_session", test_session_factory):
        companies_data = [
            {
                "name": "Acme AI Corp",
                "domain": "acme.ai",
                "website_url": "https://acme.ai",
                "industry": "Artificial Intelligence",
                "tech_stack": ["Python", "PyTorch"],
                "fit_score": 80,
            },
            {
                "name": "Beta Labs",
                "domain": "betalabs.io",
                "industry": "FinTech",
                "tech_stack": ["FastAPI", "React"],
                "fit_score": 75,
            },
        ]

        saved = await AgentPersistenceService.save_companies(companies_data)
        assert len(saved) == 2

        # Verify in DB
        async with test_session_factory() as session:
            res = await session.execute(select(Company))
            all_c = res.scalars().all()
            assert len(all_c) == 2

        # Update existing company with merged tech stack and higher fit score
        updated_data = [
            {
                "name": "Acme AI Corp",
                "domain": "acme.ai",
                "tech_stack": ["Python", "PostgreSQL"],
                "fit_score": 90,
            }
        ]
        saved_updated = await AgentPersistenceService.save_companies(updated_data)
        assert len(saved_updated) == 1

        async with test_session_factory() as session:
            res = await session.execute(select(Company).where(Company.domain == "acme.ai"))
            c = res.scalars().first()
            assert c is not None
            assert c.fit_score == 90
            assert "PostgreSQL" in c.tech_stack
            assert "PyTorch" in c.tech_stack


@pytest.mark.asyncio
async def test_save_opportunities_with_company_link(test_session_factory):
    with patch("backend.app.services.agent_persistence.async_session", test_session_factory):
        # Create company first
        await AgentPersistenceService.save_companies([
            {"name": "Nova Tech", "domain": "novatech.co", "industry": "DevTools"}
        ])

        opps = [
            {
                "title": "Lead Python Architect",
                "company": "Nova Tech",
                "source_url": "https://remoteok.com/jobs/123",
                "type": "contract",
                "score": 88,
                "tech_required": ["Python", "FastAPI", "Docker"],
            }
        ]

        saved = await AgentPersistenceService.save_opportunities(opps)
        assert len(saved) == 1
        opp_id = saved[0]["id"]

        async with test_session_factory() as session:
            opp = await session.get(Opportunity, opp_id)
            assert opp is not None
            assert opp.title == "Lead Python Architect"
            assert opp.company_id is not None
            assert opp.score == 88

        # Deduplication update
        opps_update = [
            {
                "source_url": "https://remoteok.com/jobs/123",
                "score": 95,
                "rank": 1,
            }
        ]
        saved_update = await AgentPersistenceService.save_opportunities(opps_update)
        assert len(saved_update) == 1

        async with test_session_factory() as session:
            opp = await session.get(Opportunity, opp_id)
            assert opp.score == 95
            assert opp.rank == 1


@pytest.mark.asyncio
async def test_save_contacts_and_deduplicate(test_session_factory):
    with patch("backend.app.services.agent_persistence.async_session", test_session_factory):
        # Create company
        await AgentPersistenceService.save_companies([
            {"name": "Apex Cloud", "domain": "apexcloud.com"}
        ])

        contacts_data = [
            {
                "company_name": "Apex Cloud",
                "email": "sarah.connor@apexcloud.com",
                "first_name": "Sarah",
                "last_name": "Connor",
                "title": "VP of Engineering",
                "is_decision_maker": True,
            }
        ]

        saved = await AgentPersistenceService.save_contacts(contacts_data)
        assert len(saved) == 1

        async with test_session_factory() as session:
            res = await session.execute(select(Contact).where(Contact.email == "sarah.connor@apexcloud.com"))
            ct = res.scalars().first()
            assert ct is not None
            assert ct.company_id is not None
            assert ct.is_decision_maker is True
            assert ct.title == "VP of Engineering"

        # Update contact
        contacts_update = [
            {
                "email": "sarah.connor@apexcloud.com",
                "title": "Chief Technology Officer",
                "is_decision_maker": True,
            }
        ]
        saved_up = await AgentPersistenceService.save_contacts(contacts_update)
        assert len(saved_up) == 1

        async with test_session_factory() as session:
            res = await session.execute(select(Contact).where(Contact.email == "sarah.connor@apexcloud.com"))
            ct = res.scalars().first()
            assert ct.title == "Chief Technology Officer"


@pytest.mark.asyncio
async def test_save_research_report(test_session_factory):
    with patch("backend.app.services.agent_persistence.async_session", test_session_factory):
        saved_c = await AgentPersistenceService.save_companies([
            {"name": "Cyberdyne", "domain": "cyberdyne.org"}
        ])
        company_id = saved_c[0]["id"]

        report_id = await AgentPersistenceService.save_research_report(
            company_id=company_id,
            report_data={
                "summary": "High growth AI lab with scaling bottlenecks.",
                "fit_score": 93,
                "sources_used": ["LinkedIn", "GitHub"],
                "model_used": "gemini-2.5-flash",
            },
        )

        assert report_id is not None

        async with test_session_factory() as session:
            rep = await session.get(CompanyResearchReport, report_id)
            assert rep is not None
            assert rep.summary == "High growth AI lab with scaling bottlenecks."
            assert str(rep.company_id) == company_id

            comp = await session.get(Company, company_id)
            assert comp.fit_score == 93
            assert comp.status == "researched"
            assert comp.fit_reasoning == "High growth AI lab with scaling bottlenecks."
