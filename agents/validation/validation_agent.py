"""Data Validation Agent - Assigns multi-factor confidence scores, Anti-Scam safety verification, Source Reliability, and Opportunity Quality Scores."""
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

# Anti-scam red flag trigger terms
SCAM_RED_FLAGS = [
    "wire transfer", "send payment", "buy gift cards", "crypto payment",
    "deposit check", "processing fee", "application fee", "telegram chat",
    "whatsapp interview", "unrealistic salary", "pay upfront"
]

SOURCE_RELIABILITY_SCORES = {
    "company_websites": 98,
    "greenhouse": 98,
    "lever": 98,
    "ashby": 98,
    "linkedin": 90,
    "indeed": 90,
    "remoteok": 90,
    "weworkremotely": 90,
    "wellfound": 88,
    "upwork": 88,
    "contra": 88,
    "freelancer": 85,
    "andela": 88,
    "remotive": 85,
    "github": 85,
    # Google Jobs republishes postings that originate on company boards, so it
    # ranks above a raw web search but below reading the board directly.
    "google_jobs": 80,
    "jobicy": 80,
    "arbeitnow": 80,
    "hackernews": 70,
    "reddit": 65,
    "community": 65,
    "google_search": 60,
    "unverified": 30,
}


class ValidationAgent(BaseAgent):
    """Assigns rigorous confidence metrics, anti-scam safety verification, and opportunity quality scores."""

    def __init__(self):
        super().__init__(
            name="validation",
            agent_type="validator",
            description="Validates extracted entities, calculates Quality Scores, and executes Anti-Scam verification",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "opportunities" in input_data

    @staticmethod
    def calculate_source_reliability(source: Optional[str]) -> int:
        """Returns Source Reliability Score (0 to 100)."""
        if not source:
            return 50
        src_lower = source.lower().strip()
        for key, score in SOURCE_RELIABILITY_SCORES.items():
            if key in src_lower:
                return score
        return 70

    @staticmethod
    def detect_anti_scam_flags(item: Dict[str, Any]) -> Dict[str, Any]:
        """Anti-Scam Engine detecting payment demands, crypto, fake domains, and unrealistic compensation."""
        desc = str(item.get("description") or "").lower()
        title = str(item.get("title") or "").lower()
        email = str(item.get("contact_email") or "").lower()
        salary_max = item.get("salary_max") or 0

        flags = []
        # Check text red flags
        for flag in SCAM_RED_FLAGS:
            if flag in desc or flag in title:
                flags.append(f"Suspicious keyword found: '{flag}'")

        # Check suspicious email domains for corporate claims
        if email and ("@gmail." in email or "@yahoo." in email or "@hotmail." in email):
            if item.get("salary_min", 0) > 150000:
                flags.append("High-compensation executive listing using free public email domain")

        # Check unrealistic salary claims
        if salary_max > 500000:
            flags.append(f"Unusually high salary claim: ${salary_max:,.02f}")

        if len(flags) >= 2:
            status = "REJECTED"
            confidence = 15
        elif len(flags) == 1:
            status = "HIGH RISK"
            confidence = 40
        elif not item.get("company_name") or item.get("company_name") == "Unknown":
            status = "REVIEW"
            confidence = 65
        else:
            status = "SAFE"
            confidence = 95

        return {
            "safety_status": status,
            "verification_confidence": confidence,
            "scam_flags": flags,
        }

    @staticmethod
    def calculate_opportunity_quality_score(item: Dict[str, Any], source_reliability: int, safety_info: Dict[str, Any]) -> int:
        """Calculates Opportunity Quality Score (0 to 100)."""
        if safety_info["safety_status"] == "REJECTED":
            return 0

        freshness_score = 90
        posted_at = item.get("published_date") or item.get("posted_at")
        if posted_at:
            freshness_score = 95

        comp_score = 80 if (item.get("company_name") and item.get("company_domain")) else 40
        match_score = item.get("score") or 75
        salary_score = 90 if (item.get("salary_min") or item.get("salary_max")) else 50
        location_score = 90 if item.get("location") else 60
        contact_score = 95 if item.get("contact_email") else 50
        desc_score = 90 if (item.get("description") and len(str(item.get("description"))) > 100) else 40

        quality = (
            (source_reliability * 0.20) +
            (freshness_score * 0.15) +
            (comp_score * 0.15) +
            (match_score * 0.20) +
            (salary_score * 0.10) +
            (location_score * 0.05) +
            (contact_score * 0.05) +
            (desc_score * 0.10)
        )
        return min(max(int(round(quality)), 0), 100)

    @staticmethod
    def score_email_confidence(email: Optional[str]) -> float:
        """Calculates EMAIL_CONFIDENCE: 0.00 to 1.00."""
        if not email or not isinstance(email, str):
            return 0.0
        clean_e = email.strip().lower()
        if not EMAIL_REGEX.match(clean_e):
            return 0.0

        prefix, domain = clean_e.split("@", 1)
        if "." not in domain or len(domain.split(".")[-1]) < 2:
            return 0.1

        if prefix in GENERIC_EMAIL_PREFIXES:
            return 0.65

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
        """Validate item and enrich with confidence scores, Anti-Scam safety verification, and Quality Scores."""
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

        source_reliability = self.calculate_source_reliability(item.get("source"))
        safety_info = self.detect_anti_scam_flags(item)
        quality_score = self.calculate_opportunity_quality_score(item, source_reliability, safety_info)

        overall = round((job_conf * 0.45) + (company_conf * 0.35) + (email_conf * 0.20), 2)
        needs_review = overall < 0.60 or safety_info["safety_status"] in ["REVIEW", "HIGH RISK", "REJECTED"]

        validated_item = dict(item)
        validated_item["source_reliability_score"] = source_reliability
        validated_item["quality_score"] = quality_score
        validated_item["safety"] = safety_info
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

        self.logger.info("Validation Agent: Scoring & executing Anti-Scam safety verification on %d opportunities", len(opportunities))
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
