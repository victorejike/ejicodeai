"""Supervisor Agent - orchestrates all sub-agents."""
import logging
from typing import Dict, Any, List
from datetime import datetime
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from agents.job_scout.job_scout_agent import JobScoutAgent
from agents.company_scout.company_scout_agent import CompanyScoutAgent
from agents.research.research_agent import ResearchAgent
from agents.ranking.ranking_agent import RankingAgent
from agents.contact_discovery.contact_discovery_agent import ContactDiscoveryAgent
from agents.knowledge_base.knowledge_base_agent import KnowledgeBaseAgent
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
from agents.outreach.outreach_agent import OutreachAgent
from agents.reply_monitoring.reply_monitoring_agent import ReplyMonitoringAgent

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Supervisor Agent - coordinates all sub-agents."""
    
    def __init__(self):
        super().__init__(
            name="supervisor",
            agent_type="coordinator",
            description="Central coordinator for multi-agent system",
            max_retries=3,
            timeout_seconds=1800,  # 30 minutes
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
        required_fields = ["trigger_type", "payload"]
        return all(field in input_data for field in required_fields)
    
    async def _route_to_agent(self, agent_name: str, state: AgentState) -> AgentState:
        """Route task to appropriate agent."""
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
        
        # Validate input
        if not await agent.validate_input(state.get("input_data", {})):
            state["status"] = AgentStatus.FAILURE
            state["error_message"] = f"Invalid input for {agent_name}"
            return state
        
        # Execute agent
        try:
            result_state = await agent.process(state)
            
            # Validate output
            if result_state.get("status") == AgentStatus.SUCCESS:
                if not await agent.validate_output(result_state.get("output_data", {})):
                    result_state["status"] = AgentStatus.FAILURE
                    result_state["error_message"] = f"Invalid output from {agent_name}"
            
            return result_state
        except Exception as e:
            logger.error(f"Agent {agent_name} error: {e}")
            state["status"] = AgentStatus.FAILURE
            state["error_message"] = str(e)
            return state
    
    async def _check_escalation(self, state: AgentState) -> bool:
        """Check if result should be escalated to human."""
        confidence_score = state.get("confidence_score", 1.0)
        
        if confidence_score < self.confidence_threshold:
            logger.warning(f"Low confidence score: {confidence_score}, escalating to human")
            return True
        
        return False
    
    async def process(self, state: AgentState) -> AgentState:
        """Orchestrate multi-agent workflow."""
        trigger_type = state.get("input_data", {}).get("trigger_type")
        
        logger.info(f"Supervisor: Processing trigger type: {trigger_type}")
        
        state["status"] = AgentStatus.RUNNING
        state["run_id"] = state.get("run_id", datetime.utcnow().isoformat())
        
        # Define workflows by trigger type
        if trigger_type == "daily_discovery":
            # Run daily discovery workflow
            logger.info("Supervisor: Starting daily discovery workflow")
            
            # 1. Job Scout
            state = await self._route_to_agent("job_scout", state)
            if state.get("status") != AgentStatus.SUCCESS:
                return self._update_state(state, {"status": AgentStatus.FAILURE})
            
            # 2. Company Scout
            state = await self._route_to_agent("company_scout", state)
            if state.get("status") != AgentStatus.SUCCESS:
                return self._update_state(state, {"status": AgentStatus.FAILURE})
            
            # 3. Extract companies and opportunities for next steps
            opportunities = state.get("output_data", {}).get("opportunities", [])
            
            # 4. Ranking (score opportunities)
            ranking_input = {
                "opportunities": opportunities,
                "companies": {},
            }
            state = self._update_state(state, {"input_data": ranking_input})
            state = await self._route_to_agent("ranking", state)
            
            if state.get("status") == AgentStatus.SUCCESS:
                # Get top opportunities for research
                ranked_opps = state.get("output_data", {}).get("opportunities", [])[:5]
                
                # 5. Research top opportunities
                for opp in ranked_opps:
                    company_id = opp.get("company_id")
                    research_input = {"company_id": company_id, "domain": opp.get("domain")}
                    research_state = self._update_state(state, {"input_data": research_input})
                    research_state = await self._route_to_agent("research", research_state)
                    
                    if research_state.get("status") == AgentStatus.SUCCESS:
                        # 6. Discover contacts for researched companies
                        contact_input = {
                            "company_id": company_id,
                            "domain": opp.get("domain"),
                            "company_name": opp.get("company"),
                        }
                        contact_state = self._update_state(state, {"input_data": contact_input})
                        contact_state = await self._route_to_agent("contact_discovery", contact_state)
        
        # Check for escalation
        should_escalate = await self._check_escalation(state)
        if should_escalate:
            state["status"] = AgentStatus.ESCALATED
            state["escalation_reason"] = "Low confidence score"
        
        return state
    
    async def validate_output(self, output_data: dict) -> bool:
        """Validate supervisor output."""
        return "status" in output_data or bool(output_data)
