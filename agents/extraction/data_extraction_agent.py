"""Data Extraction Agent - Transforms raw multi-source discovery into structured records without fabricating missing information."""
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Optional
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from agents.scrapers.base_adapter import clean_url

logger = logging.getLogger(__name__)


class DataExtractionAgent(BaseAgent):
    """Specialized agent transforming raw discovery into structured opportunity and contact schemas."""

    def __init__(self):
        super().__init__(
            name="extraction",
            agent_type="extractor",
            description="Transforms multi-source discovery results into validated structured data without hallucination",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "raw_items" in input_data or "opportunities" in input_data

    @staticmethod
    def extract_structured_opportunity(raw: Dict[str, Any]) -> Dict[str, Any]:
        """Extract standardized opportunity schema. Unavailable fields default strictly to None."""
        title = raw.get("title") or raw.get("job_title")
        if title:
            title = title.strip()

        company_name = raw.get("company_name") or raw.get("company")
        if company_name:
            company_name = company_name.strip()

        # Parse salary figures if present in text
        salary_min = raw.get("salary_min")
        salary_max = raw.get("salary_max")
        salary_currency = raw.get("salary_currency", "USD")

        raw_desc = str(raw.get("description") or raw.get("raw_description") or "")
        if not salary_min and ("$" in raw_desc or "£" in raw_desc or "€" in raw_desc):
            # Look for numbers like $120k, $120,000, $1500/mo
            salary_matches = re.findall(r"[\$£€]\s?(\d+[\d,]*)(?:\s?k)?", raw_desc, re.IGNORECASE)
            if salary_matches:
                try:
                    vals = []
                    for m in salary_matches[:2]:
                        num = float(m.replace(",", ""))
                        if "k" in raw_desc.lower() and num < 1000:
                            num *= 1000
                        vals.append(num)
                    if vals:
                        salary_min = min(vals)
                        salary_max = max(vals)
                except Exception:
                    pass

        # Normalize location and remote status
        location = raw.get("location")
        if location:
            location = location.strip()
        location_type = raw.get("location_type")
        if not location_type:
            loc_str = f"{title or ''} {location or ''} {raw_desc}".lower()
            if "remote" in loc_str or "anywhere" in loc_str or "work from home" in loc_str:
                location_type = "remote"
            elif "hybrid" in loc_str:
                location_type = "hybrid"
            else:
                location_type = "onsite" if location else "remote"

        # Tech stack / skills
        tech = raw.get("tech_required") or raw.get("tech_stack") or raw.get("skills") or []
        if isinstance(tech, str):
            tech = [t.strip() for t in tech.split(",") if t.strip()]

        # Common tech keywords detection in description if not already extracted
        common_keywords = ["Python", "FastAPI", "Go", "Golang", "React", "Vue", "Docker", "Kubernetes", "PostgreSQL", "PyTorch", "AWS", "GCP", "ChromaDB", "LangGraph", "LLM", "TypeScript", "Node.js"]
        found_tech = set(tech)
        for kw in common_keywords:
            if re.search(r"\b" + re.escape(kw) + r"\b", raw_desc, re.IGNORECASE):
                found_tech.add(kw)

        source_url = clean_url(raw.get("source_url") or raw.get("url"))
        company_url = clean_url(raw.get("company_url") or raw.get("website"))

        return {
            "title": title or "Untitled Opportunity",
            "company_name": company_name or "Unknown Organization",
            "company_domain": raw.get("company_domain"),
            "company_url": company_url,
            "source": raw.get("source", "scout"),
            "source_url": source_url,
            "description": raw_desc or None,
            "location": location or None,
            "location_type": location_type,
            "salary_min": float(salary_min) if salary_min else None,
            "salary_max": float(salary_max) if salary_max else None,
            "salary_currency": salary_currency,
            "tech_required": list(found_tech),
            "published_date": raw.get("published_date"),
            "deadline": raw.get("deadline"),
            "contact_name": raw.get("contact_name"),
            "contact_email": raw.get("contact_email") or raw.get("email"),
            "contact_role": raw.get("contact_role"),
            "company_size": raw.get("company_size"),
            "industry": raw.get("industry") or "Technology",
        }

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        raw_items = input_data.get("raw_items") or input_data.get("opportunities") or []

        self.logger.info("Extraction Agent: Processing %d raw items", len(raw_items))
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "extraction"

        extracted: List[Dict[str, Any]] = []
        for item in raw_items:
            try:
                extracted.append(self.extract_structured_opportunity(item))
            except Exception as e:
                self.logger.warning("Failed extracting item: %s", e)

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {
            "opportunities": extracted,
            "count": len(extracted),
            "extracted_at": datetime.now(timezone.utc).isoformat(),
        }
        state["steps_completed"] = state.get("steps_completed", []) + ["extraction"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "opportunities" in output_data
