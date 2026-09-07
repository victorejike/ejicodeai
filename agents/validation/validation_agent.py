"""Data Validation Agent - Assigns multi-factor confidence scores (EMAIL_CONFIDENCE, COMPANY_CONFIDENCE, JOB_CONFIDENCE) and flags anomalies."""
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)

EMAIL_REGEX = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
)

GENERIC_EMAIL_PREFIXES = {"info", "contact", "support", "sales", "hello", "office", "admin", "jobs", "careers"}


class ValidationAgent(BaseAgent):
    """Assigns rigorous confidence metrics to extracted opportunities and contacts."""

    def __init__(self):
        super().__init__(
            name="validation",
            agent_type="validator",
            description="Validates extracted entities and computes confidence scores",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "opportunities" in input_data

    @staticmethod
    def score_email_confidence(email: Optional[str]) -> float:
        """Calculates EMAIL_CONFIDENCE: 0.00 to 1.00."""
        if not email or not isinstance(email, str):
            return 0.0
        clean_e = email.strip().lower()
        if not EMAIL_REGEX.match(clean_e):
            return 0.0

        prefix, domain = clean_e.split("@", 1)
        # Invalid TLD or domain
        if "." not in domain or len(domain.split(".")[-1]) < 2:
            return 0.1

        # Check generic email prefix
        if prefix in GENERIC_EMAIL_PREFIXES:
            return 0.65  # Public generic mailbox

        # Verified direct individual address
        if "." in prefix or "_" in prefix or len(prefix) >= 4:
            return 0.95

        return 0.80

    @staticmethod
    def score_company_confidence(company_name: Optional[str], company_domain: Optional[str], company_url: Optional[str]) -> float:
        """Calculates COMPANY_CONFIDENCE: 0.00 to 1.00."""
        if not company_name or company_name.lower() in ["unknown", "confidential", "stealth", ""]:
            return 0.20

        score = 0.50
        if len(company_name) >= 3:
            score += 0.20

        if company_domain and "." in company_domain:
            score += 0.20

        if company_url and company_url.startswith("http"):
            score += 0.10

        return min(round(score, 2), 1.00)

    @staticmethod
    def score_job_confidence(title: Optional[str], description: Optional[str], source_url: Optional[str]) -> float:
        """Calculates JOB_CONFIDENCE: 0.00 to 1.00."""
        if not title or len(title.strip()) < 3:
            return 0.10

        score = 0.40
        if description and len(description.strip()) > 50:
            score += 0.30

        if source_url and (source_url.startswith("http://") or source_url.startswith("https://")):
            score += 0.30

        return min(round(score, 2), 1.00)

    def validate_and_score(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """Validate item and enrich with confidence scores."""
        email_conf = self.score_email_confidence(item.get("contact_email"))
        company_conf = self.score_company_confidence(
            item.get("company_name"),
            item.get("company_domain"),
            item.get("company_url"),
        )
        job_conf = self.score_job_confidence(
            item.get("title"),
            item.get("description"),
            item.get("source_url"),
        )

        # Weighted overall confidence
        overall = round((job_conf * 0.45) + (company_conf * 0.35) + (email_conf * 0.20), 2)
        needs_review = overall < 0.60 or job_conf < 0.50

        validated_item = dict(item)
        validated_item["confidence_scores"] = {
            "email_confidence": email_conf,
            "company_confidence": company_conf,
            "job_confidence": job_conf,
            "overall_confidence": overall,
        }
        validated_item["needs_review"] = needs_review
        return validated_item

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        opportunities = input_data.get("opportunities", [])

        self.logger.info("Validation Agent: Scoring %d opportunities", len(opportunities))
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "validation"

        validated: List[Dict[str, Any]] = []
        flagged_count = 0
        for opp in opportunities:
            scored = self.validate_and_score(opp)
            if scored["needs_review"]:
                flagged_count += 1
            validated.append(scored)

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {
            "opportunities": validated,
            "total_validated": len(validated),
            "flagged_for_review": flagged_count,
            "validated_at": datetime.now(timezone.utc).isoformat(),
        }
        state["steps_completed"] = state.get("steps_completed", []) + ["validation"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "opportunities" in output_data
