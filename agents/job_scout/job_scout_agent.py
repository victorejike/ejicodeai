"""Job Scout Agent — discovers real opportunities from RemoteOK, HackerNews, and optionally Google Maps via Apify."""
import asyncio
import logging
from typing import List, Dict, Any
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus
from backend.app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TECH_TAGS = {"python", "go", "backend", "fullstack", "devops", "ai", "ml",
             "fastapi", "django", "react", "typescript", "node", "rust", "cloud"}


class RemoteOKScraper:
    async def scrape(self) -> List[Dict[str, Any]]:
        try:
            import httpx
            async with httpx.AsyncClient(headers={"User-Agent": "EjicodeAI/1.0"}) as client:
                resp = await client.get("https://remoteok.com/api", timeout=30)
                jobs = resp.json()
                results = []
                for job in jobs:
                    if not isinstance(job, dict) or not job.get("position"):
                        continue
                    tags = {t.lower() for t in (job.get("tags") or [])}
                    if not tags & TECH_TAGS:
                        continue
                    results.append({
                        "title": job.get("position", ""),
                        "company": job.get("company", ""),
                        "url": job.get("url", ""),
                        "type": "job",
                        "location": job.get("location", "Remote"),
                        "description": job.get("description", "")[:500],
                        "tags": list(tags),
                        "source_platform": "remoteok",
                        "salary_min": job.get("salary_min"),
                        "salary_max": job.get("salary_max"),
                    })
                logger.info(f"RemoteOK: {len(results)} jobs")
                return results
        except Exception as e:
            logger.error(f"RemoteOK error: {e}")
            return []


class HackerNewsScraper:
    """HackerNews 'Who is Hiring' via Algolia API — free, no auth needed."""

    async def scrape(self) -> List[Dict[str, Any]]:
        try:
            import httpx
            from datetime import datetime

            # Search latest "Who is Hiring" posts
            async with httpx.AsyncClient() as client:
                # Get the latest hiring thread ID
                search_resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"query": "Ask HN: Who is hiring", "tags": "story", "hitsPerPage": 1},
                    timeout=15,
                )
                hits = search_resp.json().get("hits", [])
                if not hits:
                    return []

                thread_id = hits[0]["objectID"]

                # Get comments from that thread
                comments_resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"tags": f"comment,story_{thread_id}", "hitsPerPage": 50},
                    timeout=15,
                )
                comments = comments_resp.json().get("hits", [])

                results = []
                for c in comments:
                    text = c.get("comment_text", "") or ""
                    if not text or len(text) < 50:
                        continue
                    text_lower = text.lower()
                    if not any(t in text_lower for t in TECH_TAGS):
                        continue

                    # Extract company name from first line
                    first_line = text.split("<p>")[0].replace("<b>", "").replace("</b>", "").strip()
                    company = first_line[:80] if first_line else "Unknown"

                    results.append({
                        "title": f"HN Hiring: {company[:60]}",
                        "company": company,
                        "url": f"https://news.ycombinator.com/item?id={c.get('objectID', '')}",
                        "type": "job",
                        "location": "Remote" if "remote" in text_lower else "Unknown",
                        "description": text[:500],
                        "tags": [t for t in TECH_TAGS if t in text_lower],
                        "source_platform": "hackernews",
                    })

                logger.info(f"HackerNews: {len(results)} jobs")
                return results
        except Exception as e:
            logger.error(f"HackerNews error: {e}")
            return []


class GoogleMapsScraper:
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
                        "searchTerms": [self.query, "AI company", "software development company", "tech startup"],
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
                    description = (item.get("description") or item.get("snippet") or "")[:500]
                    title = item.get("title") or item.get("name") or self.query
                    results.append({
                        "title": title,
                        "company": title,
                        "url": item.get("url") or item.get("placeUrl") or "",
                        "type": "business",
                        "location": item.get("address") or self.location,
                        "description": description,
                        "tags": [self.query, "ai", "software", "tech"],
                        "source_platform": "googlemaps",
                    })

                logger.info(f"GoogleMaps: {len(results)} places")
                return results
        except Exception as e:
            logger.error(f"GoogleMaps error: {e}")
            return []


class JobScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="job_scout",
            agent_type="discovery",
            description="Discovers job and contract opportunities from RemoteOK, HackerNews, and optionally Google Maps",
            max_retries=3,
            timeout_seconds=120,
        )
        self.scrapers = [RemoteOKScraper(), HackerNewsScraper()]
        if settings.apify_api_token:
            self.scrapers.append(GoogleMapsScraper(query="AI startup", location="Remote"))
            self.scrapers.append(GoogleMapsScraper(query="software development company", location="Remote"))

    async def validate_input(self, input_data: dict) -> bool:
        return True

    async def process(self, state: AgentState) -> AgentState:
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "scraping"

        results = await asyncio.gather(*[s.scrape() for s in self.scrapers], return_exceptions=True)

        all_opps = []
        for r in results:
            if isinstance(r, list):
                all_opps.extend(r)

        # Deduplicate by URL
        seen = {}
        for o in all_opps:
            url = o.get("url", "")
            if url and url not in seen:
                seen[url] = o
        unique = list(seen.values())

        logger.info(f"Job Scout: {len(unique)} unique opportunities found")

        return self._update_state(state, {
            "current_step": "discovery_complete",
            "steps_completed": ["scraping", "deduplication"],
            "output_data": {"opportunities": unique, "count": len(unique)},
            "status": AgentStatus.SUCCESS,
        })

    async def validate_output(self, output_data: dict) -> bool:
        return "opportunities" in output_data
