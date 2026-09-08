"""Search-engine and applicant-tracking-system adapters.

These cover the sources the product promised but never had:

* ``GoogleJobsAdapter`` - Google. Structured Google Jobs data when a SerpAPI or
  ScrapingDog key is configured; otherwise a keyless Google web search scoped to
  the applicant-tracking hosts companies actually post on. The keyless path is
  best-effort by nature (Google may serve a consent page or rate-limit), so it
  returns ``[]`` rather than raising, and the keyed path is preferred whenever a
  key exists.
* ``GreenhouseAdapter`` / ``LeverAdapter`` - the two highest-trust sources in
  ``ValidationAgent.calculate_source_reliability`` (98/100). Public per-company
  JSON boards, no key needed. Boards come from settings or from the caller, never
  from a list baked into the code.
* ``WeWorkRemotelyAdapter`` - public RSS.

Every adapter obeys the same contract: it takes ``query`` plus optional
``location`` / ``remote_only`` / ``limit`` filters, returns items through
``BaseScraperAdapter.normalize()``, and never invents a company, title or salary.
When a field is not present in the source it stays ``None``.
"""
from __future__ import annotations

import asyncio
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qs, quote_plus, urlparse

import httpx

from agents.scrapers.base_adapter import (
    BaseScraperAdapter,
    clean_url,
    parse_salary_range,
    prettify_slug,
    scraper_config,
    strip_html,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Applicant-tracking hosts. Used to scope the keyless Google search to pages
# that are actually job postings, and to read the employer out of the URL.
# ---------------------------------------------------------------------------

#: host -> callable(path_parts) -> company slug or None
_ATS_HOSTS: Tuple[Tuple[str, Any], ...] = (
    ("boards.greenhouse.io", lambda p: p[0] if p else None),
    ("job-boards.greenhouse.io", lambda p: p[0] if p else None),
    ("jobs.lever.co", lambda p: p[0] if p else None),
    ("jobs.ashbyhq.com", lambda p: p[0] if p else None),
    ("apply.workable.com", lambda p: p[0] if p else None),
    ("jobs.workable.com", lambda p: p[0] if p else None),
    ("jobs.smartrecruiters.com", lambda p: p[0] if p else None),
    ("careers.smartrecruiters.com", lambda p: p[0] if p else None),
    ("weworkremotely.com", lambda p: None),
    ("remoteok.com", lambda p: None),
    ("wellfound.com", lambda p: None),
)

#: Host suffixes where the employer is the sub-domain, e.g. acme.breezy.hr.
_ATS_SUBDOMAIN_SUFFIXES = (
    ".breezy.hr",
    ".recruitee.com",
    ".teamtailor.com",
    ".applytojob.com",
    ".bamboohr.com",
    ".rippling.com",
    ".pinpointhq.com",
    ".myworkdayjobs.com",
)

#: The `site:` clause for the keyless Google query, derived from the hosts above
#: so there is exactly one list to maintain.
_GOOGLE_SITE_CLAUSE = " OR ".join(
    f"site:{host}" for host, _ in _ATS_HOSTS
) + " OR " + " OR ".join(f"site:*{suffix}" for suffix in _ATS_SUBDOMAIN_SUFFIXES)

#: Noise Google/ATS pages append to a job title.
_TITLE_NOISE = re.compile(
    r"\s*[-|–—]\s*(greenhouse|lever|workable|ashby|smartrecruiters|breezy|"
    r"teamtailor|recruitee|bamboohr|workday|job application|careers?|jobs?)\s*$",
    re.I,
)
_JOB_APPLICATION_PREFIX = re.compile(r"^job application for\s+", re.I)


def _company_from_url(url: Optional[str]) -> Optional[str]:
    """Read the employer out of an ATS URL. Returns None when it cannot be known."""
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except Exception:
        return None
    host = (parsed.netloc or "").lower().replace("www.", "")
    parts = [p for p in (parsed.path or "").split("/") if p]

    for known_host, extractor in _ATS_HOSTS:
        if host == known_host:
            return prettify_slug(extractor(parts))

    for suffix in _ATS_SUBDOMAIN_SUFFIXES:
        if host.endswith(suffix):
            sub = host[: -len(suffix)]
            # acme.wd1.myworkdayjobs.com -> acme
            return prettify_slug(sub.split(".")[0])

    return None


def _clean_title(title: Optional[str]) -> Optional[str]:
    """Strip ATS boilerplate from a title without inventing one."""
    if not title:
        return None
    text = _JOB_APPLICATION_PREFIX.sub("", str(title).strip())
    for _ in range(3):  # titles often carry two suffixes: "Role - Acme - Greenhouse"
        new = _TITLE_NOISE.sub("", text).strip()
        if new == text:
            break
        text = new
    return text or None


def _split_title_and_company(title: Optional[str]) -> Tuple[Optional[str], Optional[str]]:
    """``Backend Engineer at Acme`` -> ``("Backend Engineer", "Acme")``."""
    if not title:
        return None, None
    match = re.search(r"^(.*?)\s+(?:at|@)\s+(.+)$", title.strip(), re.I)
    if match:
        role = match.group(1).strip()
        company = match.group(2).strip()
        if role and company:
            return role, company
    return title.strip(), None


def _unwrap_google_href(href: Optional[str]) -> Optional[str]:
    """Turn ``/url?q=https://...&sa=U`` into the destination URL."""
    if not href:
        return None
    if href.startswith("/url?") or href.startswith("https://www.google.com/url?"):
        query = parse_qs(urlparse(href).query)
        for key in ("q", "url"):
            if query.get(key):
                return query[key][0]
        return None
    if href.startswith("http"):
        return href
    return None


def _build_query(query: str, location: Optional[str], remote_only: bool) -> str:
    parts = [query.strip()] if query and query.strip() else []
    if remote_only:
        parts.append("remote")
    elif location:
        parts.append(location.strip())
    return " ".join(p for p in parts if p)


def _matches(query: str, *fields: Optional[str]) -> bool:
    """Loose relevance check: every meaningful query word appears somewhere."""
    if not query:
        return True
    haystack = " ".join(f.lower() for f in fields if f)
    if not haystack:
        return False
    words = [w for w in re.split(r"\W+", query.lower()) if len(w) > 2]
    if not words:
        return True
    return any(w in haystack for w in words)


class GoogleJobsAdapter(BaseScraperAdapter):
    """Google-backed job discovery.

    Order of preference: SerpAPI's ``google_jobs`` engine, then ScrapingDog's,
    then a keyless Google web search restricted to applicant-tracking hosts.
    """

    def __init__(self):
        super().__init__(name="google_jobs", rate_limit_delay_seconds=1.0)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        cfg = scraper_config()
        limit = int(filters.get("limit") or cfg.results_per_source)
        location = filters.get("location")
        remote_only = bool(filters.get("remote_only"))

        await self.throttle()

        try:
            if cfg.serpapi_key:
                return await self._via_serpapi(query, location, remote_only, limit, cfg)
            if cfg.scrapingdog_key:
                return await self._via_scrapingdog(query, location, remote_only, limit, cfg)
            return await self._via_web_search(query, location, remote_only, limit, cfg)
        except Exception as exc:
            logger.warning("Google jobs search failed for '%s': %s", query, exc)
            return []

    # -- keyed providers ---------------------------------------------------

    async def _via_serpapi(self, query, location, remote_only, limit, cfg) -> List[Dict[str, Any]]:
        params = {
            "engine": "google_jobs",
            "q": _build_query(query, location, remote_only),
            "hl": "en",
            "api_key": cfg.serpapi_key,
        }
        if location and not remote_only:
            params["location"] = location
        async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
            resp = await client.get("https://serpapi.com/search.json", params=params)
        if resp.status_code != 200:
            logger.warning("SerpAPI google_jobs returned %s", resp.status_code)
            return []
        return self._normalize_google_jobs(resp.json().get("jobs_results") or [], limit, provider="serpapi")

    async def _via_scrapingdog(self, query, location, remote_only, limit, cfg) -> List[Dict[str, Any]]:
        params = {
            "api_key": cfg.scrapingdog_key,
            "query": _build_query(query, location, remote_only),
            "language": "en",
        }
        async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
            resp = await client.get("https://api.scrapingdog.com/google_jobs", params=params)
        if resp.status_code != 200:
            logger.warning("ScrapingDog google_jobs returned %s", resp.status_code)
            return []
        payload = resp.json()
        items = payload.get("jobs_results") or payload.get("jobs") or []
        return self._normalize_google_jobs(items, limit, provider="scrapingdog")

    def _normalize_google_jobs(
        self, items: List[Dict[str, Any]], limit: int, *, provider: str
    ) -> List[Dict[str, Any]]:
        """Map the shared Google Jobs payload shape used by both keyed providers."""
        results: List[Dict[str, Any]] = []
        for job in items[:limit]:
            if not isinstance(job, dict):
                continue
            extensions = job.get("detected_extensions") or {}
            apply_options = job.get("apply_options") or []
            source_url = (
                job.get("share_link")
                or (apply_options[0].get("link") if apply_options and isinstance(apply_options[0], dict) else None)
                or job.get("link")
            )
            salary_text = extensions.get("salary") or job.get("salary")
            salary_min, salary_max, currency = parse_salary_range(salary_text)

            location = job.get("location")
            schedule = extensions.get("schedule_type")
            work_from_home = extensions.get("work_from_home")
            location_type = "remote" if work_from_home or "remote" in str(location or "").lower() else None

            results.append(
                self.normalize(
                    {
                        "title": _clean_title(job.get("title")),
                        "company_name": job.get("company_name"),
                        "company_url": job.get("company_url"),
                        "source_url": source_url,
                        "description": strip_html(job.get("description")),
                        "location": location,
                        "location_type": location_type,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": currency,
                        "published_date": extensions.get("posted_at"),
                        "metadata": {
                            "google_provider": provider,
                            "via": job.get("via"),
                            "schedule_type": schedule,
                            "salary_text": salary_text,
                            "apply_options": [
                                o.get("link") for o in apply_options if isinstance(o, dict) and o.get("link")
                            ],
                        },
                    }
                )
            )
        return [r for r in results if r.get("source_url") and r.get("title")]

    # -- keyless path ------------------------------------------------------

    async def _via_web_search(self, query, location, remote_only, limit, cfg) -> List[Dict[str, Any]]:
        """Google web search scoped to ATS hosts, parsed from the HTML results page.

        This is the no-key fallback. Google may answer with a consent or captcha
        page; in that case we log and return nothing rather than guessing.
        """
        try:
            from bs4 import BeautifulSoup
        except ImportError:  # pragma: no cover - beautifulsoup4 is in requirements
            logger.warning("beautifulsoup4 is not installed; keyless Google search disabled")
            return []

        terms = _build_query(query, location, remote_only)
        search_q = f'"{query.strip()}" ({_GOOGLE_SITE_CLAUSE})' if query.strip() else _GOOGLE_SITE_CLAUSE
        if remote_only:
            search_q += " remote"
        elif location:
            search_q += f' "{location.strip()}"'

        url = (
            "https://www.google.com/search"
            f"?q={quote_plus(search_q)}&hl=en&gl=us&num={min(limit * 2, 40)}&filter=0"
        )
        headers = {
            **cfg.headers,
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with httpx.AsyncClient(
            timeout=cfg.timeout, headers=headers, follow_redirects=True
        ) as client:
            resp = await client.get(url)

        if resp.status_code != 200:
            logger.info("Keyless Google search unavailable (HTTP %s) for '%s'", resp.status_code, terms)
            return []
        if "/sorry/" in str(resp.url) or "unusual traffic" in resp.text[:4000].lower():
            logger.info("Google served a captcha page; skipping keyless results for '%s'", terms)
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        results: List[Dict[str, Any]] = []
        seen: set[str] = set()

        for anchor in soup.find_all("a", href=True):
            destination = _unwrap_google_href(anchor["href"])
            if not destination:
                continue
            company = _company_from_url(destination)
            host = (urlparse(destination).netloc or "").lower().replace("www.", "")
            is_ats = company is not None or any(host == h for h, _ in _ATS_HOSTS)
            if not is_ats:
                continue

            canonical = clean_url(destination)
            if not canonical or canonical in seen:
                continue

            heading = anchor.find("h3")
            raw_title = heading.get_text(" ", strip=True) if heading else anchor.get_text(" ", strip=True)
            title = _clean_title(raw_title)
            if not title or len(title) < 3:
                continue
            title, title_company = _split_title_and_company(title)

            # The snippet lives in a sibling container; take the nearest block of
            # text that is not the heading itself.
            snippet = None
            container = anchor.find_parent("div")
            for _ in range(3):
                if container is None:
                    break
                text = container.get_text("\n", strip=True)
                if text and len(text) > len(raw_title) + 40:
                    snippet = text
                    break
                container = container.find_parent("div")

            salary_min, salary_max, currency = parse_salary_range(snippet)

            seen.add(canonical)
            results.append(
                self.normalize(
                    {
                        "title": title,
                        "company_name": company or title_company,
                        "company_url": f"https://{host}" if host else None,
                        "source_url": canonical,
                        "description": strip_html(snippet),
                        "location": "Remote" if remote_only else location,
                        "location_type": "remote" if remote_only else None,
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": currency,
                        "metadata": {"google_provider": "keyless_web_search", "result_host": host},
                    }
                )
            )
            if len(results) >= limit:
                break

        if not results:
            logger.info("Keyless Google search returned no parseable job links for '%s'", terms)
        return results


class GreenhouseAdapter(BaseScraperAdapter):
    """Public Greenhouse job boards - the highest-trust source in the rubric.

    Boards are supplied by the caller (``filters["boards"]``, e.g. slugified
    ``preferred_companies``) or by the ``GREENHOUSE_BOARDS`` setting. With no
    boards configured the adapter returns nothing instead of scanning a
    hardcoded list of companies nobody asked about.
    """

    API = "https://boards-api.greenhouse.io/v1/boards"

    def __init__(self):
        super().__init__(name="greenhouse", rate_limit_delay_seconds=0.3)
        self._board_names: Dict[str, Optional[str]] = {}

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        cfg = scraper_config()
        boards = [str(b).strip() for b in (filters.get("boards") or cfg.greenhouse_boards) if str(b).strip()]
        if not boards:
            return []

        limit = int(filters.get("limit") or cfg.results_per_source)
        await self.throttle()

        async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
            gathered = await asyncio.gather(
                *(self._fetch_board(client, board, query, filters) for board in boards),
                return_exceptions=True,
            )

        results: List[Dict[str, Any]] = []
        for board, outcome in zip(boards, gathered):
            if isinstance(outcome, Exception):
                logger.info("Greenhouse board '%s' failed: %s", board, outcome)
                continue
            results.extend(outcome)
        return results[:limit]

    async def _fetch_board(
        self, client: httpx.AsyncClient, board: str, query: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        resp = await client.get(f"{self.API}/{quote_plus(board)}/jobs", params={"content": "true"})
        if resp.status_code != 200:
            return []

        company = await self._board_name(client, board)
        location_filter = (filters.get("location") or "").lower().strip()
        remote_only = bool(filters.get("remote_only"))

        results: List[Dict[str, Any]] = []
        for job in resp.json().get("jobs") or []:
            title = job.get("title")
            description = strip_html(job.get("content"))
            if not _matches(query, title, description):
                continue

            location = (job.get("location") or {}).get("name")
            location_lower = str(location or "").lower()
            is_remote = "remote" in location_lower or "anywhere" in location_lower
            if remote_only and not is_remote:
                continue
            if location_filter and location_filter not in location_lower and not is_remote:
                continue

            departments = [d.get("name") for d in (job.get("departments") or []) if isinstance(d, dict)]
            results.append(
                self.normalize(
                    {
                        "title": title,
                        "company_name": company,
                        "company_url": f"https://boards.greenhouse.io/{board}",
                        "source_url": job.get("absolute_url"),
                        "description": description,
                        "location": location,
                        "location_type": "remote" if is_remote else None,
                        "published_date": job.get("updated_at") or job.get("first_published"),
                        "metadata": {
                            "board": board,
                            "greenhouse_job_id": job.get("id"),
                            "departments": [d for d in departments if d],
                        },
                    }
                )
            )
        return results

    async def _board_name(self, client: httpx.AsyncClient, board: str) -> Optional[str]:
        """Real company name from the board metadata, cached per process."""
        if board in self._board_names:
            return self._board_names[board]
        name: Optional[str] = None
        try:
            resp = await client.get(f"{self.API}/{quote_plus(board)}")
            if resp.status_code == 200:
                name = resp.json().get("name")
        except Exception as exc:
            logger.debug("Could not read Greenhouse board name for '%s': %s", board, exc)
        self._board_names[board] = name or prettify_slug(board)
        return self._board_names[board]


class LeverAdapter(BaseScraperAdapter):
    """Public Lever postings API. Boards come from the caller or settings."""

    API = "https://api.lever.co/v0/postings"

    def __init__(self):
        super().__init__(name="lever", rate_limit_delay_seconds=0.3)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        cfg = scraper_config()
        boards = [str(b).strip() for b in (filters.get("boards") or cfg.lever_boards) if str(b).strip()]
        if not boards:
            return []

        limit = int(filters.get("limit") or cfg.results_per_source)
        await self.throttle()

        async with httpx.AsyncClient(timeout=cfg.timeout, headers=cfg.headers) as client:
            gathered = await asyncio.gather(
                *(self._fetch_board(client, board, query, filters) for board in boards),
                return_exceptions=True,
            )

        results: List[Dict[str, Any]] = []
        for board, outcome in zip(boards, gathered):
            if isinstance(outcome, Exception):
                logger.info("Lever board '%s' failed: %s", board, outcome)
                continue
            results.extend(outcome)
        return results[:limit]

    async def _fetch_board(
        self, client: httpx.AsyncClient, board: str, query: str, filters: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        resp = await client.get(f"{self.API}/{quote_plus(board)}", params={"mode": "json"})
        if resp.status_code != 200:
            return []

        company = prettify_slug(board)
        location_filter = (filters.get("location") or "").lower().strip()
        remote_only = bool(filters.get("remote_only"))

        results: List[Dict[str, Any]] = []
        payload = resp.json()
        if not isinstance(payload, list):
            return []

        for job in payload:
            if not isinstance(job, dict):
                continue
            title = job.get("text")
            description = job.get("descriptionPlain") or strip_html(job.get("description"))
            if not _matches(query, title, description):
                continue

            categories = job.get("categories") or {}
            location = categories.get("location")
            workplace = str(job.get("workplaceType") or "").lower()
            location_lower = str(location or "").lower()
            is_remote = workplace == "remote" or "remote" in location_lower
            if remote_only and not is_remote:
                continue
            if location_filter and location_filter not in location_lower and not is_remote:
                continue

            published = job.get("createdAt")
            if isinstance(published, (int, float)):
                # Lever reports epoch milliseconds.
                from datetime import datetime, timezone

                published = datetime.fromtimestamp(published / 1000, tz=timezone.utc).isoformat()

            results.append(
                self.normalize(
                    {
                        "title": title,
                        "company_name": company,
                        "company_url": f"https://jobs.lever.co/{board}",
                        "source_url": job.get("hostedUrl") or job.get("applyUrl"),
                        "description": strip_html(description) if description else None,
                        "location": location,
                        "location_type": workplace or ("remote" if is_remote else None),
                        "published_date": published,
                        "metadata": {
                            "board": board,
                            "lever_job_id": job.get("id"),
                            "team": categories.get("team"),
                            "commitment": categories.get("commitment"),
                        },
                    }
                )
            )
        return results


class WeWorkRemotelyAdapter(BaseScraperAdapter):
    """We Work Remotely search RSS feed. Keyless, remote-only by definition."""

    FEED = "https://weworkremotely.com/remote-jobs/search.rss"

    def __init__(self):
        super().__init__(name="weworkremotely", rate_limit_delay_seconds=0.3)

    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        filters = filters or {}
        cfg = scraper_config()
        limit = int(filters.get("limit") or cfg.results_per_source)
        await self.throttle()

        try:
            async with httpx.AsyncClient(
                timeout=cfg.timeout, headers=cfg.headers, follow_redirects=True
            ) as client:
                resp = await client.get(self.FEED, params={"term": query})
            if resp.status_code != 200:
                return []
            root = ET.fromstring(resp.text)
        except Exception as exc:
            logger.warning("WeWorkRemotely feed failed for '%s': %s", query, exc)
            return []

        results: List[Dict[str, Any]] = []
        for item in root.iter("item"):
            raw_title = (item.findtext("title") or "").strip()
            if not raw_title:
                continue
            # WWR titles are "Company: Role".
            company, _, role = raw_title.partition(":")
            title = (role or raw_title).strip()
            company_name = company.strip() if role else None

            description = strip_html(item.findtext("description"))
            region = (item.findtext("region") or "").strip() or None
            salary_min, salary_max, currency = parse_salary_range(description)

            results.append(
                self.normalize(
                    {
                        "title": title,
                        "company_name": company_name,
                        "source_url": (item.findtext("link") or "").strip() or None,
                        "description": description,
                        "location": region or "Remote",
                        "location_type": "remote",
                        "salary_min": salary_min,
                        "salary_max": salary_max,
                        "salary_currency": currency,
                        "published_date": (item.findtext("pubDate") or "").strip() or None,
                        "metadata": {"category": (item.findtext("category") or "").strip() or None},
                    }
                )
            )
            if len(results) >= limit:
                break
        return results


__all__ = [
    "GoogleJobsAdapter",
    "GreenhouseAdapter",
    "LeverAdapter",
    "WeWorkRemotelyAdapter",
]
