"""Unit tests for Organization, UserProfile, Candidate, WorkflowExecution, RejectionLog, and FollowUpSchedule models."""
import pytest
from datetime import datetime, timedelta, timezone
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

from backend.app.models.core import (
    Base,
    User,
    Organization,
    OrganizationMember,
    UserProfile,
    Candidate,
    WorkflowExecution,
    WorkflowStep,
    RejectionLog,
    FollowUpSchedule,
    PasswordResetToken,
    Company,
    Opportunity,
    Contact,
    Proposal,
    OutreachHistory,
)


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
async def test_organization_and_membership(db: AsyncSession):
    user = User(
        email="owner@ejicorp.com",
        username="org_owner",
        hashed_password="hash",
        full_name="Alex Morgan",
        account_type="enterprise",
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    org = Organization(
        name="Ejicode Enterprise",
        slug="ejicode-ent",
        domain="ejicode.com",
        plan="enterprise",
        billing_email="billing@ejicode.com",
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role="owner",
        permissions=["admin", "recruiter", "billing"],
    )
    db.add(member)
    await db.commit()

    res = await db.execute(select(OrganizationMember).where(OrganizationMember.organization_id == org.id))
    members = res.scalars().all()
    assert len(members) == 1
    assert members[0].role == "owner"
    assert "recruiter" in members[0].permissions


@pytest.mark.asyncio
async def test_individual_user_profile(db: AsyncSession):
    user = User(
        email="candidate@dev.io",
        username="jane_dev",
        hashed_password="hash",
        account_type="individual",
    )
    db.add(user)
    await db.commit()

    profile = UserProfile(
        user_id=user.id,
        full_name="Jane Developer",
        title="Senior AI Platform Engineer",
        bio="Specializing in FastAPI, PyTorch, and distributed agent workflows.",
        skills=["Python", "FastAPI", "Docker", "PyTorch", "Kubernetes"],
        experience_years=6.5,
        portfolio_url="https://janedev.me",
        github_url="https://github.com/janedev",
        linkedin_url="https://linkedin.com/in/janedev",
        remote_preference="remote",
        salary_min=140000,
        salary_max=180000,
        salary_currency="USD",
        technologies=["Python", "PostgreSQL", "ChromaDB"],
        career_goals="Lead AI architecture at a high-growth tech startup.",
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    assert profile.id is not None
    assert profile.full_name == "Jane Developer"
    assert "PyTorch" in profile.skills
    assert profile.salary_min == 140000


@pytest.mark.asyncio
async def test_candidate_pipeline(db: AsyncSession):
    org = Organization(name="Tech Talent Inc", slug="techtalent")
    db.add(org)
    await db.commit()

    cand = Candidate(
        organization_id=org.id,
        full_name="David Chen",
        email="david@talent.com",
        title="Lead Go Architect",
        skills=["Go", "Microservices", "gRPC", "Docker"],
        status="screening",
        match_score=92,
        match_explanation="92% match on Go, gRPC, and high-concurrency requirements.",
        source="ai_scout",
    )
    db.add(cand)
    await db.commit()
    await db.refresh(cand)

    assert cand.id is not None
    assert cand.status == "screening"
    assert cand.match_score == 92


@pytest.mark.asyncio
async def test_workflow_execution_and_step_locking(db: AsyncSession):
    wf = WorkflowExecution(
        workflow_type="individual_career_engine",
        status="running",
        current_step="discovery",
        lock_token="lock-token-abc-123",
        input_params={"target_role": "Python Staff Engineer"},
    )
    db.add(wf)
    await db.commit()
    await db.refresh(wf)

    step1 = WorkflowStep(
        workflow_execution_id=wf.id,
        agent_name="profile_analyzer",
        step_index=1,
        status="completed",
        output_data={"niche": "AI Platform"},
    )
    step2 = WorkflowStep(
        workflow_execution_id=wf.id,
        agent_name="discovery",
        step_index=2,
        status="running",
        input_data={"niche": "AI Platform"},
    )
    db.add_all([step1, step2])
    await db.commit()

    res = await db.execute(select(WorkflowStep).where(WorkflowStep.workflow_execution_id == wf.id).order_by(WorkflowStep.step_index))
    steps = res.scalars().all()
    assert len(steps) == 2
    assert steps[0].status == "completed"
    assert steps[1].status == "running"


@pytest.mark.asyncio
async def test_rejection_recovery_tracking(db: AsyncSession):
    comp = Company(name="CloudCorp", domain="cloudcorp.io")
    db.add(comp)
    await db.commit()

    opp = Opportunity(company_id=comp.id, title="Backend Lead", type="contract")
    contact = Contact(company_id=comp.id, email="recruiter@cloudcorp.io")
    db.add_all([opp, contact])
    await db.commit()

    rejection = RejectionLog(
        opportunity_id=opp.id,
        contact_id=contact.id,
        rejection_source="recipient_reply",
        rejection_reason="Position filled internally",
        feedback_analysis={"recommendation": "Search for Series A competitors needing similar stack"},
        similar_search_triggered=True,
        similar_organizations_found=["ScaleAI Inc", "DataFlow Labs"],
        alternate_contacts_found=["cto@cloudcorp.io"],
    )
    db.add(rejection)
    await db.commit()
    await db.refresh(rejection)

    assert rejection.id is not None
    assert rejection.similar_search_triggered is True
    assert len(rejection.similar_organizations_found) == 2


@pytest.mark.asyncio
async def test_follow_up_schedule_lifecycle(db: AsyncSession):
    comp = Company(name="TargetCo", domain="targetco.com")
    db.add(comp)
    await db.commit()

    opp = Opportunity(company_id=comp.id, title="Dev Job", type="contract")
    contact = Contact(company_id=comp.id, email="lead@targetco.com")
    db.add_all([opp, contact])
    await db.commit()

    prop = Proposal(opportunity_id=opp.id, contact_id=contact.id, body="Pitch", status="approved")
    db.add(prop)
    await db.commit()

    outreach = OutreachHistory(
        proposal_id=prop.id,
        contact_id=contact.id,
        opportunity_id=opp.id,
        delivery_status="sent",
    )
    db.add(outreach)
    await db.commit()

    # Schedule Day 3 follow-up
    sched = FollowUpSchedule(
        outreach_id=outreach.id,
        contact_id=contact.id,
        proposal_id=prop.id,
        sequence_step=1,
        delay_days=3,
        scheduled_for=datetime.now(timezone.utc) + timedelta(days=3),
        status="scheduled",
        subject="Re: Pitch - quick follow up",
        body_draft="Hi, following up on our previous conversation...",
    )
    db.add(sched)
    await db.commit()
    await db.refresh(sched)

    assert sched.id is not None
    assert sched.status == "scheduled"
    assert sched.sequence_step == 1


@pytest.mark.asyncio
async def test_password_reset_token(db: AsyncSession):
    user = User(email="user@ejicode.com", username="pwd_user", hashed_password="pwd")
    db.add(user)
    await db.commit()

    token = PasswordResetToken(
        user_id=user.id,
        token_hash="hashed-secure-reset-token-xyz",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
        used=False,
    )
    db.add(token)
    await db.commit()
    await db.refresh(token)

    assert token.id is not None
    assert token.used is False
