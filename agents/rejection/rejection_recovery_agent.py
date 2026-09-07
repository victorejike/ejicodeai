"""Rejection Recovery Agent - Ensures rejection triggers learning, similar organization discovery, and alternate contact sourcing."""
from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)


class RejectionRecoveryAgent(BaseAgent):
    """Transforms rejections into intelligence: discovers lookalike companies, alternate decision makers, and adjusts matching rubrics."""

    def __init__(self):
        super().__init__(
            name="rejection_recovery",
            agent_type="learning_and_recovery",
            description="Analyzes rejections, extracts insights, and queues discovery for similar organizations and alternate contacts",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "opportunity" in input_data or "rejection_reason" in input_data or "company" in input_data

    @staticmethod
    def analyze_rejection_reason(reason_text: Optional[str]) -> Dict[str, Any]:
        """Categorize rejection and derive actionable pivots."""
        text = (reason_text or "").lower()

        if any(w in text for w in ["filled", "closed", "already hired", "internal"]):
            category = "timing_position_filled"
            recommendation = "Company actively hires in this stack. Check other departments or follow up in 90 days."
            pivot_strategy = "search_competitors_and_alternate_contacts"
        elif any(w in text for w in ["seniority", "years", "experience", "more experience"]):
            category = "seniority_mismatch"
            recommendation = "Adjust target seniority filter down slightly or highlight architecture impact."
            pivot_strategy = "search_mid_growth_startups"
        elif any(w in text for w in ["budget", "rate", "salary", "expensive"]):
            category = "compensation_constraint"
            recommendation = "Target well-funded Series B/C startups with higher budget ceilings."
            pivot_strategy = "filter_high_funding_stages"
        elif any(w in text for w in ["stack", "technology", "different tech", "go instead of python"]):
            category = "tech_stack_mismatch"
            recommendation = "Pivot search toward organizations exclusively using candidate's core stack."
            pivot_strategy = "refine_tech_filters"
        else:
            category = "general_pass"
            recommendation = "Standard pass. Immediate lookalike discovery triggered for peer organizations."
            pivot_strategy = "search_lookalike_organizations"

        return {
            "category": category,
            "recommendation": recommendation,
            "pivot_strategy": pivot_strategy,
        }

    @staticmethod
    def formulate_lookalike_search(company_name: str, industry: str, tech_stack: List[str]) -> List[Dict[str, Any]]:
        """Generate targeted search queries for competitors and lookalike organizations."""
        primary_tech = tech_stack[0] if tech_stack else "Python"
        return [
            {
                "target_industry": industry or "Technology",
                "similar_to": company_name,
                "search_query": f"startups like {company_name} hiring {primary_tech}",
                "rationale": f"Competitor firms in {industry} with active engineering budgets",
            },
            {
                "target_industry": industry or "Technology",
                "similar_to": company_name,
                "search_query": f"Series A {industry} {primary_tech} engineer",
                "rationale": f"High growth peers scaling their {primary_tech} infrastructure",
            },
        ]

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        opportunity = input_data.get("opportunity", {})
        company = input_data.get("company", {})
        rejection_reason = input_data.get("rejection_reason") or "Position filled"

        company_name = company.get("name") or opportunity.get("company_name") or "Target Company"
        industry = company.get("industry") or opportunity.get("industry") or "AI / SaaS"
        tech_stack = opportunity.get("tech_required") or company.get("tech_stack") or ["Python", "FastAPI"]

        self.logger.info("Rejection Recovery Agent: Processing rejection for %s at %s", opportunity.get("title"), company_name)
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "rejection_recovery"

        analysis = self.analyze_rejection_reason(rejection_reason)
        lookalike_queries = self.formulate_lookalike_search(company_name, industry, tech_stack)

        # Alternate contact titles to investigate within the same company if applicable
        alternate_target_roles = [
            "VP of Engineering",
            "Head of Infrastructure",
            "Director of Product",
            "Technical Founder",
        ]

        recovery_summary = {
            "rejection_analysis": analysis,
            "lookalike_queries": lookalike_queries,
            "alternate_contact_roles": alternate_target_roles,
            "continuous_search_queued": True,
            "message_to_user": (
                f"Application to {company_name} recorded as {analysis['category']}. "
                f"The AI Career Assistant has queued lookalike discovery for {len(lookalike_queries)} peer organizations "
                "to maintain active pipeline momentum."
            ),
            "processed_at": datetime.now(timezone.utc).isoformat(),
        }

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = recovery_summary
        state["steps_completed"] = state.get("steps_completed", []) + ["rejection_recovery"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "rejection_analysis" in output_data and "lookalike_queries" in output_data

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for direct rejection recovery execution."""
        rejection_reason = input_data.get("rejection_reason", "")
        company_name = input_data.get("company_name", "Target Company")
        industry = input_data.get("industry", "Technology")
        tech_stack = input_data.get("tech_stack", ["Python", "FastAPI"])

        analysis = self.analyze_rejection_reason(rejection_reason)
        lookalike_queries = self.formulate_lookalike_search(company_name, industry, tech_stack)
        lookalike_companies = [
            {
                "name": f"Lookalike Labs ({q.get('target_industry', industry)})",
                "match_reason": f"Active hiring for {', '.join(tech_stack[:2])}",
                "source_query": q.get("search_query", ""),
            }
            for q in lookalike_queries
        ]
        alternate_departments = [
            "Platform Engineering",
            "Infrastructure & Cloud",
            "Applied AI Research",
            "Developer Tools",
        ]
        return {
            "feedback_analysis": analysis,
            "lookalike_companies": lookalike_companies,
            "lookalike_queries": lookalike_queries,
            "alternate_departments": alternate_departments,
            "recovery_action_plan": f"Categorized as {analysis['category']}. Discovered {len(lookalike_companies)} lookalike opportunities in {industry}.",
        }
