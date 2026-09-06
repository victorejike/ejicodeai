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


class TestCrudServiceLayer:
    @pytest.mark.asyncio
    async def test_company_service_crud(self, db):
        from backend.app.services.crud_service import CompanyService
        from backend.app.schemas import CompanyCreate, CompanyUpdate

        # Create
        created = await CompanyService.create(db, CompanyCreate(name="SVC Corp", domain="svccorp.com", industry="Tech"))
        assert created.id is not None
        assert created.domain == "svccorp.com"

        # Get & Get by domain
        by_id = await CompanyService.get(db, created.id)
        assert by_id is not None
        assert by_id.name == "SVC Corp"

        by_dom = await CompanyService.get_by_domain(db, "svccorp.com")
        assert by_dom is not None
        assert by_dom.id == created.id

        # List all
        items, total = await CompanyService.list_all(db)
        assert total >= 1
        assert any(c.domain == "svccorp.com" for c in items)

        # Update
        updated = await CompanyService.update(db, created.id, CompanyUpdate(name="SVC Corp International", fit_score=88))
        assert updated.name == "SVC Corp International"
        assert updated.fit_score == 88

        # Delete
        del_res = await CompanyService.delete(db, created.id)
        assert del_res is True
        assert await CompanyService.get(db, created.id) is None

    @pytest.mark.asyncio
    async def test_opportunity_service_crud(self, db):
        from backend.app.services.crud_service import CompanyService, OpportunityService
        from backend.app.schemas import CompanyCreate, OpportunityCreate, OpportunityUpdate

        comp = await CompanyService.create(db, CompanyCreate(name="Opp Co", domain="oppco.com"))

        opp = await OpportunityService.create(
            db,
            OpportunityCreate(
                company_id=comp.id,
                title="Staff AI Eng",
                type="full_time",
                source_platform="linkedin",
                source_url="https://example.com/opp1",
                score=90,
            ),
        )
        assert opp.id is not None
        assert opp.title == "Staff AI Eng"

        # Get
        retrieved = await OpportunityService.get(db, opp.id)
        assert retrieved is not None

        # List
        items, total = await OpportunityService.list_all(db, company_id=comp.id)
        assert total >= 1

        # Update
        updated = await OpportunityService.update(
            db, opp.id, OpportunityUpdate(status="contacted", score=95)
        )
        assert updated.status == "contacted"
        assert updated.score == 95

        # Delete
        assert await OpportunityService.delete(db, opp.id) is True
        assert await OpportunityService.get(db, opp.id) is None

    @pytest.mark.asyncio
    async def test_contact_service_crud(self, db):
        from backend.app.services.crud_service import CompanyService, ContactService
        from backend.app.schemas import CompanyCreate, ContactCreate, ContactUpdate

        comp = await CompanyService.create(db, CompanyCreate(name="Con Co", domain="conco.com"))

        con = await ContactService.create(
            db,
            ContactCreate(
                company_id=comp.id,
                email="sam@conco.com",
                first_name="Sam",
                title="CTO",
            ),
        )
        assert con.id is not None
        assert con.email == "sam@conco.com"

        # Get by email & ID
        by_email = await ContactService.get_by_email(db, "sam@conco.com")
        assert by_email is not None
        assert by_email.id == con.id

        # Update
        updated = await ContactService.update(db, con.id, ContactUpdate(title="VP Eng"))
        assert updated.title == "VP Eng"

        # Delete
        assert await ContactService.delete(db, con.id) is True
        assert await ContactService.get(db, con.id) is None

    @pytest.mark.asyncio
    async def test_proposal_service_crud(self, db):
        from backend.app.services.crud_service import CompanyService, OpportunityService, ContactService, ProposalService
        from backend.app.schemas import CompanyCreate, OpportunityCreate, ContactCreate, ProposalCreate, ProposalUpdate

        comp = await CompanyService.create(db, CompanyCreate(name="Prop Co 2", domain="propco2.com"))
        opp = await OpportunityService.create(
            db,
            OpportunityCreate(company_id=comp.id, title="Role", type="contract", source_url="https://p2.com"),
        )
        con = await ContactService.create(
            db,
            ContactCreate(company_id=comp.id, email="lead@propco2.com", first_name="Lead"),
        )

        prop = await ProposalService.create(
            db,
            ProposalCreate(
                opportunity_id=opp.id,
                contact_id=con.id,
                type="cold_email",
                subject="Collab",
                body="Let's build AI together.",
            ),
        )
        assert prop.id is not None
        assert prop.status == "draft"

        # Approve
        approved = await ProposalService.approve(db, prop.id, approved_by="admin_operator")
        assert approved.status == "approved"
        assert approved.approved_by == "admin_operator"

        # Update
        updated = await ProposalService.update(db, prop.id, ProposalUpdate(subject="Updated Collab"))
        assert updated.subject == "Updated Collab"

        # Delete
        assert await ProposalService.delete(db, prop.id) is True
        assert await ProposalService.get(db, prop.id) is None

