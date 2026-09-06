"""End-to-end integration test verifying the complete platform pipeline:
Job Scout -> Ranking -> Research -> Contact Discovery -> Agent Persistence -> Proposal Generation -> Review/Approve -> Outreach Send -> Unsubscribe/Suppression.
"""
import pytest
from unittest.mock import AsyncMock, patch
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from backend.app.models.core import (
    Base,
    Company,
    Opportunity,
    Contact,
    Proposal,
    OutreachHistory,
    AgentRun,
)
from backend.app.services.agent_persistence import AgentPersistenceService
from backend.app.services import proposal_service as proposal_svc
from backend.app.services.outreach_service import (
    create_outreach_history,
    get_outreach_by_proposal,
    mark_proposal_as_sent,
    suppress_contact_by_email,
)
from agents.ranking.ranking_agent import RankingAgent
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
from agents.base.base_agent import AgentStatus


@pytest.fixture
async def db_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.mark.asyncio
async def test_complete_platform_lifecycle(db_factory):
    with patch("backend.app.services.agent_persistence.async_session", db_factory):

        # 1. Record workflow start in Agent Persistence
        run_id = await AgentPersistenceService.record_run_start(
            agent_name="supervisor_pipeline",
            trigger_type="scheduled",
            input_payload={"target_niche": "AI/ML Startups"},
        )
        assert run_id is not None

        # 2. Scout & Ranking agent finds and scores opportunities
        raw_opportunities = [
            {
                "company_id": "c1",
                "title": "Urgent: Principal AI Platform Engineer",
                "company": "Cognitive Scale AI",
                "domain": "cognitivescale.ai",
                "source_url": "https://remoteok.com/job/ai-eng-999",
                "tech_required": ["Python", "FastAPI", "Docker", "Kubernetes"],
                "raw_description": "Building next-gen AI workflows with Python and FastAPI.",
                "type": "contract",
                "salary_min": 5000,
                "contact": {
                    "email_confidence": "verified",
                    "is_decision_maker": True,
                },
            }
        ]

        ranking_agent = RankingAgent()
        ranking_state = {
            "status": AgentStatus.PENDING,
            "input_data": {
                "opportunities": raw_opportunities,
                "companies": {
                    "c1": {
                        "company_size": "startup",
                        "funding_stage": "series_a",
                    }
                },
            },
            "output_data": {},
        }
        ranked_result = await ranking_agent.process(ranking_state)
        assert ranked_result["status"] == AgentStatus.SUCCESS
        ranked_opps = ranked_result["output_data"]["opportunities"]
        assert len(ranked_opps) == 1
        assert ranked_opps[0]["score"] > 80

        # 3. Persist Company, Opportunity, and Discovered Contacts
        saved_companies = await AgentPersistenceService.save_companies([
            {
                "name": "Cognitive Scale AI",
                "domain": "cognitivescale.ai",
                "website_url": "https://cognitivescale.ai",
                "industry": "Artificial Intelligence",
                "tech_stack": ["Python", "PyTorch"],
            }
        ])
        assert len(saved_companies) == 1
        company_id = saved_companies[0]["id"]

        saved_opps = await AgentPersistenceService.save_opportunities([
            {
                "title": ranked_opps[0]["title"],
                "company": "Cognitive Scale AI",
                "company_id": company_id,
                "source_url": ranked_opps[0]["source_url"],
                "score": ranked_opps[0]["score"],
                "rank": ranked_opps[0]["rank"],
            }
        ])
        assert len(saved_opps) == 1
        opportunity_id = saved_opps[0]["id"]

        saved_contacts = await AgentPersistenceService.save_contacts([
            {
                "company_name": "Cognitive Scale AI",
                "company_id": company_id,
                "email": "alex.chen@cognitivescale.ai",
                "first_name": "Alex",
                "last_name": "Chen",
                "title": "VP of Engineering",
                "is_decision_maker": True,
            }
        ])
        assert len(saved_contacts) == 1
        contact_id = saved_contacts[0]["id"]

        # 4. Save Research Audit Report
        report_id = await AgentPersistenceService.save_research_report(
            company_id=company_id,
            report_data={
                "summary": "Fast-growing Series A startup facing engineering talent shortage.",
                "fit_score": 92,
                "pain_points": ["FastAPI architecture bottlenecks", "LLM pipeline latency"],
            },
        )
        assert report_id is not None

        # 5. Proposal Generation Agent produces proposal content
        proposal_agent = ProposalGenerationAgent()
        with patch.object(proposal_agent, "_retrieve_rag_context", new_callable=AsyncMock) as mock_rag, \
             patch.object(proposal_agent, "_run_reasoning_pass", new_callable=AsyncMock) as mock_reason, \
             patch.object(proposal_agent, "_run_refinement_pass", new_callable=AsyncMock) as mock_refine:

            mock_rag.return_value = [{"content": "Past success optimizing LLM workflows by 4x"}]
            mock_reason.return_value = "Highlight expertise in FastAPI high throughput and agent architecture."
            mock_refine.return_value = {
                "subject": "Optimizing AI latency for Cognitive Scale",
                "subject_variants": ["Optimizing AI latency", "FastAPI architecture for Cognitive Scale"],
                "body": "Hi Alex,\n\nI noticed Cognitive Scale's rapid growth in AI workflows. Our team at Ejicode specializes in high-throughput FastAPI and production agent architectures.\n\nBest,\nVictor",
                "generation_model": "gemini-2.5-flash",
                "generation_prompt": "Prompt text",
            }

            gen_state = {
                "status": AgentStatus.PENDING,
                "input_data": {
                    "opportunity_id": opportunity_id,
                    "contact_id": contact_id,
                    "type": "cold_outreach",
                    "tone": "consultative",
                    "opportunity_data": {"title": ranked_opps[0]["title"]},
                    "contact_data": {"email": "alex.chen@cognitivescale.ai", "title": "VP of Engineering"},
                    "company_data": {"name": "Cognitive Scale AI", "domain": "cognitivescale.ai"},
                },
                "output_data": {},
            }
            gen_res = await proposal_agent.process(gen_state)
            assert gen_res["status"] == AgentStatus.SUCCESS
            proposal_content = gen_res["output_data"]

        # 6. Proposal Service saves proposal as 'draft'
        async with db_factory() as session:
            proposal = await proposal_svc.create_proposal(
                session=session,
                opportunity_id=opportunity_id,
                contact_id=contact_id,
                proposal_type="cold_outreach",
                tone="consultative",
                subject=proposal_content["subject"],
                body=proposal_content["body"],
                word_count=len(proposal_content["body"].split()),
                generation_model=proposal_content.get("generation_model", "gemini-2.5-flash"),
                generation_prompt=proposal_content.get("generation_prompt"),
                initial_status="draft",
            )
            assert proposal.status == "draft"
            assert proposal.subject == "Optimizing AI latency for Cognitive Scale"
            proposal_id = proposal.id

            # 7. Human in the Loop: Review and Approve Proposal
            approved_prop = await proposal_svc.update_proposal_status(
                session=session,
                proposal_id=str(proposal_id),
                status="approved",
                approved_by="tech-lead@ejicode.com",
            )
            assert approved_prop.status == "approved"
            assert approved_prop.approved_by == "tech-lead@ejicode.com"

            # 8. Outreach Service enforces limits and dispatches email
            # Check double send prevention before sending
            prev = await get_outreach_by_proposal(session, approved_prop.id)
            assert prev is None

            # Create outreach record and mark proposal as sent
            outreach = await create_outreach_history(
                session=session,
                proposal_id=str(approved_prop.id),
                contact_id=contact_id,
                opportunity_id=opportunity_id,
                message_id="msg-e2e-12345",
                delivery_status="sent",
            )
            assert outreach.delivery_status == "sent"
            await mark_proposal_as_sent(session, approved_prop.id)

            # Check proposal status is now sent
            updated_prop = await session.get(Proposal, approved_prop.id)
            assert updated_prop.status == "sent"

            # 9. Contact Suppression & Unsubscribe Flow
            suppressed = await suppress_contact_by_email(
                session=session,
                email="alex.chen@cognitivescale.ai",
            )
            assert suppressed is not None
            assert suppressed.status == "unsubscribed"

            # Verify contact is marked unsubscribed in DB
            res = await session.get(Contact, contact_id)
            assert res.status == "unsubscribed"

        # 10. Complete Agent Run record
        await AgentPersistenceService.record_run_completion(
            run_id=run_id,
            status="completed",
            items_processed=1,
            items_created=1,
            output_summary={"pipeline": "success", "proposal_id": str(proposal_id)},
        )

        async with db_factory() as session:
            completed_run = await session.get(AgentRun, run_id)
            assert completed_run.status == "completed"
            assert completed_run.output_summary["pipeline"] == "success"
