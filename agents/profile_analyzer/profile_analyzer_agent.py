"""Profile Analyzer Agent - Constructs Candidate Intelligence Profile, Transferable Skill Mapping, and multi-source search strategy."""
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)

# Transferable Role Cluster Mappings
ROLE_TRANSFER_CLUSTERS = {
    "software engineer": [
        "Backend Engineer",
        "Full Stack Engineer",
        "AI Engineer",
        "Python Developer",
        "Go Developer",
        "Platform Engineer",
        "Automation Engineer",
        "ML Engineer",
        "Software Developer",
        "Cloud Infrastructure Engineer",
    ],
    "backend engineer": [
        "Distributed Systems Engineer",
        "API Platform Engineer",
        "Data Engineer",
        "Python Developer",
        "Go Developer",
        "DevOps Engineer",
        "Software Engineer",
    ],
    "ai engineer": [
        "Machine Learning Engineer",
        "LLM Applications Developer",
        "Prompt Systems Engineer",
        "Data Scientist",
        "AI Solutions Architect",
        "Python Developer",
    ],
    "designer": [
        "Product Designer",
        "UI/UX Designer",
        "Design Systems Lead",
        "Visual Designer",
        "Frontend Developer",
    ],
    "data scientist": [
        "Machine Learning Engineer",
        "Data Analyst",
        "Analytics Engineer",
        "Quantitative Developer",
        "AI Engineer",
    ],
}


class ProfileAnalyzerAgent(BaseAgent):
    """Analyzes a candidate's background to build a structured Candidate Intelligence Profile and transferable roles map."""

    def __init__(self):
        super().__init__(
            name="profile_analyzer",
            agent_type="analyzer",
            description="Builds Candidate Intelligence Profile, Transferable Roles, and Multi-Source Search Strategy",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "profile" in input_data or "candidate_profile" in input_data or "user_id" in input_data

    @staticmethod
    def map_transferable_roles(primary_title: str) -> List[str]:
        """Maps candidate title to broad transferable roles across engineering/product domains."""
        title_lower = primary_title.lower().strip()
        for key, transfers in ROLE_TRANSFER_CLUSTERS.items():
            if key in title_lower or title_lower in key:
                return transfers
        return [
            primary_title,
            "Software Engineer",
            "Backend Engineer",
            "Full Stack Developer",
            "Platform Engineer",
        ]

    @staticmethod
    def build_candidate_intelligence_profile(raw_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Construct canonical Candidate Intelligence Profile conforming to EJICODE AI build specification."""
        skills = raw_profile.get("skills", ["Python", "FastAPI", "PostgreSQL", "React", "Docker"])
        title = raw_profile.get("title") or "Software Engineer"
        years = float(raw_profile.get("experience_years", 3.0) or 3.0)

        # Seniority determination
        if years >= 7.0:
            seniority = "Staff / Principal"
        elif years >= 5.0:
            seniority = "Senior"
        elif years >= 2.0:
            seniority = "Mid-Level"
        else:
            seniority = "Junior"

        transferable_roles = ProfileAnalyzerAgent.map_transferable_roles(title)

        return {
            "full_name": raw_profile.get("full_name") or "Candidate",
            "primary_title": title,
            "seniority_level": seniority,
            "skills": skills,
            "transferable_roles": transferable_roles,
            "experience_years": years,
            "experience": raw_profile.get("experience", []),
            "projects": raw_profile.get("projects", []),
            "education": raw_profile.get("education", []),
            "certifications": raw_profile.get("certifications", []),
            "portfolio_url": raw_profile.get("portfolio_url"),
            "github_url": raw_profile.get("github_url"),
            "linkedin_url": raw_profile.get("linkedin_url"),
            "cv_url": raw_profile.get("resume_url"),
            "location": raw_profile.get("location") or "Remote",
            "remote_preference": raw_profile.get("remote_preference") or "remote",
            "salary_expectations": {
                "min": raw_profile.get("salary_min") or 100000,
                "max": raw_profile.get("salary_max") or 160000,
                "currency": raw_profile.get("salary_currency") or "USD",
            },
            "job_preferences": raw_profile.get("job_types") or ["full-time", "contract"],
            "career_goals": raw_profile.get("career_goals") or f"Growth as {seniority} {title}",
            "preferred_industries": raw_profile.get("preferred_industries") or ["AI / SaaS", "Fintech", "Developer Tools"],
            "preferred_companies": raw_profile.get("preferred_companies") or [],
            "availability": raw_profile.get("availability") or "Immediately",
            "professional_strengths": raw_profile.get("professional_strengths") or [
                "Scalable Architecture", "API Engineering", "Autonomous Problem Solving"
            ],
        }

    def analyze_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze profile, map transferable skills, and generate multi-source search matrix."""
        candidate_intel = self.build_candidate_intelligence_profile(profile)
        skills = candidate_intel["skills"]
        transferable = candidate_intel["transferable_roles"]

        # Formulate search queries across transferable roles
        queries = []
        for role in transferable[:4]:
            if skills:
                queries.append(f"{role} {skills[0]}")
            else:
                queries.append(role)

        # Source category priority matrix
        preferred_sources = [
            "linkedin", "indeed", "greenhouse", "lever", "weworkremotely",
            "remoteok", "wellfound", "github", "jobberman"
        ]
        if "contract" in candidate_intel["job_preferences"] or "freelance" in candidate_intel["job_preferences"]:
            preferred_sources.extend(["upwork", "contra", "freelancer", "reddit"])

        return {
            "candidate_intelligence_profile": candidate_intel,
            "transferable_roles": transferable,
            "search_queries": queries,
            "target_sources": preferred_sources,
            "strategic_summary": (
                f"{candidate_intel['seniority_level']} {candidate_intel['primary_title']} "
                f"with {len(skills)} verified core skills. Qualified for {len(transferable)} transferable role types."
            ),
        }

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        profile = input_data.get("profile") or input_data.get("candidate_profile") or {}

        self.logger.info("Profile Analyzer: Building Candidate Intelligence Profile & Transferable Roles")
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "profile_analyzer"

        analysis = self.analyze_profile(profile)

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {
            "analysis": analysis,
            "search_queries": analysis["search_queries"],
            "target_sources": analysis["target_sources"],
            "candidate_profile": analysis["candidate_intelligence_profile"],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        state["steps_completed"] = state.get("steps_completed", []) + ["profile_analyzer"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "analysis" in output_data and "search_queries" in output_data

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for direct execution."""
        profile = input_data.get("profile") or input_data.get("candidate_profile") or input_data
        resume_text = input_data.get("resume_text", "")
        extracted_skills = []
        if resume_text:
            tech_keywords = [
                "Python", "FastAPI", "React", "TypeScript", "JavaScript", "Docker",
                "Kubernetes", "PostgreSQL", "Redis", "AWS", "GCP", "PyTorch",
                "TensorFlow", "LangChain", "GraphQL", "Node.js", "Go", "Rust",
                "Next.js", "SQL", "TailwindCSS", "Celery", "ChromaDB",
            ]
            for kw in tech_keywords:
                if re.search(r"\b" + re.escape(kw) + r"\b", resume_text, re.IGNORECASE):
                    extracted_skills.append(kw)

        if extracted_skills:
            current = profile.get("skills", [])
            profile["skills"] = list(set(current + extracted_skills))

        analysis = self.analyze_profile(profile)
        return {
            "analysis": analysis,
            "extracted_skills": extracted_skills or profile.get("skills", ["Python", "FastAPI"]),
            "candidate_intelligence_profile": analysis["candidate_intelligence_profile"],
            "suggested_titles": analysis["transferable_roles"][:3],
            "experience_years": profile.get("experience_years", 4.0),
            "search_queries": analysis["search_queries"],
            "target_sources": analysis["target_sources"],
        }
