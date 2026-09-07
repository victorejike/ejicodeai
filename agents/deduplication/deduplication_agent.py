"""Deduplication Agent - Merges duplicate opportunities across multiple sources while preserving all source references."""
from datetime import datetime, timezone
import logging
import re
from typing import Any, Dict, List, Set
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from agents.scrapers.base_adapter import clean_url

logger = logging.getLogger(__name__)


def normalize_title(title: str) -> str:
    """Normalize job title for comparison."""
    if not title:
        return ""
    t = title.lower()
    # Strip common prefixes/suffixes
    t = re.sub(r"\b(urgent|asap|hiring|remote|senior|sr|lead|staff|principal)\b", "", t)
    t = re.sub(r"[^\w\s]", "", t)
    return " ".join(t.split())


def calculate_title_similarity(title1: str, title2: str) -> float:
    """Calculate token Jaccard similarity between two job titles."""
    tokens1 = set(normalize_title(title1).split())
    tokens2 = set(normalize_title(title2).split())
    if not tokens1 or not tokens2:
        return 0.0
    intersection = len(tokens1 & tokens2)
    union = len(tokens1 | tokens2)
    return intersection / union if union > 0 else 0.0


def normalize_company(name: str) -> str:
    """Normalize company name for comparison."""
    if not name:
        return ""
    n = name.lower()
    n = re.sub(r"\b(inc|llc|ltd|corp|corporation|technologies|solutions|labs|systems|ai)\b", "", n)
    n = re.sub(r"[^\w\s]", "", n)
    return " ".join(n.split())


class DeduplicationAgent(BaseAgent):
    """Deduplication engine identifying and merging identical opportunities across disparate sources."""

    def __init__(self):
        super().__init__(
            name="deduplication",
            agent_type="deduplicator",
            description="Identifies duplicates and merges records across all sources",
            max_retries=2,
            timeout_seconds=300,
        )

    async def validate_input(self, input_data: dict) -> bool:
        return "opportunities" in input_data

    @staticmethod
    def are_duplicates(item1: Dict[str, Any], item2: Dict[str, Any]) -> bool:
        """Determines if two opportunities represent the exact same role."""
        url1 = clean_url(item1.get("source_url"))
        url2 = clean_url(item2.get("source_url"))

        # 1. Exact canonical URL match
        if url1 and url2 and url1 == url2:
            return True

        # 2. Company domain match + title similarity
        domain1 = item1.get("company_domain")
        domain2 = item2.get("company_domain")
        if domain1 and domain2 and domain1 == domain2:
            sim = calculate_title_similarity(item1.get("title", ""), item2.get("title", ""))
            if sim >= 0.50:
                return True

        # 3. Company name match + high title similarity
        comp1 = normalize_company(item1.get("company_name", ""))
        comp2 = normalize_company(item2.get("company_name", ""))
        if comp1 and comp2 and (comp1 == comp2 or comp1 in comp2 or comp2 in comp1):
            sim = calculate_title_similarity(item1.get("title", ""), item2.get("title", ""))
            if sim >= 0.65:
                return True

        return False

    @staticmethod
    def merge_records(primary: Dict[str, Any], duplicate: Dict[str, Any]) -> Dict[str, Any]:
        """Merge duplicate opportunity into primary, preserving all source metadata."""
        merged = dict(primary)

        # Merge source references
        all_sources = merged.get("all_sources", [])
        if not all_sources:
            if merged.get("source") and merged.get("source_url"):
                all_sources.append({"source": merged["source"], "url": merged["source_url"]})

        dup_src = duplicate.get("source")
        dup_url = duplicate.get("source_url")
        if dup_src and dup_url:
            if not any(s.get("url") == dup_url for s in all_sources):
                all_sources.append({"source": dup_src, "url": dup_url})

        merged["all_sources"] = all_sources
        merged["all_source_urls"] = [s.get("url") for s in all_sources if s.get("url")]

        # Merge tech stack
        t1 = set(merged.get("tech_required", []))
        t2 = set(duplicate.get("tech_required", []))
        merged["tech_required"] = list(t1 | t2)

        # Retain maximum salary bounds
        if duplicate.get("salary_max") and (not merged.get("salary_max") or duplicate["salary_max"] > merged["salary_max"]):
            merged["salary_max"] = duplicate["salary_max"]
        if duplicate.get("salary_min") and (not merged.get("salary_min") or duplicate["salary_min"] < merged["salary_min"]):
            merged["salary_min"] = duplicate["salary_min"]

        # Fill missing contact if duplicate has one
        if not merged.get("contact_email") and duplicate.get("contact_email"):
            merged["contact_email"] = duplicate["contact_email"]
            merged["contact_name"] = duplicate.get("contact_name")
            merged["contact_role"] = duplicate.get("contact_role")

        # Merge confidence scores - take highest
        c1 = merged.get("confidence_scores", {})
        c2 = duplicate.get("confidence_scores", {})
        if c2.get("overall_confidence", 0) > c1.get("overall_confidence", 0):
            merged["confidence_scores"] = c2
            merged["needs_review"] = duplicate.get("needs_review", False)

        return merged

    async def process(self, state: AgentState) -> AgentState:
        input_data = state.get("input_data", {})
        raw_opps = input_data.get("opportunities", [])

        self.logger.info("Deduplication Agent: Processing %d items", len(raw_opps))
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "deduplication"

        unique_opps: List[Dict[str, Any]] = []
        duplicates_merged_count = 0

        for opp in raw_opps:
            found_dup = False
            for idx, u_opp in enumerate(unique_opps):
                if self.are_duplicates(u_opp, opp):
                    unique_opps[idx] = self.merge_records(u_opp, opp)
                    duplicates_merged_count += 1
                    found_dup = True
                    break
            if not found_dup:
                initial_merged = dict(opp)
                if initial_merged.get("source_url"):
                    initial_merged["all_sources"] = [{"source": initial_merged.get("source", "scout"), "url": initial_merged["source_url"]}]
                    initial_merged["all_source_urls"] = [initial_merged["source_url"]]
                unique_opps.append(initial_merged)

        state["status"] = AgentStatus.SUCCESS
        state["output_data"] = {
            "opportunities": unique_opps,
            "total_raw": len(raw_opps),
            "total_unique": len(unique_opps),
            "duplicates_merged": duplicates_merged_count,
            "deduplicated_at": datetime.now(timezone.utc).isoformat(),
        }
        state["steps_completed"] = state.get("steps_completed", []) + ["deduplication"]
        return state

    async def validate_output(self, output_data: dict) -> bool:
        return "opportunities" in output_data
