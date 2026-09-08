"""Ranking Agent - scores and prioritizes opportunities for outreach.

Distinct from ``MatchingAgent``: matching answers "how well does this job fit the
candidate" (the 6-factor rubric), ranking answers "which of these should we act on
first" - factoring in whether we have a contact, how fresh the posting is, and how
likely a reply is. Both score against the candidate's own data; neither has a
built-in idea of what a "good" candidate looks like.
"""
import logging
from typing import Any, Dict, List, Optional, Set

from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)

#: Reply rates by engagement type, from the pipeline's own outreach history model.
#: Applied to the opportunity, not to the candidate, so nothing here is personal.
RESPONSE_RATE_BY_TYPE = {
    "job": 0.3,
    "contract": 0.5,
    "freelance": 0.4,
    "partnership": 0.6,
    "ai_project": 0.7,
}
DEFAULT_RESPONSE_RATE = 0.3


class RankingAgent(BaseAgent):
    """Ranking Agent - scores opportunities using multi-factor model."""

    def __init__(self):
        super().__init__(
            name="ranking",
            agent_type="scoring",
            description="Scores and prioritizes opportunities using multi-factor model",
            max_retries=2,
            timeout_seconds=300,
        )

        # Scoring rubric (100 points total)
        self.scoring_rubric = {
            "tech_match": 25,
            "company_fit": 20,
            "contact_availability": 15,
            "compensation": 15,
            "response_probability": 15,
            "urgency_signal": 10,
        }
        #: Set from the candidate profile at the start of `process`, so the private
        #: scorers can stay callable on their own.
        self.candidate_skills: Set[str] = set()
        self.candidate_salary_min: Optional[float] = None
        self.candidate_salary_max: Optional[float] = None

    async def validate_input(self, input_data: dict) -> bool:
        """Validate ranking input."""
        return "opportunities" in input_data

    def load_candidate(self, candidate_profile: Optional[Dict[str, Any]]) -> None:
        """Adopt the candidate's skills and pay expectations as the scoring baseline."""
        profile = candidate_profile or {}
        skills = list(profile.get("skills") or []) + list(profile.get("technologies") or [])
        self.candidate_skills = {str(s).lower().strip() for s in skills if str(s).strip()}
        self.candidate_salary_min = profile.get("salary_min")
        self.candidate_salary_max = profile.get("salary_max")

    def _score_tech_match(
        self, opportunity: Dict[str, Any], candidate_skills: Optional[Set[str]] = None
    ) -> int:
        """Score technology overlap between the posting and the candidate (0-25).

        Measured against the candidate's declared skills. With no skills on file
        there is no basis for a technology score, so it is 0 and the missing data
        shows up in the breakdown rather than as a flattering guess.
        """
        skills = candidate_skills if candidate_skills is not None else self.candidate_skills
        if not skills:
            return 0

        tech_required = {str(t).lower().strip() for t in (opportunity.get("tech_required") or []) if str(t).strip()}
        if not tech_required:
            return 0

        match_count = len(tech_required & skills)
        score = int((match_count / len(tech_required)) * 25)
        return min(score, 25)
    
    def _score_company_fit(self, company: Dict[str, Any]) -> int:
        """Score company fit (0-20)."""
        score = 0
        
        # Size preference (startup/small/mid preferred)
        size = company.get("company_size", "").lower()
        if size in ["startup", "small", "mid"]:
            score += 10
        elif size == "enterprise":
            score += 5
        
        # Stage preference
        stage = company.get("funding_stage", "").lower()
        if stage in ["seed", "series_a", "series_b"]:
            score += 10
        elif stage == "public":
            score += 5
        
        return min(score, 20)
    
    def _score_contact_availability(self, contact_data: Dict[str, Any]) -> int:
        """Score contact availability (0-15)."""
        if not contact_data:
            return 0
        
        score = 0
        
        # Verified email is best
        if contact_data.get("email_confidence") == "verified":
            score += 15
        elif contact_data.get("email_confidence") == "probable":
            score += 10
        else:
            score += 5
        
        # Decision maker bonus
        if contact_data.get("is_decision_maker"):
            score += 5
        
        return min(score, 15)
    
    def _score_compensation(self, opportunity: Dict[str, Any]) -> int:
        """Score pay against the candidate's own expectation (0-15).

        Without a stated expectation there is nothing to compare to, so a posting
        that publishes pay scores mid-band and one that hides it scores lower -
        neither is judged against a number we made up.
        """
        salary_min = opportunity.get("salary_min")
        salary_max = opportunity.get("salary_max")
        offered = salary_max or salary_min

        if not offered:
            return 3  # Undisclosed pay is a real negative signal for outreach.

        target = self.candidate_salary_min or self.candidate_salary_max
        if not target:
            return 8

        if offered >= target:
            return 15
        if offered >= target * 0.85:
            return 10
        if offered >= target * 0.7:
            return 6
        return 2

    def _score_response_probability(self, opportunity: Dict[str, Any], company: Dict[str, Any]) -> int:
        """Score likelihood of response (0-15)."""
        opp_type = opportunity.get("type") or opportunity.get("opportunity_type") or "job"
        rate = RESPONSE_RATE_BY_TYPE.get(str(opp_type).lower(), DEFAULT_RESPONSE_RATE)
        return int(rate * 15)
    
    def _score_urgency(self, opportunity: Dict[str, Any]) -> int:
        """Score urgency signals (0-10)."""
        from datetime import datetime, timezone

        score = 0

        posted_at = opportunity.get("posted_at") or opportunity.get("published_date")
        posted_dt = self._coerce_datetime(posted_at)
        if posted_dt:
            days_posted = (datetime.now(timezone.utc) - posted_dt).days
            if days_posted < 3:
                score += 10
            elif days_posted < 7:
                score += 5

        # "Urgent" keywords in title
        title = (opportunity.get("title") or "").lower()
        if any(word in title for word in ["urgent", "asap", "immediately"]):
            score += 5

        return min(score, 10)

    @staticmethod
    def _coerce_datetime(value: Any):
        """Accept a datetime or an ISO/RFC date string; return None if unparseable.

        Sources report dates in whatever format they like, and the previous version
        assumed a ``datetime`` - so a single string posting date crashed the run.
        """
        from datetime import datetime, timezone

        if value is None:
            return None
        if isinstance(value, datetime):
            return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        text = str(value).strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
        for fmt in ("%a, %d %b %Y %H:%M:%S %z", "%Y-%m-%d", "%Y/%m/%d", "%d %b %Y"):
            try:
                parsed = datetime.strptime(text, fmt)
                return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None

    async def process(self, state: AgentState) -> AgentState:
        """Score and rank opportunities."""
        input_data = state.get("input_data", {})
        opportunities = input_data.get("opportunities", [])
        companies = input_data.get("companies", {})
        candidate_profile = input_data.get("candidate_profile") or input_data.get("profile") or {}

        self.load_candidate(candidate_profile)

        self.logger.info(
            "Ranking Agent: Scoring %d opportunities against %d candidate skills",
            len(opportunities), len(self.candidate_skills),
        )

        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "ranking"

        scored_opps = []

        for i, opp in enumerate(opportunities):
            company_id = opp.get("company_id")
            company = companies.get(company_id, {}) if isinstance(companies, dict) else {}

            # Calculate individual scores
            scores = {
                "tech_match": self._score_tech_match(opp),
                "company_fit": self._score_company_fit(company),
                "contact_availability": self._score_contact_availability(opp.get("contact")),
                "compensation": self._score_compensation(opp),
                "response_probability": self._score_response_probability(opp, company),
                "urgency_signal": self._score_urgency(opp),
            }

            # Calculate total score
            total_score = sum(scores.values())

            scored_opp = {
                **opp,
                "score": total_score,
                "rank": i + 1,
                "score_breakdown": scores,
                "status": "scored",
            }

            scored_opps.append(scored_opp)

        # Sort by score descending
        scored_opps.sort(key=lambda x: x["score"], reverse=True)

        # Update ranks
        for i, opp in enumerate(scored_opps):
            opp["rank"] = i + 1

        self.logger.info(f"Ranked {len(scored_opps)} opportunities")

        notes: List[str] = []
        if not self.candidate_skills:
            notes.append("No candidate skills on file, so technology fit scored 0 for every opportunity.")
        if not (self.candidate_salary_min or self.candidate_salary_max):
            notes.append("No salary expectation on file, so compensation was scored on disclosure only.")

        return self._update_state(state, {
            "current_step": "ranking_complete",
            "steps_completed": state.get("steps_completed", []) + ["ranking"],
            "output_data": {
                "opportunities": scored_opps,
                "count": len(scored_opps),
                "top_opportunity": scored_opps[0] if scored_opps else None,
                "scoring_notes": notes,
                "candidate_profile": candidate_profile,
            },
            "status": AgentStatus.SUCCESS,
        })
    
    async def validate_output(self, output_data: dict) -> bool:
        """Validate ranking output."""
        return "opportunities" in output_data
