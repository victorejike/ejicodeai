"""Profile Analyzer Agent - Analyzes candidate profile and formulates targeted multi-source search strategies."""
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)


class ProfileAnalyzerAgent(BaseAgent):
    """Analyzes a candidate's background to build an optimal discovery search strategy."""

    def __init__(self):
        super().__init__(
            name="profile_analyzer",
            agent_type="analyzer",
            description="Analyzes individual candidate profile to formulate targeted search strategies",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "profile" in input_data or "candidate_profile" in input_data or "user_id" in input_data

    @staticmethod
    def analyze_profile(profile: Dict[str, Any]) -> Dict[str, Any]:
        """Extract core keywords, seniority, niche, and targeted search queries."""
        skills = profile.get("skills", [])
        title = profile.get("title") or "Software Engineer"
        years = profile.get("experience_years", 3.0)

        # Seniority label
        if years >= 7.0:
            seniority = "Staff / Principal"
        elif years >= 5.0:
            seniority = "Senior"
        elif years >= 2.0:
            seniority = "Mid-Level"
        else:
            seniority = "Junior"

        # Formulate search queries
        top_skills = skills[:3] if skills else ["Python", "FastAPI"]
        primary_query = f"{top_skills[0]} {title}" if top_skills else title
        secondary_query = f"{seniority} {top_skills[0]} Engineer" if top_skills else title
        contract_query = f"{top_skills[0]} contract developer" if top_skills else "software contract"

        target_sources = ["linkedin", "indeed", "github", "google_search"]
        job_types = profile.get("job_types") or ["full-time", "contract"]
        if "freelance" in job_types or "contract" in job_types:
            target_sources.extend(["upwork", "reddit", "freelancer"])

        return {
            "candidate_name": profile.get("full_name") or "Candidate",
            "seniority_level": seniority,
            "core_skills": skills,
            "primary_niche": f"{seniority} {title} ({', '.join(top_skills)})",
            "search_queries": [primary_query, secondary_query, contract_query],
            "target_sources": target_sources,
            "location_preference": profile.get("remote_preference", "remote"),
            "salary_expectation": {
                "min": profile.get("salary_min"),
                "max": profile.get("salary_max"),
                "currency": profile.get("salary_currency", "USD"),
            },
        }

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        profile = input_data.get("profile") or input_data.get("candidate_profile") or {}

        self.logger.info("Profile Analyzer: Analyzing candidate profile")
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "profile_analyzer"

        analysis = self.analyze_profile(profile)

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {
            "analysis": analysis,
            "search_queries": analysis["search_queries"],
            "target_sources": analysis["target_sources"],
            "candidate_profile": profile,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        state["steps_completed"] = state.get("steps_completed", []) + ["profile_analyzer"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "analysis" in output_data and "search_queries" in output_data

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for direct profile analysis execution."""
        profile = input_data.get("profile") or input_data.get("candidate_profile") or input_data
        resume_text = input_data.get("resume_text", "")
        extracted_skills = []
        if resume_text:
            tech_keywords = [
                "Python", "FastAPI", "React", "TypeScript", "JavaScript", "Docker",
                "Kubernetes", "PostgreSQL", "Redis", "AWS", "GCP", "PyTorch",
                "TensorFlow", "LangChain", "GraphQL", "Node.js", "Go", "Rust",
            ]
            for kw in tech_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", resume_text, re.IGNORECASE):
                    extracted_skills.append(kw)
        
        analysis = self.analyze_profile(profile)
        return {
            "analysis": analysis,
            "extracted_skills": extracted_skills or profile.get("skills", ["Python", "FastAPI"]),
            "suggested_titles": [profile.get("title") or "Senior Software Engineer", "Full-Stack AI Architect"],
            "experience_years": profile.get("experience_years", 4.0),
            "search_queries": analysis.get("search_queries", []),
            "target_sources": analysis.get("target_sources", []),
        }
