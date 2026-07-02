"""Agent package initialization."""
from agents.job_scout.job_scout_agent import JobScoutAgent
from agents.company_scout.company_scout_agent import CompanyScoutAgent
from agents.research.research_agent import ResearchAgent
from agents.ranking.ranking_agent import RankingAgent
from agents.contact_discovery.contact_discovery_agent import ContactDiscoveryAgent
from agents.knowledge_base.knowledge_base_agent import KnowledgeBaseAgent
from agents.proposal_generation.proposal_generation_agent import ProposalGenerationAgent
from agents.outreach.outreach_agent import OutreachAgent
from agents.reply_monitoring.reply_monitoring_agent import ReplyMonitoringAgent
from agents.supervisor.supervisor_agent import SupervisorAgent

__all__ = [
    "JobScoutAgent",
    "CompanyScoutAgent",
    "ResearchAgent",
    "RankingAgent",
    "ContactDiscoveryAgent",
    "KnowledgeBaseAgent",
    "ProposalGenerationAgent",
    "OutreachAgent",
    "ReplyMonitoringAgent",
    "SupervisorAgent",
]
