"""Job Scout Agent - discovers opportunities for one specific candidate.

The agent no longer owns scrapers of its own. Discovery goes through
``scraper_registry``, which is the single place where sources, trust tiers and
the canonical opportunity schema live, and the search terms come from the
candidate's own title, adjacent roles and skills. Without a candidate profile
the agent refuses to run - a global feed filtered by a fixed tag list is the
same result for everybody, which is not a match.

``GoogleMapsScraper`` stays here for local company discovery (it returns
businesses, not job posts) and is only used when an Apify token is configured.
"""
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from backend.app.config import get_settings

logger = logging.getLogger(__name__)


def _slugify_company(name: str) -> Optional[str]:
    """Turn a company name into the board slug Greenhouse/Lever use."""
    slug = re.sub(r"[^a-z0-9]+", "", str(name).lower().strip())
    return slug or None


class GoogleMapsScraper:
    """Google Maps business listings via Apify - company discovery, not job posts."""

    def __init__(self, query: str | None = None, location: str | None = None):
        self.query = query or "software company"
        self.location = location or "Remote"

    async def scrape(self) -> List[Dict[str, Any]]:
        try:
            import httpx

            settings = get_settings()
            if not settings.apify_api_token:
                return []

            async with httpx.AsyncClient(timeout=60) as client:
                run_resp = await client.post(
                    "https://api.apify.com/v2/acts/compass~crawler-google-places/runs?token=" + settings.apify_api_token,
                    json={
                        "searchTerms": [self.query],
                        "location": self.location,
                        "maxPlaces": 25,
                        "includeReviews": False,
                        "includeSearchMetadata": False,
                    },
                    headers={"Content-Type": "application/json"},
                )
                run_resp.raise_for_status()
                run_data = run_resp.json()
                run_id = run_data.get("data", {}).get("id")
                if not run_id:
                    return []

                dataset_url = f"https://api.apify.com/v2/acts/compass~crawler-google-places/runs/{run_id}/dataset/items?token={settings.apify_api_token}"
                dataset_resp = await client.get(dataset_url, timeout=60)
                dataset_resp.raise_for_status()
                items = dataset_resp.json()

                results = []
                for item in items:
                    if not isinstance(item, dict):
                        continue
                    title = item.get("title") or item.get("name")
                    if not title:
                        continue
                    results.append({
                        "title": title,
                        "company_name": title,
                        "company": title,
                        "source_url": item.get("url") or item.get("placeUrl") or "",
                        "url": item.get("url") or item.get("placeUrl") or "",
                        "type": "business",
                        "location": item.get("address") or self.location,
                        "description": (item.get("description") or item.get("snippet") or "")[:500] or None,
                        # Maps says nothing about a company's stack, so it stays empty.
                        "tech_required": [],
                        "source": "googlemaps",
                        "source_platform": "googlemaps",
                    })

                logger.info(f"GoogleMaps: {len(results)} places")
                return results
        except Exception as e:
            logger.error(f"GoogleMaps error: {e}")
            return []


class JobScoutAgent(BaseAgent):
    """Runs the candidate's own search terms across every configured job source."""

    def __init__(self):
        super().__init__(
            name="job_scout",
            agent_type="discovery",
            description="Discovers opportunities across every configured job source using the candidate's own profile",
            max_retries=3,
            timeout_seconds=180,
        )

    async def validate_input(self, input_data: dict) -> bool:
        """A candidate profile (or ready-made search terms) is mandatory."""
        input_data = input_data or {}
        if input_data.get("search_queries"):
            return True
        profile = input_data.get("candidate_profile") or input_data.get("profile") or {}
        if not isinstance(profile, dict):
            return False
        return bool(
            profile.get("skills")
            or profile.get("technologies")
            or profile.get("primary_title")
            or profile.get("title")
        )

    @staticmethod
    def build_queries(candidate_profile: Dict[str, Any], *, max_queries: int = 6) -> List[str]:
        """Search terms from the candidate's title, adjacent roles and top skills."""
        from agents.profile_analyzer.profile_analyzer_agent import ProfileAnalyzerAgent

        profile = candidate_profile or {}
        # Accept either a raw profile or an already-built intelligence profile.
        intel = profile
        if not profile.get("primary_title") and not profile.get("transferable_roles"):
            intel = ProfileAnalyzerAgent.build_candidate_intelligence_profile(profile)
        return ProfileAnalyzerAgent.build_search_queries(intel, max_queries=max_queries)

    @staticmethod
    def build_filters(candidate_profile: Dict[str, Any], input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Discovery filters taken from the candidate's stated preferences."""
        profile = candidate_profile or {}
        preferred_locations = profile.get("preferred_locations") or []
        remote_pref = str(profile.get("remote_preference") or "").lower()

        location = (
            input_data.get("location")
            or (preferred_locations[0] if preferred_locations else None)
            or profile.get("location")
        )

        boards = [
            slug
            for slug in (
                _slugify_company(c) for c in (profile.get("preferred_companies") or [])
            )
            if slug
        ]

        filters: Dict[str, Any] = {
            "remote_only": bool(input_data.get("remote_only")) or remote_pref == "remote",
        }
        if location:
            filters["location"] = location
        if boards:
            filters["boards"] = boards
        if input_data.get("limit"):
            filters["limit"] = input_data["limit"]
        return filters

    async def process(self, state: AgentState) -> AgentState:
        from agents.scrapers.adapters import scraper_registry

        input_data = state.get("input_data", {}) or {}
        candidate_profile = input_data.get("candidate_profile") or input_data.get("profile") or {}

        queries = list(input_data.get("search_queries") or []) or self.build_queries(candidate_profile)

        if not queries:
            self.logger.warning("Job Scout: no search terms could be derived from the candidate profile")
            state["status"] = AgentStatus.ESCALATED
            state["escalation_reason"] = "profile_incomplete"
            state["error_message"] = (
                "Discovery needs the candidate's job title or skills; the profile has neither."
            )
            state["output_data"] = {
                "opportunities": [],
                "count": 0,
                "search_queries": [],
                "candidate_profile": candidate_profile,
            }
            return state

        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "scraping"

        sources = input_data.get("target_sources") or input_data.get("sources")
        filters = self.build_filters(candidate_profile, input_data)

        source_count = len(sources) if sources else len(scraper_registry.available_sources)
        await self.emit(
            state,
            "agent.progress",
            f"Searching {source_count} sources for {len(queries)} variants of your role",
            payload={"queries": queries, "sources": sources, "filters": filters},
        )

        opportunities = await scraper_registry.search_opportunities(
            queries=queries, sources=sources, filters=filters
        )

        # Local companies are a different kind of lead; only fetched when the user
        # asked for a location and Apify is configured.
        companies: List[Dict[str, Any]] = []
        if get_settings().apify_api_token and filters.get("location"):
            scrapers = [GoogleMapsScraper(query=q, location=filters["location"]) for q in queries[:2]]
            gathered = await asyncio.gather(*(s.scrape() for s in scrapers), return_exceptions=True)
            for result in gathered:
                if isinstance(result, list):
                    companies.extend(result)

        self.logger.info(
            "Job Scout: %d opportunities from %d queries (+%d local companies)",
            len(opportunities), len(queries), len(companies),
        )

        return self._update_state(state, {
            "current_step": "discovery_complete",
            "steps_completed": state.get("steps_completed", []) + ["discovery"],
            "output_data": {
                "opportunities": opportunities,
                "count": len(opportunities),
                "local_companies": companies,
                "search_queries": queries,
                "sources_used": sources or list(scraper_registry.available_sources),
                "filters": filters,
                # Handed straight to the next stage so it never re-queries the user.
                "candidate_profile": candidate_profile,
            },
            "status": AgentStatus.SUCCESS,
        })

    async def validate_output(self, output_data: dict) -> bool:
        return "opportunities" in output_data
