"""Matching Agent - Calculates 6-factor candidate-opportunity alignment scores and generates natural language explanations."""
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)


class MatchingAgent(BaseAgent):
    """Computes weighted multi-factor matching rubric:
    Skills Match: 35%
    Experience Match: 20%
    Location Match: 10%
    Salary Match: 10%
    Technology Match: 10%
    Career Goal Match: 15%
    Total: 100 points
    """

    def __init__(self):
        super().__init__(
            name="matching",
            agent_type="matcher",
            description="Computes 6-factor candidate-opportunity alignment and generates natural language explanations",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "opportunities" in input_data

    @staticmethod
    def _calculate_skills_match(candidate_skills: List[str], required_skills: List[str]) -> Tuple[int, List[str]]:
        if not required_skills:
            return 28, []  # Generous baseline if no rigid skills specified

        c_set = {s.lower().strip() for s in candidate_skills}
        r_set = {s.lower().strip() for s in required_skills}

        matched = c_set & r_set
        overlap_ratio = len(matched) / len(r_set) if r_set else 1.0
        score = int(round(overlap_ratio * 35))
        return min(score, 35), list(matched)

    @staticmethod
    def _calculate_experience_match(candidate_years: float, title: str, description: Optional[str]) -> int:
        text = f"{title} {description or ''}".lower()
        required_years = 0.0

        m = re.search(r"(\d+)\+?\s*years?(?:\s+of)?\s+experience", text)
        if m:
            try:
                required_years = float(m.group(1))
            except Exception:
                pass

        if "senior" in text or "sr" in text:
            required_years = max(required_years, 5.0)
        elif "lead" in text or "staff" in text or "principal" in text:
            required_years = max(required_years, 7.0)
        elif "junior" in text or "entry" in text:
            required_years = 1.0

        if candidate_years >= required_years:
            return 20
        elif candidate_years >= (required_years - 2.0):
            return 14
        else:
            return 8

    @staticmethod
    def _calculate_location_match(candidate_pref: str, opp_type: str, candidate_loc: Optional[str], opp_loc: Optional[str]) -> int:
        c_pref = (candidate_pref or "remote").lower()
        o_type = (opp_type or "remote").lower()

        if "remote" in o_type or "anywhere" in o_type:
            return 10  # Full marks for remote flexibility

        if c_pref == "remote" and "onsite" in o_type:
            return 3

        if candidate_loc and opp_loc and (candidate_loc.lower() in opp_loc.lower() or opp_loc.lower() in candidate_loc.lower()):
            return 10

        return 6

    @staticmethod
    def _calculate_salary_match(candidate_min: Optional[float], opp_min: Optional[float], opp_max: Optional[float]) -> int:
        if not candidate_min:
            return 10  # No rigid threshold set

        if not opp_min and not opp_max:
            return 7  # Unspecified compensation, neutral score

        offered = opp_max or opp_min or 0.0
        if offered >= candidate_min:
            return 10
        elif offered >= (candidate_min * 0.85):
            return 7
        else:
            return 3

    @staticmethod
    def _calculate_tech_match(candidate_tech: List[str], required_tech: List[str]) -> int:
        if not required_tech:
            return 8
        c_tech = {t.lower().strip() for t in candidate_tech}
        r_tech = {t.lower().strip() for t in required_tech}
        matched = c_tech & r_tech
        ratio = len(matched) / len(r_tech) if r_tech else 1.0
        return min(int(round(ratio * 10)), 10)

    @staticmethod
    def _calculate_career_goal_match(career_goals: Optional[str], title: str, description: Optional[str]) -> int:
        if not career_goals:
            return 11  # Neutral-positive baseline

        goals_lower = career_goals.lower()
        title_lower = title.lower()
        desc_lower = (description or "").lower()

        # Check keyword intersections
        goal_words = set(re.findall(r"\w{4,}", goals_lower))
        text_words = set(re.findall(r"\w{4,}", f"{title_lower} {desc_lower}"))

        common = goal_words & text_words
        if len(common) >= 3:
            return 15
        elif len(common) >= 1:
            return 11
        return 7

    def score_opportunity(self, opportunity: Dict[str, Any], candidate_profile: Dict[str, Any]) -> Dict[str, Any]:
        """Calculates multi-factor breakdown and overall match score (0-100)."""
        skills_score, matched_skills = self._calculate_skills_match(
            candidate_profile.get("skills", []),
            opportunity.get("tech_required", []),
        )
        exp_score = self._calculate_experience_match(
            candidate_profile.get("experience_years", 5.0),
            opportunity.get("title", ""),
            opportunity.get("description"),
        )
        loc_score = self._calculate_location_match(
            candidate_profile.get("remote_preference", "remote"),
            opportunity.get("location_type", "remote"),
            candidate_profile.get("location"),
            opportunity.get("location"),
        )
        salary_score = self._calculate_salary_match(
            candidate_profile.get("salary_min"),
            opportunity.get("salary_min"),
            opportunity.get("salary_max"),
        )
        tech_score = self._calculate_tech_match(
            candidate_profile.get("technologies") or candidate_profile.get("skills", []),
            opportunity.get("tech_required", []),
        )
        goal_score = self._calculate_career_goal_match(
            candidate_profile.get("career_goals"),
            opportunity.get("title", ""),
            opportunity.get("description"),
        )

        overall = skills_score + exp_score + loc_score + salary_score + tech_score + goal_score

        # Generate explanation
        comp_name = opportunity.get("company_name", "the organization")
        title = opportunity.get("title", "this role")
        matched_str = ", ".join(matched_skills[:3]) if matched_skills else "core technical stack"
        explanation = (
            f"{overall}% match: Strong alignment on {matched_str} ({skills_score}/35 pts) "
            f"and experience level ({exp_score}/20 pts) for {title} at {comp_name}. "
            f"Compensation and location profile fit within preferred parameters."
        )

        scored_opp = dict(opportunity)
        scored_opp["match_score"] = overall
        scored_opp["score_breakdown"] = {
            "skills_match": skills_score,
            "experience_match": exp_score,
            "location_match": loc_score,
            "salary_match": salary_score,
            "technology_match": tech_score,
            "career_goal_match": goal_score,
            "total_score": overall,
        }
        scored_opp["match_explanation"] = explanation
        return scored_opp

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        opportunities = input_data.get("opportunities", [])
        candidate_profile = input_data.get("candidate_profile") or input_data.get("profile") or {}

        # If no profile provided in input, use default senior engineer persona
        if not candidate_profile:
            candidate_profile = {
                "skills": ["Python", "FastAPI", "Docker", "Kubernetes", "PostgreSQL", "Go"],
                "experience_years": 6.0,
                "remote_preference": "remote",
                "salary_min": 120000,
                "career_goals": "Architect scalable AI backend infrastructure and multi-agent platforms.",
            }

        self.logger.info("Matching Agent: Scoring %d opportunities against candidate profile", len(opportunities))
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "matching"

        scored = [self.score_opportunity(opp, candidate_profile) for opp in opportunities]
        # Sort descending by match score
        scored.sort(key=lambda x: x.get("match_score", 0), reverse=True)

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {
            "opportunities": scored,
            "best_match": scored[0] if scored else None,
            "average_match_score": round(sum(s["match_score"] for s in scored) / len(scored), 1) if scored else 0,
            "scored_at": datetime.now(timezone.utc).isoformat(),
        }
        state["steps_completed"] = state.get("steps_completed", []) + ["matching"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "opportunities" in output_data

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Convenience method for direct scoring without full AgentState ceremony."""
        candidate_profile = input_data.get("candidate_profile") or input_data.get("profile") or {}
        if "opportunity" in input_data:
            scored = self.score_opportunity(input_data["opportunity"], candidate_profile)
            return {
                "total_score": scored["match_score"],
                "rubric_breakdown": scored["score_breakdown"],
                "explanation": scored["match_explanation"],
                "opportunity": scored,
            }
        opportunities = input_data.get("opportunities", [])
        state: AgentState = {
            "agent_id": self.agent_id,
            "status": AgentStatus.PENDING,
            "current_step": "init",
            "input_data": {"opportunities": opportunities, "candidate_profile": candidate_profile},
            "output_data": {},
            "errors": [],
            "start_time": datetime.now(timezone.utc),
            "end_time": None,
            "retry_count": 0,
            "execution_history": [],
        }
        res = await self.process(state)
        return res["output_data"]
