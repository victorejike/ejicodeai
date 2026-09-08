"""Profile Analyzer Agent - Constructs Candidate Intelligence Profile, Transferable Skill Mapping, and multi-source search strategy.

Nothing here substitutes data the candidate did not give us. A missing title stays
``None``, missing skills stay ``[]``, and the gaps are reported in
``missing_fields`` so the UI can ask the user for them - a made-up default would
silently send every candidate hunting for the same jobs.
"""
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional

from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from agents.base.skill_vocabulary import canonicalize, extract_skills

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

#: Seniority words stripped from a title to widen the search, and the synonyms we
#: broaden into. Used only when the title has no cluster of its own, so an
#: accountant or a nurse gets accountant/nurse variants - not engineer titles.
SENIORITY_PREFIXES = (
    "senior", "snr", "sr", "junior", "jr", "lead", "principal", "staff",
    "head of", "chief", "entry level", "entry-level", "mid-level", "mid level",
    "associate", "trainee", "graduate", "intern",
)

#: Interchangeable role nouns, applied to whatever domain the title names.
ROLE_SYNONYMS = {
    "engineer": ["Developer", "Specialist"],
    "developer": ["Engineer", "Programmer"],
    "designer": ["Design Lead"],
    "analyst": ["Specialist", "Consultant"],
    "manager": ["Lead", "Head"],
    "specialist": ["Analyst", "Consultant"],
    "consultant": ["Specialist", "Advisor"],
    "administrator": ["Coordinator", "Officer"],
    "coordinator": ["Administrator", "Officer"],
    "writer": ["Copywriter", "Content Specialist"],
    "nurse": ["Registered Nurse", "Clinical Nurse"],
    "accountant": ["Financial Accountant", "Finance Analyst"],
    "teacher": ["Instructor", "Tutor"],
    "marketer": ["Marketing Specialist", "Growth Marketer"],
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
    def map_transferable_roles(primary_title: Optional[str]) -> List[str]:
        """Roles adjacent to the candidate's own title.

        Known clusters are used first. Otherwise the title itself is widened -
        seniority stripped, role noun swapped for its synonyms - which keeps the
        result inside the candidate's actual profession.
        """
        if not primary_title or not str(primary_title).strip():
            return []

        title = str(primary_title).strip()
        title_lower = title.lower()
        for key, transfers in ROLE_TRANSFER_CLUSTERS.items():
            if key in title_lower or title_lower in key:
                return transfers

        roles = [title]

        base = title_lower
        for prefix in SENIORITY_PREFIXES:
            if base.startswith(prefix + " "):
                base = base[len(prefix) + 1:].strip()
                break
        stripped = base.title()
        if stripped and stripped.lower() != title_lower:
            roles.append(stripped)

        words = re.split(r"\s+", base)
        if words:
            noun = words[-1].rstrip("s")
            for synonym in ROLE_SYNONYMS.get(noun, []):
                domain = " ".join(words[:-1]).title().strip()
                candidate = f"{domain} {synonym}".strip()
                if candidate.lower() not in {r.lower() for r in roles}:
                    roles.append(candidate)

        return roles

    @staticmethod
    def derive_seniority(years: Optional[float]) -> Optional[str]:
        """Seniority band, or None when the candidate has not told us their years."""
        if years is None:
            return None
        if years >= 7.0:
            return "Staff / Principal"
        if years >= 5.0:
            return "Senior"
        if years >= 2.0:
            return "Mid-Level"
        return "Junior"

    @staticmethod
    def build_candidate_intelligence_profile(raw_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Construct canonical Candidate Intelligence Profile conforming to EJICODE AI build specification.

        Every field mirrors the candidate's own data. Unknown values are ``None``
        or empty and listed in ``missing_fields``.
        """
        raw_profile = raw_profile or {}
        skills = canonicalize(raw_profile.get("skills"))
        title = (raw_profile.get("title") or "").strip() or None

        years_raw = raw_profile.get("experience_years")
        try:
            years = float(years_raw) if years_raw not in (None, "") else None
        except (TypeError, ValueError):
            years = None

        seniority = ProfileAnalyzerAgent.derive_seniority(years)
        transferable_roles = ProfileAnalyzerAgent.map_transferable_roles(title)

        salary_min = raw_profile.get("salary_min")
        salary_max = raw_profile.get("salary_max")

        missing_fields = [
            key
            for key, value in (
                ("full_name", raw_profile.get("full_name")),
                ("title", title),
                ("skills", skills),
                ("experience_years", years),
                ("experience", raw_profile.get("experience")),
                ("education", raw_profile.get("education")),
                ("location", raw_profile.get("location") or raw_profile.get("remote_preference")),
                ("career_goals", raw_profile.get("career_goals")),
                ("salary_expectations", salary_min or salary_max),
            )
            if not value
        ]

        return {
            "user_id": raw_profile.get("user_id"),
            "full_name": raw_profile.get("full_name") or None,
            "primary_title": title,
            "seniority_level": seniority,
            "skills": skills,
            "technologies": canonicalize(raw_profile.get("technologies")),
            "transferable_roles": transferable_roles,
            "experience_years": years,
            "experience": raw_profile.get("experience") or [],
            "projects": raw_profile.get("projects") or [],
            "education": raw_profile.get("education") or [],
            "certifications": raw_profile.get("certifications") or [],
            "bio": raw_profile.get("bio") or None,
            "portfolio_url": raw_profile.get("portfolio_url"),
            "github_url": raw_profile.get("github_url"),
            "linkedin_url": raw_profile.get("linkedin_url"),
            "cv_url": raw_profile.get("resume_url"),
            "location": raw_profile.get("location") or None,
            "preferred_locations": raw_profile.get("preferred_locations") or [],
            "remote_preference": raw_profile.get("remote_preference") or None,
            "salary_expectations": {
                "min": salary_min,
                "max": salary_max,
                "currency": raw_profile.get("salary_currency") or None,
            },
            "job_preferences": raw_profile.get("job_types") or [],
            "career_goals": raw_profile.get("career_goals") or None,
            "preferred_industries": raw_profile.get("preferred_industries") or [],
            "preferred_companies": raw_profile.get("preferred_companies") or [],
            # A scheduling preference the user can change, not a claim about them.
            "availability": raw_profile.get("availability") or "Immediately",
            "professional_strengths": raw_profile.get("professional_strengths") or [],
            "missing_fields": missing_fields,
        }

    @staticmethod
    def build_search_queries(candidate_intel: Dict[str, Any], *, max_queries: int = 6) -> List[str]:
        """Search terms drawn from the candidate's own title, adjacent roles and skills.

        Returns ``[]`` for a candidate with neither a title nor skills - there is
        nothing truthful to search for, and the caller should ask them to finish
        their profile instead.
        """
        title = candidate_intel.get("primary_title")
        skills = [s for s in (candidate_intel.get("skills") or []) if s]
        roles = [r for r in (candidate_intel.get("transferable_roles") or []) if r]

        queries: List[str] = []

        def add(term: Optional[str]) -> None:
            if not term:
                return
            term = " ".join(str(term).split())
            if term and term.lower() not in {q.lower() for q in queries}:
                queries.append(term)

        add(title)
        if title and skills:
            add(f"{title} {skills[0]}")
        for role in roles[:3]:
            add(role)
        for skill in skills[:3]:
            add(skill)

        return queries[:max_queries]

    def analyze_profile(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze profile, map transferable skills, and generate multi-source search matrix."""
        candidate_intel = self.build_candidate_intelligence_profile(profile)
        skills = candidate_intel["skills"]
        transferable = candidate_intel["transferable_roles"]
        queries = self.build_search_queries(candidate_intel)

        # Only sources we can actually query, so the discovery stage never gets
        # handed a source name with no adapter behind it.
        from agents.scrapers.adapters import scraper_registry

        target_sources = list(scraper_registry.available_sources)

        # Company boards are only worth hitting when the user named companies.
        if not candidate_intel["preferred_companies"]:
            target_sources = [s for s in target_sources if s not in ("greenhouse", "lever")]

        descriptor = " ".join(
            part for part in (candidate_intel["seniority_level"], candidate_intel["primary_title"]) if part
        ) or "Candidate"

        return {
            "candidate_intelligence_profile": candidate_intel,
            "transferable_roles": transferable,
            "search_queries": queries,
            "target_sources": target_sources,
            "missing_fields": candidate_intel["missing_fields"],
            "strategic_summary": (
                f"{descriptor} with {len(skills)} verified core skills. "
                f"Qualified for {len(transferable)} transferable role types."
                if skills or transferable
                else "Profile is too incomplete to build a search strategy; ask the candidate to finish it."
            ),
        }

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        profile = input_data.get("profile") or input_data.get("candidate_profile") or {}

        self.logger.info("Profile Analyzer: Building Candidate Intelligence Profile & Transferable Roles")
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "profile_analyzer"

        analysis = self.analyze_profile(profile)

        if not analysis["search_queries"]:
            state["status"] = AgentStatus.ESCALATED
            state["error_message"] = (
                "Cannot build a search strategy: the profile has no professional title and no skills."
            )
            state["escalation_reason"] = "profile_incomplete"
            state["output_data"] = {
                "analysis": analysis,
                "search_queries": [],
                "target_sources": analysis["target_sources"],
                "candidate_profile": analysis["candidate_intelligence_profile"],
                "missing_fields": analysis["missing_fields"],
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
            return state

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {
            "analysis": analysis,
            "search_queries": analysis["search_queries"],
            "target_sources": analysis["target_sources"],
            "candidate_profile": analysis["candidate_intelligence_profile"],
            "missing_fields": analysis["missing_fields"],
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
        }
        state["steps_completed"] = state.get("steps_completed", []) + ["profile_analyzer"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "analysis" in output_data and "search_queries" in output_data

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for direct execution (used by the CV upload flow).

        Skills are read from the CV text with the shared vocabulary and merged
        with anything already on the profile. Years of experience are read from
        the text when the profile does not state them; if neither has it, the
        answer is ``None`` rather than an invented number.
        """
        profile = dict(input_data.get("profile") or input_data.get("candidate_profile") or input_data)
        resume_text = input_data.get("resume_text", "")

        extracted_skills = extract_skills(resume_text) if resume_text else []
        if extracted_skills:
            profile["skills"] = canonicalize(list(profile.get("skills") or []) + extracted_skills)

        if not profile.get("experience_years") and resume_text:
            inferred = self.infer_experience_years(resume_text)
            if inferred is not None:
                profile["experience_years"] = inferred

        if not profile.get("title") and resume_text:
            profile["title"] = self.infer_title(resume_text)

        analysis = self.analyze_profile(profile)
        intel = analysis["candidate_intelligence_profile"]
        return {
            "analysis": analysis,
            "extracted_skills": extracted_skills or intel["skills"],
            "candidate_intelligence_profile": intel,
            "suggested_titles": analysis["transferable_roles"][:3],
            "experience_years": intel["experience_years"],
            "search_queries": analysis["search_queries"],
            "target_sources": analysis["target_sources"],
            "missing_fields": analysis["missing_fields"],
        }

    @staticmethod
    def infer_experience_years(text: str) -> Optional[float]:
        """Read "N years of experience" out of CV text. None when it is not stated."""
        if not text:
            return None
        match = re.search(
            r"(\d{1,2}(?:\.\d)?)\s*\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:professional\s+|relevant\s+|hands-on\s+)?experience",
            text,
            re.I,
        )
        if match:
            try:
                years = float(match.group(1))
                return years if 0 < years <= 60 else None
            except ValueError:
                return None
        return None

    @staticmethod
    def infer_title(text: str) -> Optional[str]:
        """Read a job title from the first lines of a CV. None when unclear.

        CVs conventionally put the current title directly under the name, so only
        the opening lines are considered - anything further in is a past role or
        prose and would be a guess.
        """
        if not text:
            return None
        role_noun = re.compile(
            r"\b(engineer|developer|designer|analyst|manager|scientist|architect|consultant|"
            r"specialist|administrator|coordinator|director|lead|nurse|accountant|teacher|"
            r"writer|marketer|recruiter|technician|officer)\b",
            re.I,
        )
        for line in [ln.strip() for ln in str(text).splitlines() if ln.strip()][:8]:
            if len(line) > 70 or "@" in line or line.count(",") > 2:
                continue
            if role_noun.search(line):
                return " ".join(line.strip(" -|•·").split())
        return None
