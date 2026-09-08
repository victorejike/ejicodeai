"""Updated Celery task definitions for Phase 2 agents."""
from celery import shared_task
from backend.tasks.celery_app import celery_app
import logging
import asyncio
from datetime import datetime

logger = logging.getLogger(__name__)


@shared_task
def run_daily_discovery():
    """Run full daily discovery workflow (Job Scout -> Company Scout -> Ranking -> Research -> Contacts)."""
    logger.info("Daily Discovery: Starting full workflow")
    
    try:
        from agents import SupervisorAgent
        from agents.base.base_agent import AgentState, AgentStatus
        
        supervisor = SupervisorAgent()
        
        # Create initial state
        state = {
            "agent_name": "supervisor",
            "run_id": datetime.utcnow().isoformat(),
            "status": AgentStatus.PENDING,
            "timestamp": datetime.utcnow().isoformat(),
            "input_data": {
                "trigger_type": "daily_discovery",
                "payload": {},
            },
            "output_data": {},
            "messages": [],
            "current_step": "initialization",
            "steps_completed": [],
            "error_count": 0,
            "confidence_score": 1.0,
            "quality_checks_passed": True,
            "sub_agent_results": {},
            "dependencies_resolved": True,
        }
        
        # Run supervisor workflow
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result_state = loop.run_until_complete(supervisor.process(state))
        loop.close()
        
        return {
            "status": "completed",
            "run_id": state["run_id"],
            "final_status": result_state.get("status"),
            "results_summary": result_state.get("output_data", {}),
        }
    
    except Exception as e:
        logger.error(f"Daily discovery error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def run_job_scout():
    """Run discovery for every candidate whose profile the agents can work from.

    Search terms come from a user's own title and skills, so there is no such
    thing as a global run: this fans out one scout run per agent-ready user and
    stores each user's own copy of the results.
    """
    logger.info("Job Scout: starting per-candidate discovery")

    try:
        from backend.app.database import async_session
        from backend.app.services.pipeline_dispatch import (
            discover_for_user,
            list_agent_ready_users,
        )

        async def _run_async_task():
            async with async_session() as db:
                candidates = await list_agent_ready_users(db)
                results = []
                for candidate in candidates:
                    try:
                        results.append(await discover_for_user(candidate, db))
                    except Exception as exc:  # one profile must not stop the rest
                        logger.warning("Discovery failed for %s: %s", candidate.user_id, exc)
                        results.append(
                            {"user_id": str(candidate.user_id), "status": "failed", "error": str(exc)}
                        )
                return {
                    "status": "completed",
                    "candidates": len(candidates),
                    "opportunities_found": sum(r.get("found", 0) for r in results),
                    "opportunities_created": sum(r.get("created", 0) for r in results),
                    "results": results,
                }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run_async_task())
        loop.close()
        return result

    except Exception as e:
        logger.error(f"Job Scout error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task(name="backend.tasks.agent_tasks.run_career_pipeline_task")
def run_career_pipeline_task(user_id: str, trigger: str = "scheduled"):
    """Run the full ordered agent chain for one user."""
    logger.info("Career pipeline: starting for user %s (%s)", user_id, trigger)
    try:
        from agents.supervisor.career_pipeline import CareerPipeline

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(CareerPipeline().run(user_id, trigger=trigger))
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Career pipeline error for {user_id}: {e}")
        return {"status": "failed", "user_id": user_id, "error": str(e)}


@shared_task
def fan_out_career_pipelines():
    """Beat entry point: enqueue one pipeline per candidate who opted in.

    Enumerating users here - rather than running one global workflow - is what
    makes the scheduled run produce results tied to each person's own profile.
    Users who switched continuous search off are skipped.
    """
    logger.info("Career pipeline fan-out: enumerating candidates")
    try:
        from backend.app.database import async_session
        from backend.app.services.pipeline_dispatch import list_agent_ready_users

        async def _eligible():
            async with async_session() as db:
                return await list_agent_ready_users(db, require_continuous=True)

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        candidates = loop.run_until_complete(_eligible())
        loop.close()

        queued = []
        for candidate in candidates:
            try:
                run_career_pipeline_task.delay(str(candidate.user_id), "scheduled")
                queued.append(str(candidate.user_id))
            except Exception as exc:  # broker trouble - report rather than crash the beat
                logger.error("Could not enqueue pipeline for %s: %s", candidate.user_id, exc)

        return {"status": "completed", "eligible": len(candidates), "queued": len(queued)}
    except Exception as e:
        logger.error(f"Career pipeline fan-out error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def run_company_scout():
    """Run Company Scout Agent."""
    logger.info("Company Scout: Starting company discovery")
    
    try:
        from agents.company_scout.company_scout_agent import CompanyScoutAgent
        from agents.base.base_agent import AgentStatus
        
        agent = CompanyScoutAgent()
        
        state = {
            "status": AgentStatus.PENDING,
            "input_data": {"trigger_type": "scheduled"},
            "output_data": {},
            "messages": [],
            "current_step": "initialization",
            "steps_completed": [],
            "error_count": 0,
            "confidence_score": 1.0,
            "quality_checks_passed": True,
        }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result_state = loop.run_until_complete(agent.process(state))
        loop.close()
        
        companies = result_state.get("output_data", {}).get("companies", [])
        
        return {
            "status": "completed",
            "companies_found": len(companies),
            "results": companies[:10],
        }
    
    except Exception as e:
        logger.error(f"Company Scout error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def run_research_agent(company_id: str, domain: str):
    """Run Research Agent for specific company."""
    logger.info(f"Research Agent: Starting research for {domain}")
    
    try:
        from agents.research.research_agent import ResearchAgent
        from agents.base.base_agent import AgentStatus
        
        agent = ResearchAgent()
        
        state = {
            "status": AgentStatus.PENDING,
            "input_data": {
                "company_id": company_id,
                "domain": domain,
            },
            "output_data": {},
            "messages": [],
            "current_step": "initialization",
            "steps_completed": [],
            "error_count": 0,
            "confidence_score": 1.0,
        }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result_state = loop.run_until_complete(agent.process(state))
        loop.close()
        
        return {
            "status": "completed",
            "company_id": company_id,
            "report": result_state.get("output_data", {}),
        }
    
    except Exception as e:
        logger.error(f"Research Agent error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def run_ranking_agent(opportunities: list):
    """Run Ranking Agent for opportunity scoring."""
    logger.info(f"Ranking Agent: Scoring {len(opportunities)} opportunities")
    
    try:
        from agents.ranking.ranking_agent import RankingAgent
        from agents.base.base_agent import AgentStatus
        
        agent = RankingAgent()
        
        state = {
            "status": AgentStatus.PENDING,
            "input_data": {
                "opportunities": opportunities,
                "companies": {},
            },
            "output_data": {},
            "messages": [],
            "current_step": "initialization",
            "steps_completed": [],
            "error_count": 0,
            "confidence_score": 1.0,
        }
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result_state = loop.run_until_complete(agent.process(state))
        loop.close()
        
        ranked = result_state.get("output_data", {}).get("opportunities", [])
        
        return {
            "status": "completed",
            "ranked_count": len(ranked),
            "top_opportunity": ranked[0] if ranked else None,
        }
    
    except Exception as e:
        logger.error(f"Ranking Agent error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def generate_proposal_task(opportunity_id: str, contact_id: str, proposal_type: str = "cold_email", tone: str = "professional"):
    """Run Proposal Generation Agent."""
    logger.info(f"Proposal Generation: opportunity={opportunity_id}, contact={contact_id}")
    try:
        from backend.app.database import get_session
        from backend.app.services.proposal_service import get_opportunity, get_contact, get_company, create_proposal
        from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
        from agents.base.base_agent import AgentStatus

        async def _run_async_task():
            async for db in get_session():
                opportunity = await get_opportunity(db, opportunity_id)
                contact = await get_contact(db, contact_id)
                company = await get_company(db, str(opportunity.company_id) if opportunity else None)
                if not opportunity or not contact or not company:
                    return {
                        "status": "failed",
                        "error": "Opportunity, contact, or company not found",
                    }

                agent = ProposalGenerationAgent()
                state = {
                    "status": AgentStatus.PENDING,
                    "input_data": {
                        "opportunity_id": opportunity_id,
                        "contact_id": contact_id,
                        "type": proposal_type,
                        "tone": tone,
                        "opportunity_data": {
                            "title": opportunity.title,
                            "type": opportunity.type,
                            "source_platform": opportunity.source_platform,
                            "raw_description": opportunity.raw_description,
                            "tech_required": opportunity.tech_required,
                        },
                        "contact_data": {
                            "id": str(contact.id),
                            "email": contact.email,
                            "first_name": contact.first_name,
                            "last_name": contact.last_name,
                            "title": contact.title,
                        },
                        "company_data": {
                            "id": str(company.id),
                            "name": company.name,
                            "domain": company.domain,
                            "industry": company.industry,
                            "description": company.description,
                            "tech_stack": company.tech_stack,
                        },
                    },
                    "output_data": {},
                    "messages": [],
                    "current_step": "initialization",
                    "steps_completed": [],
                    "error_count": 0,
                    "confidence_score": 1.0,
                    "quality_checks_passed": True,
                }
                result_state = await agent.process(state)
                if result_state.get("status") != AgentStatus.SUCCESS:
                    return {
                        "status": "failed",
                        "error": result_state.get("error_message", "Proposal generation failed"),
                    }

                output = result_state.get("output_data", {})
                proposal = await create_proposal(
                    db,
                    opportunity_id=opportunity_id,
                    contact_id=contact_id,
                    proposal_type=proposal_type,
                    tone=tone,
                    subject=output.get("subject", "Opportunity from Ejicode"),
                    body=output.get("body", ""),
                    word_count=output.get("word_count", 0),
                    generation_model=output.get("generation_model", ""),
                    generation_prompt=output.get("generation_prompt", ""),
                    rag_context={"items": output.get("rag_context", [])},
                )
                return {
                    "status": "completed",
                    "proposal_id": str(proposal.id),
                    "subject": proposal.subject,
                }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run_async_task())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Proposal Generation error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def send_outreach_task(proposal_id: str):
    """Run Outreach Agent to send an approved proposal."""
    logger.info(f"Outreach send: proposal={proposal_id}")
    try:
        from backend.app.database import get_session
        from backend.app.services.outreach_service import get_proposal, get_contact, get_opportunity, create_outreach_history
        from agents.outreach.outreach_agent import OutreachAgent
        from agents.base.base_agent import AgentStatus

        async def _run_async_task():
            async for db in get_session():
                proposal = await get_proposal(db, proposal_id)
                if not proposal or proposal.status != "approved":
                    return {
                        "status": "failed",
                        "error": "Proposal not found or not approved",
                    }

                contact = await get_contact(db, str(proposal.contact_id))
                opportunity = await get_opportunity(db, str(proposal.opportunity_id))
                if not contact or not opportunity:
                    return {
                        "status": "failed",
                        "error": "Contact or opportunity not found",
                    }

                agent = OutreachAgent()
                state = {
                    "status": AgentStatus.PENDING,
                    "input_data": {
                        "proposal": {
                            "proposal_id": str(proposal.id),
                            "subject": proposal.subject,
                            "body": proposal.body,
                        },
                        "contact": {
                            "id": str(contact.id),
                            "email": contact.email,
                            "first_name": contact.first_name,
                            "last_name": contact.last_name,
                            "title": contact.title,
                        },
                        "opportunity_id": str(opportunity.id),
                    },
                    "output_data": {},
                    "messages": [],
                    "current_step": "initialization",
                    "steps_completed": [],
                    "error_count": 0,
                    "confidence_score": 1.0,
                    "quality_checks_passed": True,
                }

                result_state = await agent.process(state)
                if result_state.get("status") != AgentStatus.SUCCESS:
                    return {
                        "status": "failed",
                        "error": result_state.get("error_message", "Outreach send failed"),
                    }

                output = result_state.get("output_data", {})
                outreach = await create_outreach_history(
                    db,
                    proposal_id=proposal_id,
                    contact_id=str(contact.id),
                    opportunity_id=str(opportunity.id),
                    message_id=output.get("message_id", ""),
                    delivery_status="delivered" if output.get("message_id") else "failed",
                )
                return {
                    "status": "completed",
                    "outreach_id": str(outreach.id),
                    "message_id": outreach.message_id,
                }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run_async_task())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Outreach send error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def monitor_replies_task():
    """Run reply monitoring agent."""
    logger.info("Reply Monitoring: polling for replies")
    try:
        from backend.app.database import get_session
        from backend.app.services.outreach_service import update_outreach_reply
        from agents.reply_monitoring.reply_monitoring_agent import ReplyMonitoringAgent
        from agents.base.base_agent import AgentStatus

        async def _run_async_task():
            async for db in get_session():
                agent = ReplyMonitoringAgent()
                state = {
                    "status": AgentStatus.PENDING,
                    "input_data": {"since": None},
                    "output_data": {},
                    "messages": [],
                    "current_step": "initialization",
                    "steps_completed": [],
                    "error_count": 0,
                    "confidence_score": 1.0,
                }

                result_state = await agent.process(state)
                if result_state.get("status") != AgentStatus.SUCCESS:
                    return {
                        "status": "failed",
                        "error": result_state.get("error_message", "Reply monitoring failed"),
                    }

                replies = result_state.get("output_data", {}).get("replies", [])
                updated_records = []
                for reply in replies:
                    message_id = reply.get("in_reply_to") or reply.get("message_id")
                    if not message_id:
                        continue

                    outreach = await update_outreach_reply(
                        db,
                        message_id=message_id,
                        reply_content=reply.get("content", ""),
                        reply_classification=reply.get("classification", "UNKNOWN"),
                        replied_at=reply.get("received_at"),
                        outcome=reply.get("classification", "UNKNOWN"),
                    )
                    if outreach:
                        updated_records.append({"outreach_id": str(outreach.id), "message_id": outreach.message_id})

                return {
                    "status": "completed",
                    "replies": replies,
                    "updated_records": updated_records,
                }

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(_run_async_task())
        loop.close()
        return result
    except Exception as e:
        logger.error(f"Reply Monitoring error: {e}")
        return {"status": "failed", "error": str(e)}


@shared_task
def generate_daily_report():
    """Generate daily intelligence report."""
    logger.info("Generating daily report")
    
    return {
        "status": "completed",
        "report_type": "daily",
        "timestamp": datetime.utcnow().isoformat(),
    }


@shared_task
def generate_weekly_report():
    """Generate weekly intelligence report."""
    logger.info("Generating weekly report")
    
    return {
        "status": "completed",
        "report_type": "weekly",
        "timestamp": datetime.utcnow().isoformat(),
    }
