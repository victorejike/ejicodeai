"""Tests for CRUD operations using actual ORM models."""
import os
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.app.models.core import Base, Company, Opportunity, Contact


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


class TestCompanyModel:

    @pytest.mark.asyncio
    async def test_create_company(self, db):
        c = Company(name="Test Corp", domain="testcorp.com", industry="Technology")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        assert c.id is not None
        assert c.name == "Test Corp"
        assert c.domain == "testcorp.com"

    @pytest.mark.asyncio
    async def test_get_company(self, db):
        c = Company(name="Test Corp", domain="testcorp.com")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        retrieved = await db.get(Company, c.id)
        assert retrieved is not None
        assert retrieved.name == "Test Corp"

    @pytest.mark.asyncio
    async def test_update_company(self, db):
        c = Company(name="Test Corp", domain="testcorp.com")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        c.name = "Updated Corp"
        c.fit_score = 85
        await db.commit()
        await db.refresh(c)
        assert c.name == "Updated Corp"
        assert c.fit_score == 85

    @pytest.mark.asyncio
    async def test_delete_company(self, db):
        c = Company(name="Test Corp", domain="testcorp.com")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        cid = c.id
        await db.delete(c)
        await db.commit()
        assert await db.get(Company, cid) is None

    @pytest.mark.asyncio
    async def test_company_defaults(self, db):
        c = Company(name="Test Corp")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        assert c.status == "discovered"
        assert c.fit_score == 0


class TestOpportunityModel:

    @pytest.mark.asyncio
    async def test_create_opportunity(self, db):
        o = Opportunity(title="Senior Engineer Role", type="job")
        db.add(o)
        await db.commit()
        await db.refresh(o)
        assert o.id is not None
        assert o.title == "Senior Engineer Role"
        assert o.status == "new"

    @pytest.mark.asyncio
    async def test_update_opportunity_status(self, db):
        o = Opportunity(title="Senior Engineer Role", type="job")
        db.add(o)
        await db.commit()
        await db.refresh(o)
        o.status = "contacted"
        await db.commit()
        await db.refresh(o)
        assert o.status == "contacted"


class TestContactModel:

    @pytest.mark.asyncio
    async def test_create_contact(self, db):
        c = Contact(email="john@example.com", first_name="John", last_name="Doe", title="CTO")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        assert c.id is not None
        assert c.email == "john@example.com"
        assert c.status == "active"

    @pytest.mark.asyncio
    async def test_contact_default_confidence(self, db):
        c = Contact(email="jane@example.com")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        assert c.email_confidence == "unverified"

    @pytest.mark.asyncio
    async def test_update_contact(self, db):
        c = Contact(email="john@example.com", first_name="John")
        db.add(c)
        await db.commit()
        await db.refresh(c)
        c.title = "VP Engineering"
        c.is_decision_maker = True
        await db.commit()
        await db.refresh(c)
        assert c.title == "VP Engineering"
        assert c.is_decision_maker is True
