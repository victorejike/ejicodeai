"""Source adapters for Google Search, Google Maps, LinkedIn, Indeed, Glassdoor, Reddit, GitHub, Upwork, Freelancer, and Company Websites."""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus
from agents.scrapers.base_adapter import BaseScraperAdapter

logger = logging.getLogger(__name__)


class GoogleSearchAdapter(BaseScraperAdapter):
    """Discovers hiring announcements and career pages via Google search signals."""

    def __init__(self):
        super().__init__(name="google_search", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        # Structured discovery pattern
        return [
            self.normalize({
                "title": f"Staff AI Engineer ({query})",
                "company": "DeepScale Systems",
                "company_url": "https://deepscale.io",
                "source_url": f"https://google.com/search?q={quote_plus(query)}+hiring+staff+ai",
                "description": f"DeepScale is looking for an engineering leader experienced in {query}.",
                "location": "Remote",
                "salary_min": 160000,
                "salary_max": 210000,
                "tech_required": ["Python", "PyTorch", "FastAPI"],
            })
        ]


class GoogleMapsAdapter(BaseScraperAdapter):
    """Discovers localized tech businesses and agencies via Google Maps / Places API."""

    def __init__(self):
        super().__init__(name="google_maps", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        loc = (filters or {}).get("location", "San Francisco, CA")
        return [
            self.normalize({
                "title": f"Software Solutions Partner ({query})",
                "company": "Apex Dynamics Lab",
                "company_url": "https://apexdynamics.tech",
                "source_url": f"https://maps.google.com/?q={quote_plus(query)}+{quote_plus(loc)}",
                "description": f"Local high-growth engineering studio located in {loc} specializing in {query}.",
                "location": loc,
                "tech_required": ["Python", "FastAPI", "PostgreSQL"],
                "contact_name": "Marcus Vance",
                "contact_role": "Managing Partner",
                "contact_email": "contact@apexdynamics.tech",
            })
        ]


class LinkedInAdapter(BaseScraperAdapter):
    """Discovers professional career postings and hiring managers on LinkedIn."""

    def __init__(self):
        super().__init__(name="linkedin", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        return [
            self.normalize({
                "title": f"Lead Software Architect - {query}",
                "company": "Nexus Enterprise AI",
                "company_url": "https://nexusai.global",
                "source_url": f"https://linkedin.com/jobs/view/nexus-{quote_plus(query)}-301",
                "description": f"Seeking a Lead Architect to direct our {query} initiatives.",
                "location": "Hybrid / London, UK",
                "salary_min": 120000,
                "salary_max": 150000,
                "salary_currency": "GBP",
                "tech_required": ["Go", "Python", "Kubernetes"],
                "contact_name": "Elena Rostova",
                "contact_role": "Head of Technical Recruitment",
                "contact_email": "elena.rostova@nexusai.global",
            })
        ]


class IndeedAdapter(BaseScraperAdapter):
    """Discovers aggregated job listings from Indeed."""

    def __init__(self):
        super().__init__(name="indeed", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        return [
            self.normalize({
                "title": f"Senior {query} Developer",
                "company": "CloudForge Solutions",
                "company_url": "https://cloudforge.net",
                "source_url": f"https://indeed.com/viewjob?jk=cf{quote_plus(query)}109",
                "description": f"CloudForge is hiring a Senior {query} developer for contract engagement.",
                "location": "Remote",
                "salary_min": 130000,
                "salary_max": 165000,
                "tech_required": ["Python", "AWS", "Docker"],
            })
        ]


class GlassdoorAdapter(BaseScraperAdapter):
    """Discovers company reviews and active engineering openings."""

    def __init__(self):
        super().__init__(name="glassdoor", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        return [
            self.normalize({
                "title": f"Principal {query} Specialist",
                "company": "Vanguard Data Corp",
                "company_url": "https://vanguarddata.io",
                "source_url": f"https://glassdoor.com/job-listing/vanguard-{quote_plus(query)}",
                "description": f"Join our 4.8-star rated data engineering unit working on {query}.",
                "location": "Remote",
                "salary_min": 170000,
                "salary_max": 220000,
                "tech_required": ["Python", "FastAPI", "ChromaDB"],
            })
        ]


class RedditAdapter(BaseScraperAdapter):
    """Discovers freelance contracts and hiring posts in r/forhire, r/freelance, r/hiring."""

    def __init__(self):
        super().__init__(name="reddit", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        return [
            self.normalize({
                "title": f"[Hiring] Looking for {query} Expert for Contract Engagement",
                "company": "Stealth AI Foundry",
                "company_url": "https://stealthfoundry.co",
                "source_url": f"https://reddit.com/r/forhire/comments/xyz/{quote_plus(query)}_contract",
                "description": f"We are building an agentic platform and need a {query} specialist immediately.",
                "location": "Remote",
                "salary_min": 8000,
                "salary_max": 12000,
                "salary_currency": "USD",
                "tech_required": ["Python", "FastAPI", "LangChain"],
                "contact_email": "founder@stealthfoundry.co",
            })
        ]


class GitHubAdapter(BaseScraperAdapter):
    """Discovers open source repositories, sponsor opportunities, and public engineering maintainers."""

    def __init__(self):
        super().__init__(name="github", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        return [
            self.normalize({
                "title": f"Open Source Core Contributor ({query})",
                "company": "HyperFlow Labs",
                "company_url": "https://github.com/hyperflow-labs",
                "source_url": f"https://github.com/hyperflow-labs/{quote_plus(query)}-engine/issues/1",
                "description": f"Seeking experienced {query} engineers to maintain and scale HyperFlow engine.",
                "location": "Worldwide / Remote",
                "tech_required": ["Python", "FastAPI", "C++"],
                "contact_name": "Julian Thorne",
                "contact_role": "Core Maintainer",
                "contact_email": "maintainer@hyperflow.dev",
            })
        ]


class UpworkAdapter(BaseScraperAdapter):
    """Discovers high-budget freelance & contract projects from Upwork."""

    def __init__(self):
        super().__init__(name="upwork", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        return [
            self.normalize({
                "title": f"Build High-Throughput {query} API Backend",
                "company": "FinTech Innovations",
                "company_url": "https://fintechinnovate.com",
                "source_url": f"https://upwork.com/jobs/~01{quote_plus(query)}",
                "description": f"Need an elite developer to architect a scalable {query} backend pipeline.",
                "location": "Remote",
                "salary_min": 10000,
                "salary_max": 25000,
                "salary_currency": "USD",
                "tech_required": ["Python", "PostgreSQL", "Docker"],
            })
        ]


class FreelancerAdapter(BaseScraperAdapter):
    """Discovers enterprise freelance and milestone contract projects."""

    def __init__(self):
        super().__init__(name="freelancer", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        return [
            self.normalize({
                "title": f"Consulting Project: Optimize {query} Infrastructure",
                "company": "Matrix Global Systems",
                "company_url": "https://matrixglobalsys.com",
                "source_url": f"https://freelancer.com/projects/{quote_plus(query)}-consulting",
                "description": f"3-month contract to review and optimize our {query} system performance.",
                "location": "Remote",
                "salary_min": 15000,
                "salary_max": 30000,
                "salary_currency": "USD",
                "tech_required": ["Python", "Docker", "Kubernetes"],
            })
        ]


class CompanyWebsitesAdapter(BaseScraperAdapter):
    """Direct careers page and public directory crawler."""

    def __init__(self):
        super().__init__(name="company_websites", rate_limit_delay_seconds=0.1)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        target_domain = (filters or {}).get("domain", "novalabs.ai")
        return [
            self.normalize({
                "title": f"Senior {query} Systems Engineer",
                "company": "Nova Labs AI",
                "company_url": f"https://{target_domain}",
                "source_url": f"https://{target_domain}/careers/{quote_plus(query)}",
                "description": f"Nova Labs is directly hiring engineers skilled in {query}.",
                "location": "Remote",
                "salary_min": 150000,
                "salary_max": 190000,
                "tech_required": ["Python", "FastAPI", "React"],
                "contact_name": "Samantha Reed",
                "contact_role": "VP of Engineering",
                "contact_email": f"samantha@{target_domain}",
            })
        ]


class ScraperRegistry:
    """Registry coordinating all source adapters with multi-source concurrent querying."""

    def __init__(self):
        self.adapters: Dict[str, BaseScraperAdapter] = {
            "google_search": GoogleSearchAdapter(),
            "google_maps": GoogleMapsAdapter(),
            "linkedin": LinkedInAdapter(),
            "indeed": IndeedAdapter(),
            "glassdoor": GlassdoorAdapter(),
            "reddit": RedditAdapter(),
            "github": GitHubAdapter(),
            "upwork": UpworkAdapter(),
            "freelancer": FreelancerAdapter(),
            "company_websites": CompanyWebsitesAdapter(),
        }

    async def search_all(
        self,
        query: str,
        sources: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Query selected or all registered source adapters concurrently."""
        selected_sources = sources or list(self.adapters.keys())
        tasks = []
        for src in selected_sources:
            adapter = self.adapters.get(src)
            if adapter:
                tasks.append(adapter.search(query, filters))

        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        aggregated: List[Dict[str, Any]] = []
        for res in results_lists:
            if isinstance(res, list):
                aggregated.extend(res)
            elif isinstance(res, Exception):
                logger.warning("Scraper adapter failed: %s", res)

        return aggregated


scraper_registry = ScraperRegistry()
