"""LangGraph supervisor graph with isolated state routing and error handling."""
import logging
from typing import Literal
from langgraph.graph import StateGraph, END
from agents.base.base_agent import AgentState, AgentStatus

logger = logging.getLogger(__name__)


async def supervisor_node(state: AgentState) -> AgentState:
    """Determine next step based on workflow stage."""
    steps = state.get("steps_completed", [])
    trigger = state.get("input_data", {}).get("trigger_type", "daily_discovery")

    if trigger == "daily_discovery":
        if "job_scout" not in steps:
            state["next_node"] = "job_scout"
        elif "company_scout" not in steps:
            state["next_node"] = "company_scout"
        elif "ranking" not in steps:
            state["next_node"] = "ranking"
        elif "research" not in steps:
            state["next_node"] = "research"
        else:
            state["next_node"] = "end"
    else:
        state["next_node"] = "end"

    state["current_step"] = "supervisor"
    return state


def route_supervisor(state: AgentState) -> Literal["job_scout", "company_scout", "ranking", "research", "__end__"]:
    next_node = state.get("next_node", "end")
    if next_node == "end":
        return END
    return next_node


async def job_scout_node(state: AgentState) -> AgentState:
    """Run Job Scout Agent and preserve discovered opportunities."""
    try:
        from agents.job_scout.job_scout_agent import JobScoutAgent
        agent = JobScoutAgent()
        result = await agent.process(state)
        opps = result.get("output_data", {}).get("opportunities", [])
        result["job_scout_opportunities"] = opps
        result["steps_completed"] = result.get("steps_completed", []) + ["job_scout"]
        return result
    except Exception as e:
        logger.error(f"Job scout node error: {e}")
        state["steps_completed"] = state.get("steps_completed", []) + ["job_scout"]
        return state


async def company_scout_node(state: AgentState) -> AgentState:
    """Run Company Scout Agent and preserve discovered companies."""
    try:
        from agents.company_scout.company_scout_agent import CompanyScoutAgent
        agent = CompanyScoutAgent()
        result = await agent.process(state)
        companies = result.get("output_data", {}).get("companies", [])
        result["company_scout_companies"] = companies
        result["steps_completed"] = result.get("steps_completed", []) + ["company_scout"]
        return result
    except Exception as e:
        logger.error(f"Company scout node error: {e}")
        state["steps_completed"] = state.get("steps_completed", []) + ["company_scout"]
        return state


async def ranking_node(state: AgentState) -> AgentState:
    """Run Ranking Agent receiving preserved opportunities from job scout."""
    try:
        from agents.ranking.ranking_agent import RankingAgent
        agent = RankingAgent()
        opportunities = state.get("job_scout_opportunities") or state.get("output_data", {}).get("opportunities", [])
        companies = state.get("company_scout_companies") or state.get("output_data", {}).get("companies", [])
        
        state["input_data"] = {
            "opportunities": opportunities,
            "companies": {c.get("name", ""): c for c in companies},
        }
        result = await agent.process(state)
        result["ranking_opportunities"] = result.get("output_data", {}).get("opportunities", opportunities)
        result["steps_completed"] = result.get("steps_completed", []) + ["ranking"]
        return result
    except Exception as e:
        logger.error(f"Ranking node error: {e}")
        state["steps_completed"] = state.get("steps_completed", []) + ["ranking"]
        return state


async def research_node(state: AgentState) -> AgentState:
    """Run Research Agent on top ranked opportunities."""
    try:
        from agents.research.research_agent import ResearchAgent
        opps = state.get("ranking_opportunities") or state.get("job_scout_opportunities") or []
        companies = state.get("company_scout_companies") or []

        domain = ""
        company_id = ""
        if opps:
            top_opp = opps[0]
            domain = top_opp.get("domain") or top_opp.get("company_domain", "")
            company_id = top_opp.get("company_id", "")
        elif companies:
            top_comp = companies[0]
            domain = top_comp.get("domain", "")
            company_id = top_comp.get("id", "")

        state["input_data"] = {"domain": domain, "company_id": company_id}
        agent = ResearchAgent()
        result = await agent.process(state)
        result["steps_completed"] = result.get("steps_completed", []) + ["research"]
        return result
    except Exception as e:
        logger.error(f"Research node error: {e}")
        state["steps_completed"] = state.get("steps_completed", []) + ["research"]
        return state


def build_supervisor_graph():
    """Build LangGraph supervisor graph with real routing."""
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", supervisor_node)
    graph.add_node("job_scout", job_scout_node)
    graph.add_node("company_scout", company_scout_node)
    graph.add_node("ranking", ranking_node)
    graph.add_node("research", research_node)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_supervisor,
        {
            "job_scout": "job_scout",
            "company_scout": "company_scout",
            "ranking": "ranking",
            "research": "research",
            END: END,
        },
    )

    graph.add_edge("job_scout", "supervisor")
    graph.add_edge("company_scout", "supervisor")
    graph.add_edge("ranking", "supervisor")
    graph.add_edge("research", "supervisor")

    return graph.compile()
