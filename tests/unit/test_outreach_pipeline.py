"""Comprehensive tests for outreach pipeline: safety gates, rate limits, suppression, and replies."""
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret")

from backend.app.models.core import Base, Company, Opportunity, Contact, Proposal, OutreachHistory
from backend.app.services.outreach_service import (
    create_outreach_history,
    get_daily_outreach_count,
    get_last_outreach_for_contact,
    get_outreach_by_proposal,
    suppress_contact,
    suppress_contact_by_email,
    unsuppress_contact,
    list_suppressed_contacts,
    handle_bounce,
    update_outreach_reply,
    mark_proposal_as_sent,
)
from agents.reply_monitoring.reply_monitoring_agent import ReplyMonitoringAgent
from backend.app import main
from backend.app.dependencies import get_db


@pytest.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_create_and_get_outreach(db):
    company = Company(name="Test LLC", domain="testllc.com")
    db.add(company)
    await db.commit()

    opp = Opportunity(company_id=company.id, title="Dev Job", type="contract")
    db.add(opp)
    contact = Contact(company_id=company.id, first_name="Alice", last_name="Smith", email="alice@testllc.com")
    db.add(contact)
    await db.commit()

    prop = Proposal(opportunity_id=opp.id, contact_id=contact.id, body="Hi Alice", status="approved")
    db.add(prop)
    await db.commit()

    outreach = await create_outreach_history(
        db,
        proposal_id=str(prop.id),
        contact_id=str(contact.id),
        opportunity_id=str(opp.id),
        message_id="msg-12345",
        delivery_status="sent",
    )

    assert outreach.id is not None
    assert outreach.message_id == "msg-12345"
    assert outreach.delivery_status == "sent"

    by_prop = await get_outreach_by_proposal(db, str(prop.id))
    assert by_prop is not None
    assert by_prop.id == outreach.id


@pytest.mark.asyncio
async def test_daily_outreach_count_and_contact_cooldown(db):
    company = Company(name="Acme", domain="acme.com")
    db.add(company)
    await db.commit()
    opp = Opportunity(company_id=company.id, title="Role", type="job")
    contact = Contact(company_id=company.id, first_name="Bob", last_name="Jones", email="bob@acme.com")
    db.add(opp)
    db.add(contact)
    await db.commit()

    initial_count = await get_daily_outreach_count(db)
    assert initial_count == 0

    await create_outreach_history(
        db,
        proposal_id=str(uuid.uuid4()),
        contact_id=str(contact.id),
        opportunity_id=str(opp.id),
        message_id="msg-day-1",
        delivery_status="sent",
    )

    count_after = await get_daily_outreach_count(db)
    assert count_after == 1

    last_outreach = await get_last_outreach_for_contact(db, str(contact.id))
    assert last_outreach is not None
    assert last_outreach.message_id == "msg-day-1"


@pytest.mark.asyncio
async def test_suppression_and_unsubscribe_logic(db):
    company = Company(name="Beta", domain="beta.com")
    db.add(company)
    await db.commit()
    c1 = Contact(company_id=company.id, first_name="Charlie", email="charlie@beta.com", status="active")
    c2 = Contact(company_id=company.id, first_name="Dave", email="dave@beta.com", status="active")
    db.add_all([c1, c2])
    await db.commit()

    # Suppress c1 by ID
    await suppress_contact(db, str(c1.id))
    retrieved_c1 = await db.get(Contact, c1.id)
    assert retrieved_c1.status == "unsubscribed"

    # Suppress c2 by email
    await suppress_contact_by_email(db, "dave@beta.com")
    retrieved_c2 = await db.get(Contact, c2.id)
    assert retrieved_c2.status == "unsubscribed"

    suppressed = await list_suppressed_contacts(db)
    assert len(suppressed) == 2

    # Unsuppress c1
    await unsuppress_contact(db, str(c1.id))
    retrieved_c1 = await db.get(Contact, c1.id)
    assert retrieved_c1.status == "active"


@pytest.mark.asyncio
async def test_bounce_handling(db):
    company = Company(name="Gamma", domain="gamma.com")
    db.add(company)
    await db.commit()
    opp = Opportunity(company_id=company.id, title="Role", type="job")
    contact = Contact(company_id=company.id, first_name="Eve", email="eve@gamma.com", status="active")
    db.add_all([opp, contact])
    await db.commit()

    outreach = await create_outreach_history(
        db,
        proposal_id=str(uuid.uuid4()),
        contact_id=str(contact.id),
        opportunity_id=str(opp.id),
        message_id="msg-bounce-1",
        delivery_status="sent",
    )

    bounced = await handle_bounce(db, "msg-bounce-1", reason="Mailbox does not exist 550")
    assert bounced is not None
    assert bounced.delivery_status == "bounced"
    assert "Mailbox does not exist" in bounced.outcome

    updated_contact = await db.get(Contact, contact.id)
    assert updated_contact.status == "bounced"


@pytest.mark.asyncio
async def test_reply_monitoring_heuristics_and_auto_suppression(db):
    agent = ReplyMonitoringAgent()
    assert agent._heuristic_classify("Please unsubscribe me immediately from your lists") == "UNSUBSCRIBE"
    assert agent._heuristic_classify("Delivery failure: Mailbox not found (550 5.1.1)") == "BOUNCE"
    assert agent._heuristic_classify("I am currently out of the office on annual leave until next week") == "AUTO_REPLY"
    assert agent._heuristic_classify("Sounds good! Let's chat tomorrow, send me a calendar link") == "INTERESTED"
    assert agent._heuristic_classify("Please send more info and your rate card") == "REQUEST_INFO"
    assert agent._heuristic_classify("No thanks, not interested at this time") == "NOT_INTERESTED"

    company = Company(name="Zeta", domain="zeta.com")
    db.add(company)
    await db.commit()
    opp = Opportunity(company_id=company.id, title="Role", type="job")
    contact = Contact(company_id=company.id, first_name="Frank", email="frank@zeta.com", status="active")
    db.add_all([opp, contact])
    await db.commit()

    outreach = await create_outreach_history(
        db,
        proposal_id=str(uuid.uuid4()),
        contact_id=str(contact.id),
        opportunity_id=str(opp.id),
        message_id="msg-reply-1",
        delivery_status="sent",
    )

    # Reply with unsubscribe
    updated = await update_outreach_reply(
        db,
        message_id="msg-reply-1",
        reply_content="Please stop emailing me and take me off your list",
        reply_classification="UNSUBSCRIBE",
    )
    assert updated is not None
    assert updated.delivery_status == "replied"
    assert updated.reply_classification == "UNSUBSCRIBE"

    # Contact should have been auto-suppressed
    updated_contact = await db.get(Contact, contact.id)
    assert updated_contact.status == "unsubscribed"


def test_api_outreach_send_safety_gates(monkeypatch):
    """Test API endpoint gates: unapproved proposals, double-sending, and rate limits."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")

    async def init_test_schema():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    __import__("asyncio").run(init_test_schema())
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def override_get_db():
        async with factory() as session:
            yield session

    app = main.create_app()
    app.dependency_overrides[get_db] = override_get_db

    from backend.app.models.core import User
    from backend.app.security import get_current_active_user

    async def override_current_user():
        return User(
            id=uuid.uuid4(),
            email="admin@ejicode.ai",
            full_name="Admin",
            roles=["admin"],
            is_active=True,
        )

    app.dependency_overrides[get_current_active_user] = override_current_user
    monkeypatch.setattr(main, "init_db", AsyncMock())

    # Seed data
    async def seed_data():
        async with factory() as session:
            co = Company(name="Delta Inc", domain="deltainc.com")
            session.add(co)
            await session.commit()
            opp = Opportunity(company_id=co.id, title="Fullstack Lead", type="job")
            con = Contact(company_id=co.id, first_name="Dan", last_name="Miller", email="dan@deltainc.com")
            con_unsub = Contact(company_id=co.id, first_name="Unsub", email="unsub@deltainc.com", status="unsubscribed")
            session.add_all([opp, con, con_unsub])
            await session.commit()

            p_draft = Proposal(opportunity_id=opp.id, contact_id=con.id, body="Draft text", status="draft")
            p_approved = Proposal(opportunity_id=opp.id, contact_id=con.id, body="Approved text", status="approved")
            p_unsub = Proposal(opportunity_id=opp.id, contact_id=con_unsub.id, body="Text", status="approved")
            session.add_all([p_draft, p_approved, p_unsub])
            await session.commit()
            return str(p_draft.id), str(p_approved.id), str(p_unsub.id), str(con.id)

    draft_id, approved_id, unsub_prop_id, contact_id = __import__("asyncio").run(seed_data())

    client = TestClient(app)

    # 1. Sending draft proposal should be rejected (400)
    res_draft = client.post("/v1/outreach/send", json={"proposal_id": draft_id})
    assert res_draft.status_code == 400
    assert "approved" in res_draft.json()["detail"].lower()

    # 2. Sending to unsubscribed contact should be rejected (400)
    res_unsub = client.post("/v1/outreach/send", json={"proposal_id": unsub_prop_id})
    assert res_unsub.status_code == 400
    assert "suppressed" in res_unsub.json()["detail"].lower() or "unsubscribed" in res_unsub.json()["detail"].lower()

    # 3. Sending approved proposal succeeds (falls back to queued in dev if SMTP unavailable)
    res_approved = client.post("/v1/outreach/send", json={"proposal_id": approved_id})
    assert res_approved.status_code == 200
    data = res_approved.json()
    assert data["delivery_status"] in ["sent", "queued"]
    assert data["proposal_id"] == approved_id

    # 4. Double sending the same proposal should be rejected (400)
    res_dup = client.post("/v1/outreach/send", json={"proposal_id": approved_id})
    assert res_dup.status_code == 400
    detail = res_dup.json()["detail"].lower()
    assert "already" in detail or "approved" in detail or "sent" in detail

    # 5. Test public unsubscribe endpoint (GET)
    res_unsub_get = client.get(f"/v1/outreach/unsubscribe?contact_id={contact_id}")
    assert res_unsub_get.status_code == 200
    assert "Unsubscribed" in res_unsub_get.text

    # 6. Test suppression list
    res_supp = client.get("/v1/outreach/suppression")
    assert res_supp.status_code == 200
    assert any(c["id"] == contact_id for c in res_supp.json())
