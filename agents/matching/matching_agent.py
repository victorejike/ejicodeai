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
    def _calculate_experience_match(candidate_years: Optional[float], title: str, description: Optional[str]) -> int:
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

        if candidate_years is None:
            # The candidate has not told us their years, so seniority fit is
            # genuinely unknown. Score the midpoint and say so in the breakdown.
            return 10

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
        candidate_skills = candidate_profile.get("skills") or []
        required_skills = opportunity.get("tech_required") or []

        skills_score, matched_skills = self._calculate_skills_match(candidate_skills, required_skills)
        exp_score = self._calculate_experience_match(
            candidate_profile.get("experience_years"),
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
            candidate_profile.get("technologies") or candidate_skills,
            required_skills,
        )
        goal_score = self._calculate_career_goal_match(
            candidate_profile.get("career_goals"),
            opportunity.get("title", ""),
            opportunity.get("description"),
        )

        overall = skills_score + exp_score + loc_score + salary_score + tech_score + goal_score

        missing_skills = [
            s for s in required_skills
            if str(s).lower().strip() not in {str(c).lower().strip() for c in candidate_skills}
        ]

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
        scored_opp["matched_skills"] = matched_skills
        scored_opp["missing_skills"] = missing_skills
        scored_opp["match_explanation"] = self._explain(
            opportunity=opportunity,
            overall=overall,
            skills_score=skills_score,
            exp_score=exp_score,
            loc_score=loc_score,
            salary_score=salary_score,
            goal_score=goal_score,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            candidate_profile=candidate_profile,
        )
        return scored_opp

    @staticmethod
    def _explain(
        *,
        opportunity: Dict[str, Any],
        overall: int,
        skills_score: int,
        exp_score: int,
        loc_score: int,
        salary_score: int,
        goal_score: int,
        matched_skills: List[str],
        missing_skills: List[str],
        candidate_profile: Dict[str, Any],
    ) -> str:
        """A sentence per factor, each claim backed by the score that produced it.

        The previous version asserted that pay and location "fit within preferred
        parameters" for every opportunity, including the ones where they did not.
        """
        comp_name = opportunity.get("company_name") or "this employer"
        title = opportunity.get("title") or "this role"

        parts = [f"{overall}% match for {title} at {comp_name}."]

        if matched_skills:
            parts.append(
                f"Skills {skills_score}/35 - you match {', '.join(sorted(matched_skills)[:4])}."
            )
        elif opportunity.get("tech_required"):
            parts.append(f"Skills {skills_score}/35 - none of the listed requirements are on your profile.")
        else:
            parts.append(f"Skills {skills_score}/35 - the posting does not list specific requirements.")

        if candidate_profile.get("experience_years") is None:
            parts.append(f"Experience {exp_score}/20 - add your years of experience for an accurate score.")
        else:
            parts.append(f"Experience {exp_score}/20 against the seniority this posting implies.")

        location = opportunity.get("location") or opportunity.get("location_type") or "unspecified"
        parts.append(f"Location {loc_score}/10 ({location}).")

        if opportunity.get("salary_min") or opportunity.get("salary_max"):
            parts.append(f"Compensation {salary_score}/10 against your stated expectation.")
        else:
            parts.append(f"Compensation {salary_score}/10 - the posting states no salary.")

        if candidate_profile.get("career_goals"):
            parts.append(f"Career goal alignment {goal_score}/15.")

        if missing_skills:
            parts.append(f"Gaps to address: {', '.join(str(s) for s in missing_skills[:4])}.")

        return " ".join(parts)

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        opportunities = input_data.get("opportunities", [])
        candidate_profile = input_data.get("candidate_profile") or input_data.get("profile") or {}

        # Scoring without the candidate's data would rank every user's jobs
        # identically, so refuse instead of inventing a persona.
        if not candidate_profile.get("skills") and not candidate_profile.get("title"):
            self.logger.warning("Matching Agent: no candidate profile supplied; refusing to score")
            state["status"] = AgentStatus.ESCALATED
            state["escalation_reason"] = "missing_candidate_profile"
            state["error_message"] = (
                "Matching requires the candidate's own skills or title; none were provided."
            )
            state["output_data"] = {
                "opportunities": [],
                "best_match": None,
                "average_match_score": 0,
                "scored_at": datetime.now(timezone.utc).isoformat(),
            }
            return state

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
            # Passed straight through so the next stage never has to re-query it.
            "candidate_profile": candidate_profile,
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
            "agent_name": self.name,
            "status": AgentStatus.PENDING,
            "current_step": "init",
            "input_data": {"opportunities": opportunities, "candidate_profile": candidate_profile},
            "output_data": {},
            "steps_completed": [],
            "error_count": 0,
        }
        res = await self.process(state)
        return res["output_data"]
