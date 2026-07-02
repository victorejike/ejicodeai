"""Ranking Agent - scores and prioritizes opportunities."""
import logging
from typing import List, Dict, Any
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)


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
    
    async def validate_input(self, input_data: dict) -> bool:
        """Validate ranking input."""
        return "opportunities" in input_data
    
    def _score_tech_match(self, opportunity: Dict[str, Any]) -> int:
        """Score technology match (0-25)."""
        tech_required = set(opportunity.get("tech_required", []))
        ejicode_tech = {
            "Go", "Python", "React", "Vue", "FastAPI", 
            "PostgreSQL", "Docker", "Kubernetes", "AI", "ML"
        }
        
        match_count = len(tech_required & ejicode_tech)
        total_count = len(tech_required) if tech_required else 1
        
        score = int((match_count / total_count) * 25) if total_count > 0 else 0
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
        """Score compensation/contract value (0-15)."""
        salary_min = opportunity.get("salary_min", 0)
        salary_max = opportunity.get("salary_max", 0)
        
        # Prefer contracts > $2000/month or salaries > $50k/year
        if opportunity.get("type") == "contract":
            if salary_min and salary_min >= 2000:
                return 15
            elif salary_min and salary_min >= 1000:
                return 10
            else:
                return 5
        else:
            if salary_max and salary_max >= 100000:
                return 15
            elif salary_max and salary_max >= 80000:
                return 10
            else:
                return 5
    
    def _score_response_probability(self, opportunity: Dict[str, Any], company: Dict[str, Any]) -> int:
        """Score likelihood of response (0-15)."""
        # Historical win rate for opportunity type
        opp_type = opportunity.get("type", "job")
        
        response_rates = {
            "job": 0.3,
            "contract": 0.5,
            "freelance": 0.4,
            "partnership": 0.6,
            "ai_project": 0.7,
        }
        
        rate = response_rates.get(opp_type, 0.3)
        return int(rate * 15)
    
    def _score_urgency(self, opportunity: Dict[str, Any]) -> int:
        """Score urgency signals (0-10)."""
        from datetime import datetime, timedelta
        
        score = 0
        
        # Posted recently (< 3 days)
        posted_at = opportunity.get("posted_at")
        if posted_at:
            days_posted = (datetime.utcnow() - posted_at).days
            if days_posted < 3:
                score += 10
            elif days_posted < 7:
                score += 5
        
        # "Urgent" keywords in title
        title = (opportunity.get("title") or "").lower()
        if any(word in title for word in ["urgent", "asap", "immediately"]):
            score += 5
        
        return min(score, 10)
    
    async def process(self, state: AgentState) -> AgentState:
        """Score and rank opportunities."""
        opportunities = state.get("input_data", {}).get("opportunities", [])
        companies = state.get("input_data", {}).get("companies", {})
        
        self.logger.info(f"Ranking Agent: Scoring {len(opportunities)} opportunities")
        
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "ranking"
        
        scored_opps = []
        
        for i, opp in enumerate(opportunities):
            company_id = opp.get("company_id")
            company = companies.get(company_id, {})
            
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
        
        return self._update_state(state, {
            "current_step": "ranking_complete",
            "steps_completed": state.get("steps_completed", []) + ["ranking"],
            "output_data": {
                "opportunities": scored_opps,
                "count": len(scored_opps),
                "top_opportunity": scored_opps[0] if scored_opps else None,
            },
            "status": AgentStatus.SUCCESS,
        })
    
    async def validate_output(self, output_data: dict) -> bool:
        """Validate ranking output."""
        return "opportunities" in output_data
