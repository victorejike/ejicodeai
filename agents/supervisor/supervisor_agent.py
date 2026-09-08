"""Supervisor Agent - orchestrates all sub-agents with state preservation and database persistence."""
from datetime import datetime, timezone
import logging
import time
from typing import Any, Dict, List, Optional

from agents.base.base_agent import AgentState, AgentStatus, BaseAgent
from agents.company_scout.company_scout_agent import CompanyScoutAgent
from agents.contact_discovery.contact_discovery_agent import ContactDiscoveryAgent
from agents.job_scout.job_scout_agent import JobScoutAgent
from agents.knowledge_base.knowledge_base_agent import KnowledgeBaseAgent
from agents.outreach.outreach_agent import OutreachAgent
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
from agents.ranking.ranking_agent import RankingAgent
from agents.reply_monitoring.reply_monitoring_agent import ReplyMonitoringAgent
from backend.app.services.agent_persistence import AgentPersistenceService
from agents.research.research_agent import ResearchAgent

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Supervisor Agent - coordinates all sub-agents."""

    def __init__(self):
        super().__init__(
            name="supervisor",
            agent_type="coordinator",
            description="Central coordinator for multi-agent system",
            max_retries=3,
            timeout_seconds=1800,
        )

        # Initialize sub-agents
        self.job_scout = JobScoutAgent()
        self.company_scout = CompanyScoutAgent()
        self.research = ResearchAgent()
        self.ranking = RankingAgent()
        self.contact_discovery = ContactDiscoveryAgent()
        self.knowledge_base = KnowledgeBaseAgent()
        self.proposal_generation = ProposalGenerationAgent()
        self.outreach = OutreachAgent()
        self.reply_monitoring = ReplyMonitoringAgent()

    async def validate_input(self, input_data: dict) -> bool:
        """Validate supervisor input."""
        required_fields = ["trigger_type"]
        return any(field in input_data for field in required_fields) or bool(input_data)

    async def _route_to_agent(self, agent_name: str, state: AgentState) -> AgentState:
        """Route task to appropriate agent with isolation."""
        logger.info(f"Supervisor: Routing to {agent_name}")

        agents = {
            "job_scout": self.job_scout,
            "company_scout": self.company_scout,
            "research": self.research,
            "ranking": self.ranking,
            "contact_discovery": self.contact_discovery,
            "knowledge_base": self.knowledge_base,
            "proposal_generation": self.proposal_generation,
            "outreach": self.outreach,
            "reply_monitoring": self.reply_monitoring,
        }

        agent = agents.get(agent_name)
        if not agent:
            state["status"] = AgentStatus.FAILURE
            state["error_message"] = f"Unknown agent: {agent_name}"
            return state

        # Execute agent
        start_time = time.monotonic()
        run_id = await AgentPersistenceService.record_run_start(
            agent_name=agent_name,
            trigger_type=state.get("input_data", {}).get("trigger_type", "supervisor"),
            input_payload=state.get("input_data", {}),
        )

        try:
            result_state = await agent.process(state)
            duration_ms = int((time.monotonic() - start_time) * 1000)

            status_str = "completed" if result_state.get("status") in [AgentStatus.SUCCESS, "success"] else "failed"
            out = result_state.get("output_data", {})
            items_proc = len(out.get("opportunities", []) or out.get("companies", []) or out.get("contacts", []) or [1])

            await AgentPersistenceService.record_run_completion(
                run_id=run_id,
                status=status_str,
                duration_ms=duration_ms,
                items_processed=items_proc,
                items_created=items_proc,
                output_summary=out,
                error_message=result_state.get("error_message"),
            )
            return result_state
        except Exception as e:
            duration_ms = int((time.monotonic() - start_time) * 1000)
            logger.error(f"Agent {agent_name} error: {e}")
            await AgentPersistenceService.record_run_completion(
                run_id=run_id,
                status="failed",
                duration_ms=duration_ms,
                error_message=str(e),
            )
            state["status"] = AgentStatus.FAILURE
            state["error_message"] = str(e)
            return state

    async def process(self, state: AgentState) -> AgentState:
        """Orchestrate multi-agent workflow preserving state across stages."""
        trigger_type = state.get("input_data", {}).get("trigger_type", "daily_discovery")
        logger.info(f"Supervisor: Processing trigger type: {trigger_type}")

        start_time = time.monotonic()
        supervisor_run_id = await AgentPersistenceService.record_run_start(
            agent_name="supervisor",
            trigger_type=trigger_type,
            input_payload=state.get("input_data", {}),
        )

        state["status"] = AgentStatus.RUNNING
        state["run_id"] = supervisor_run_id

        # Carried across every stage so the scoring agents work against the real
        # person rather than re-deriving (or inventing) a candidate.
        initial_input = state.get("input_data", {}) or {}
        candidate_profile = initial_input.get("candidate_profile") or initial_input.get("profile") or {}

        discovered_opps: List[Dict[str, Any]] = []
        discovered_companies: List[Dict[str, Any]] = []
        ranked_opps: List[Dict[str, Any]] = []
        researched_count = 0
        contacts_found = 0

        # Step 1: Job Scout
        state = await self._route_to_agent("job_scout", state)
        if state.get("status") in [AgentStatus.SUCCESS, "success"]:
            job_out = state.get("output_data", {})
            discovered_opps = job_out.get("opportunities", [])
            state["job_scout_results"] = job_out
            await AgentPersistenceService.save_opportunities(discovered_opps)
            logger.info(f"Supervisor: Job scout discovered {len(discovered_opps)} opportunities")

        # Step 2: Company Scout
        state = await self._route_to_agent("company_scout", state)
        if state.get("status") in [AgentStatus.SUCCESS, "success"]:
            comp_out = state.get("output_data", {})
            discovered_companies = comp_out.get("companies", [])
            state["company_scout_results"] = comp_out
            await AgentPersistenceService.save_companies(discovered_companies)
            logger.info(f"Supervisor: Company scout discovered {len(discovered_companies)} companies")

        # Step 3: Ranking - Ensure discovered_opps are preserved and scored
        all_opps = discovered_opps or state.get("job_scout_results", {}).get("opportunities", [])
        if all_opps:
            ranking_input = {
                "opportunities": all_opps,
                "companies": {c.get("name", ""): c for c in discovered_companies},
                "candidate_profile": candidate_profile,
            }
            state = self._update_state(state, {"input_data": ranking_input})
            state = await self._route_to_agent("ranking", state)

            if state.get("status") in [AgentStatus.SUCCESS, "success"]:
                rank_out = state.get("output_data", {})
                ranked_opps = rank_out.get("opportunities", all_opps)
                state["ranking_results"] = rank_out
                await AgentPersistenceService.save_opportunities(ranked_opps)

        # Step 4: Research top opportunities / companies
        top_targets = ranked_opps[:5] if ranked_opps else all_opps[:5]
        for opp in top_targets:
            comp_id = opp.get("company_id")
            domain = opp.get("domain") or opp.get("company_domain")
            c_name = opp.get("company") or opp.get("company_name")

            if domain or comp_id or c_name:
                research_input = {"company_id": comp_id, "domain": domain, "company_name": c_name}
                research_state = self._update_state(state, {"input_data": research_input})
                research_state = await self._route_to_agent("research", research_state)

                if research_state.get("status") in [AgentStatus.SUCCESS, "success"]:
                    rep_out = research_state.get("output_data", {})
                    researched_count += 1
                    if comp_id:
                        await AgentPersistenceService.save_research_report(comp_id, rep_out)

                    # Step 5: Contact discovery for researched company
                    contact_input = {
                        "company_id": comp_id,
                        "domain": domain,
                        "company_name": c_name,
                    }
                    contact_state = self._update_state(state, {"input_data": contact_input})
                    contact_state = await self._route_to_agent("contact_discovery", contact_state)

                    if contact_state.get("status") in [AgentStatus.SUCCESS, "success"]:
                        cts = contact_state.get("output_data", {}).get("contacts", [])
                        contacts_found += len(cts)
                        await AgentPersistenceService.save_contacts(cts)

        # Final supervisor aggregation summary
        summary = {
            "trigger_type": trigger_type,
            "opportunities_discovered": len(all_opps),
            "companies_discovered": len(discovered_companies),
            "opportunities_ranked": len(ranked_opps),
            "companies_researched": researched_count,
            "contacts_found": contacts_found,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = summary

        duration_ms = int((time.monotonic() - start_time) * 1000)
        await AgentPersistenceService.record_run_completion(
            run_id=supervisor_run_id,
            status="completed",
            duration_ms=duration_ms,
            items_processed=len(all_opps) + len(discovered_companies),
            items_created=contacts_found + researched_count,
            output_summary=summary,
        )

        return state

    async def validate_output(self, output_data: dict) -> bool:
        """Validate supervisor output."""
        return bool(output_data)
