"""Production-grade Live Source Adapters for Multi-Channel Opportunity and Talent Discovery.
Strict Zero-Fabrication: All items are queried from live public endpoints.
Never fabricates fictional companies, jobs, or contacts.

Timeouts, the user agent and the per-source result cap come from application
settings via ``scraper_config()`` so there is one place to tune them.
"""
import asyncio
import logging
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus

import httpx

from agents.scrapers.base_adapter import (
    BaseScraperAdapter,
    clean_url,
    parse_salary_range,
    scraper_config,
    strip_html,
)
from agents.scrapers.search_adapters import (
    GoogleJobsAdapter,
    GreenhouseAdapter,
    LeverAdapter,
    WeWorkRemotelyAdapter,
)

logger = logging.getLogger(__name__)


class RemotiveAdapter(BaseScraperAdapter):
    """Live discovery adapter for Remotive global remote jobs API."""

    def __init__(self):
        super().__init__(name="remotive", rate_limit_delay_seconds=0.2)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        cfg = scraper_config()
        limit = int((filters or {}).get("limit") or cfg.results_per_source)
        url = f"https://remotive.com/api/remote-jobs?search={quote_plus(query)}&limit={limit}"
        results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = data.get("jobs", [])
                    for job in jobs:
                        clean_desc = strip_html(job.get("description"))
                        salary_min, salary_max, currency = parse_salary_range(job.get("salary"))

                        results.append(self.normalize({
                            "title": job.get("title"),
                            "company_name": job.get("company_name"),
                            "company_url": job.get("url"),
                            "source_url": job.get("url"),
                            "description": clean_desc,
                            "location": job.get("candidate_required_location") or "Remote Worldwide",
                            "location_type": "remote",
                            "salary_min": salary_min,
                            "salary_max": salary_max,
                            "salary_currency": currency,
                            "tech_required": job.get("tags") or [],
                            "published_date": job.get("publication_date"),
                            "metadata": {"category": job.get("category"), "job_type": job.get("job_type")},
                        }))
        except Exception as e:
            logger.warning("Remotive live query failed for query '%s': %s", query, e)

        return results[:limit]


class JobicyAdapter(BaseScraperAdapter):
    """Live discovery adapter for Jobicy public remote jobs API."""

    def __init__(self):
        super().__init__(name="jobicy", rate_limit_delay_seconds=0.2)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        cfg = scraper_config()
        limit = int((filters or {}).get("limit") or cfg.results_per_source)
        url = f"https://jobicy.com/api/v2/remote-jobs?count={limit}&tag={quote_plus(query)}"
        results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = data.get("jobs", [])
                    for job in jobs:
                        clean_desc = strip_html(job.get("jobDescription"))

                        sal_min = job.get("annualSalaryMin")
                        sal_max = job.get("annualSalaryMax")
                        industry = job.get("jobIndustry")
                        if isinstance(industry, list):
                            tech_required = industry
                        elif industry:
                            tech_required = [industry]
                        else:
                            tech_required = []

                        results.append(self.normalize({
                            "title": job.get("jobTitle"),
                            "company_name": job.get("companyName"),
                            "company_url": job.get("companyWebsite") or job.get("url"),
                            "source_url": job.get("url"),
                            "description": clean_desc,
                            "location": job.get("jobGeo") or "Remote Worldwide",
                            "location_type": "remote",
                            "salary_min": float(sal_min) if sal_min else None,
                            "salary_max": float(sal_max) if sal_max else None,
                            "salary_currency": job.get("salaryCurrency") or None,
                            "tech_required": tech_required,
                            "published_date": job.get("pubDate"),
                            "metadata": {"job_type": job.get("jobType"), "job_level": job.get("jobLevel")},
                        }))
        except Exception as e:
            logger.warning("Jobicy live query failed for query '%s': %s", query, e)

        return results[:limit]


class ArbeitnowAdapter(BaseScraperAdapter):
    """Live discovery adapter for Arbeitnow public jobs API (Europe & Global Remote)."""

    def __init__(self):
        super().__init__(name="arbeitnow", rate_limit_delay_seconds=0.2)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        cfg = scraper_config()
        filters = filters or {}
        limit = int(filters.get("limit") or cfg.results_per_source)
        remote_only = bool(filters.get("remote_only"))
        url = "https://www.arbeitnow.com/api/job-board-api"
        results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    jobs = data.get("data", [])
                    q_lower = (query or "").lower()
                    for job in jobs:
                        title = job.get("title", "")
                        tags = job.get("tags", [])
                        desc = job.get("description", "")
                        is_remote = bool(job.get("remote"))

                        if remote_only and not is_remote:
                            continue

                        # Filter by query relevance
                        if q_lower in title.lower() or any(q_lower in str(t).lower() for t in tags) or q_lower in desc.lower():
                            results.append(self.normalize({
                                "title": title,
                                "company_name": job.get("company_name"),
                                "company_url": job.get("url"),
                                "source_url": job.get("url"),
                                "description": strip_html(desc),
                                "location": job.get("location") or ("Remote" if is_remote else None),
                                "location_type": "remote" if is_remote else "onsite",
                                "salary_min": None,
                                "salary_max": None,
                                "salary_currency": None,
                                "tech_required": tags,
                                "published_date": str(job.get("created_at")) if job.get("created_at") else None,
                                "metadata": {"job_types": job.get("job_types")},
                            }))
                            if len(results) >= limit:
                                break
        except Exception as e:
            logger.warning("Arbeitnow query failed for query '%s': %s", query, e)

        return results


class RemoteOKAdapter(BaseScraperAdapter):
    """Live discovery adapter for RemoteOK public developer jobs API."""

    def __init__(self):
        super().__init__(name="remoteok", rate_limit_delay_seconds=0.3)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        cfg = scraper_config()
        limit = int((filters or {}).get("limit") or cfg.results_per_source)
        url = f"https://remoteok.com/api?tag={quote_plus(query)}"
        results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    jobs = resp.json()
                    if isinstance(jobs, list):
                        # First item in RemoteOK response is metadata/legal terms
                        for job in jobs[1:]:
                            if not isinstance(job, dict):
                                continue
                            sal_min = job.get("salary_min")
                            sal_max = job.get("salary_max")

                            results.append(self.normalize({
                                "title": job.get("position"),
                                "company_name": job.get("company"),
                                "company_url": job.get("company_url") or job.get("url"),
                                "source_url": job.get("url"),
                                "description": strip_html(job.get("description")),
                                "location": job.get("location") or "Worldwide Remote",
                                "location_type": "remote",
                                "salary_min": float(sal_min) if sal_min else None,
                                "salary_max": float(sal_max) if sal_max else None,
                                "salary_currency": "USD" if (sal_min or sal_max) else None,
                                "tech_required": job.get("tags") or [],
                                "published_date": job.get("date"),
                            }))
                            if len(results) >= limit:
                                break
        except Exception as e:
            logger.warning("RemoteOK live query failed for query '%s': %s", query, e)

        return results


class HackerNewsHiringAdapter(BaseScraperAdapter):
    """Live discovery of real monthly 'Ask HN: Who is hiring' tech and engineering postings.

    HN comments are free-form. The convention is ``Company | Role | Location |
    Remote``; when a comment does not follow it we cannot know the employer or the
    role, so the item is skipped rather than filled in with a placeholder.
    """

    def __init__(self):
        super().__init__(name="hackernews", rate_limit_delay_seconds=0.2)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        await self.throttle()
        cfg = scraper_config()
        limit = int((filters or {}).get("limit") or cfg.results_per_source)
        # Search comments in recent Who is Hiring threads matching the query
        url = (
            "https://hn.algolia.com/api/v1/search_by_date"
            f"?tags=comment,author_whoishiring&query={quote_plus(query)}&hitsPerPage={limit}"
        )
        results: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    hits = resp.json().get("hits", [])
                    for hit in hits:
                        clean_text = strip_html(hit.get("comment_text"), max_length=2000)
                        if not clean_text:
                            continue

                        # First line is conventionally "Company | Role | Location | ..."
                        first_line = clean_text.split("\n")[0]
                        parts = [p.strip() for p in first_line.split("|") if p.strip()]
                        if len(parts) < 2:
                            # Not the structured format - the employer and role are
                            # unknowable, so do not guess them.
                            continue

                        company, role = parts[0], parts[1]
                        loc = parts[2] if len(parts) > 2 else None
                        salary_min, salary_max, currency = parse_salary_range(first_line)

                        results.append(self.normalize({
                            "title": role,
                            "company_name": company,
                            "company_url": None,
                            "source_url": f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                            "description": clean_text,
                            "location": loc,
                            "location_type": "remote" if loc and "remote" in loc.lower() else None,
                            "salary_min": salary_min,
                            "salary_max": salary_max,
                            "salary_currency": currency,
                            "tech_required": [],
                            "published_date": hit.get("created_at"),
                            "metadata": {"hn_headline": first_line[:300]},
                        }))
        except Exception as e:
            logger.warning("HackerNews query failed for '%s': %s", query, e)

        return results


class GitHubTalentAdapter(BaseScraperAdapter):
    """Live talent headhunting adapter querying real engineering candidates from GitHub.

    Only reports what GitHub returns. A candidate's title, bio and skills are left
    ``None``/empty when the profile does not state them - an empty field is honest,
    an invented one is not.
    """

    def __init__(self):
        super().__init__(name="github_talent", rate_limit_delay_seconds=0.3)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not query or not str(query).strip():
            return []

        await self.throttle()
        cfg = scraper_config()
        filters = filters or {}
        location = filters.get("location")
        limit = int(filters.get("limit") or 10)

        # Build GitHub search query
        q_parts = [f"language:{query}"]
        if location:
            q_parts.append(f"location:{quote_plus(location)}")
        q_parts.append("type:user")

        search_q = "+".join(q_parts)
        url = f"https://api.github.com/search/users?q={search_q}&per_page={min(limit, 30)}"
        candidates: List[Dict[str, Any]] = []

        try:
            async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    users = resp.json().get("items", [])
                    for u in users:
                        login = u.get("login")
                        profile_url = u.get("html_url")
                        avatar_url = u.get("avatar_url")

                        # Fetch detailed user profile
                        user_resp = await client.get(f"https://api.github.com/users/{login}")
                        details = user_resp.json() if user_resp.status_code == 200 else {}

                        blog = details.get("blog")
                        candidates.append({
                            "source": "github",
                            "username": login,
                            "full_name": details.get("name") or login,
                            "email": details.get("email"),  # May be None if private, adhering to zero fabrication
                            # GitHub has no job-title field; leave it unknown.
                            "title": None,
                            # The searched language is the only skill GitHub confirms.
                            "skills": [query],
                            "location": details.get("location") or location,
                            "github_url": profile_url,
                            "portfolio_url": blog if blog and blog.startswith("http") else (f"https://{blog}" if blog else None),
                            "avatar_url": avatar_url,
                            "experience_summary": details.get("bio"),
                            "company": details.get("company"),
                            "public_repos": details.get("public_repos", 0),
                            "followers": details.get("followers", 0),
                            "hireable": details.get("hireable"),
                            "status": "discovered",
                        })
        except Exception as e:
            logger.warning("GitHub talent search failed for '%s': %s", query, e)

        return candidates


class ScraperRegistry:
    """Production Multi-Channel Discovery Coordinator.
    Queries all live adapters concurrently with fail-safe isolation.
    """

    def __init__(self):
        self.opportunity_adapters: Dict[str, BaseScraperAdapter] = {
            "google_jobs": GoogleJobsAdapter(),
            "greenhouse": GreenhouseAdapter(),
            "lever": LeverAdapter(),
            "remotive": RemotiveAdapter(),
            "jobicy": JobicyAdapter(),
            "arbeitnow": ArbeitnowAdapter(),
            "remoteok": RemoteOKAdapter(),
            "weworkremotely": WeWorkRemotelyAdapter(),
            "hackernews": HackerNewsHiringAdapter(),
        }
        self.talent_adapters: Dict[str, BaseScraperAdapter] = {
            "github_talent": GitHubTalentAdapter(),
        }

    @property
    def available_sources(self) -> List[str]:
        return list(self.opportunity_adapters.keys())

    @staticmethod
    def source_reliability(source: Optional[str]) -> int:
        """Trust score for a source, read from the single rubric in ValidationAgent."""
        from agents.validation.validation_agent import ValidationAgent

        return ValidationAgent.calculate_source_reliability(source)

    @staticmethod
    def _dedupe_key(item: Dict[str, Any]) -> Optional[str]:
        """Identity of a posting: its canonical URL, else employer + title."""
        url = clean_url(item.get("source_url"))
        if url:
            return url.lower()
        title = (item.get("title") or "").strip().lower()
        company = (item.get("company_name") or "").strip().lower()
        if title and company:
            return f"{company}::{title}"
        return None

    async def search_opportunities(
        self,
        query: Optional[str] = None,
        sources: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Query live job/contract adapters concurrently.

        ``queries`` fans out over several search terms - the candidate's own title,
        their transferable role titles and their top skills - so coverage follows
        the user's profile instead of one guessed keyword. Results are deduplicated
        on canonical URL, keeping the copy from the most reliable source.
        """
        search_terms = [q.strip() for q in (queries or ([query] if query else [])) if q and q.strip()]
        if not search_terms:
            logger.info("search_opportunities called with no search terms; nothing to do")
            return []

        # Preserve caller order but drop repeats (case-insensitive).
        seen_terms: set = set()
        ordered_terms: List[str] = []
        for term in search_terms:
            key = term.lower()
            if key not in seen_terms:
                seen_terms.add(key)
                ordered_terms.append(term)

        active_sources = [s for s in (sources or self.available_sources) if s in self.opportunity_adapters]
        if not active_sources:
            logger.warning("No known opportunity sources in %s", sources)
            return []

        jobs: List[tuple] = []
        for term in ordered_terms:
            for source in active_sources:
                jobs.append((source, term, self.opportunity_adapters[source].search(term, filters)))

        outcomes = await asyncio.gather(*(job[2] for job in jobs), return_exceptions=True)

        # Best copy wins: higher source reliability, then a longer description.
        best: Dict[str, Dict[str, Any]] = {}
        unkeyed: List[Dict[str, Any]] = []

        for (source, term, _), outcome in zip(jobs, outcomes):
            if isinstance(outcome, Exception):
                logger.warning("Adapter [%s] failed for '%s': %s", source, term, outcome)
                continue
            if not isinstance(outcome, list):
                continue
            for item in outcome:
                if not isinstance(item, dict) or not item.get("title"):
                    continue
                item.setdefault("source", source)
                metadata = item.get("metadata")
                if isinstance(metadata, dict):
                    metadata.setdefault("matched_query", term)
                key = self._dedupe_key(item)
                if key is None:
                    unkeyed.append(item)
                    continue
                incumbent = best.get(key)
                if incumbent is None:
                    best[key] = item
                    continue
                if self._rank(item) > self._rank(incumbent):
                    best[key] = item

        aggregated = list(best.values()) + unkeyed
        logger.info(
            "Discovery: %s terms x %s sources -> %s unique opportunities",
            len(ordered_terms), len(active_sources), len(aggregated),
        )
        return aggregated

    @classmethod
    def _rank(cls, item: Dict[str, Any]) -> tuple:
        return (
            cls.source_reliability(item.get("source")),
            len(str(item.get("description") or "")),
            1 if item.get("salary_min") else 0,
        )

    async def search_talent(
        self,
        skills: List[str],
        location: Optional[str] = None,
        limit: int = 15,
    ) -> List[Dict[str, Any]]:
        """Query live talent sources for candidates matching skills and location."""
        primary_skill = next((s for s in (skills or []) if s and str(s).strip()), None)
        if not primary_skill:
            logger.info("search_talent called without skills; nothing to search for")
            return []

        adapter = self.talent_adapters.get("github_talent")
        if not adapter:
            return []

        candidates = await adapter.search(primary_skill, {"location": location, "limit": limit})
        return candidates[:limit]

    async def search_all(
        self,
        query: Optional[str] = None,
        sources: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        return await self.search_opportunities(query, sources, filters, queries)


scraper_registry = ScraperRegistry()
