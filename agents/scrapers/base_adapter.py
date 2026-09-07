"""Base scraper adapter and registry for multi-source opportunity and company discovery."""
import abc
import asyncio
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)


def clean_url(url: Optional[str]) -> Optional[str]:
    """Remove tracking query parameters like utm_* and trailing slashes."""
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
        clean_query = "&".join(
            part for part in parsed.query.split("&")
            if not part.startswith("utm_") and not part.startswith("ref=")
        )
        return urlunparse((
            parsed.scheme,
            parsed.netloc.lower(),
            parsed.path.rstrip("/") if parsed.path != "/" else "/",
            parsed.params,
            clean_query,
            "",
        ))
    except Exception:
        return url.strip()


class BaseScraperAdapter(abc.ABC):
    """Standard interface for source discovery adapters."""

    def __init__(self, name: str, rate_limit_delay_seconds: float = 0.5):
        self.name = name
        self.rate_limit_delay = rate_limit_delay_seconds

    @abc.abstractmethod
    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute discovery search on target source."""
        pass

    def normalize(self, raw_item: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw scraped item into standardized opportunity/company structure. Missing fields default to None."""
        source_url = clean_url(raw_item.get("source_url") or raw_item.get("url"))
        company_url = clean_url(raw_item.get("company_url") or raw_item.get("website"))

        domain = None
        if company_url:
            try:
                domain = urlparse(company_url).netloc.lower().replace("www.", "")
            except Exception:
                domain = None

        return {
            "source": self.name,
            "source_url": source_url,
            "title": raw_item.get("title") or raw_item.get("job_title"),
            "company_name": raw_item.get("company") or raw_item.get("company_name"),
            "company_domain": domain or raw_item.get("company_domain"),
            "company_url": company_url,
            "description": raw_item.get("description") or raw_item.get("raw_description"),
            "location": raw_item.get("location"),
            "location_type": raw_item.get("location_type") or ("remote" if "remote" in str(raw_item.get("location", "")).lower() else "onsite"),
            "salary_min": raw_item.get("salary_min"),
            "salary_max": raw_item.get("salary_max"),
            "salary_currency": raw_item.get("salary_currency", "USD"),
            "tech_required": raw_item.get("tech_required") or raw_item.get("tags") or [],
            "published_date": raw_item.get("published_date") or raw_item.get("posted_at"),
            "contact_email": raw_item.get("contact_email") or raw_item.get("email"),
            "contact_name": raw_item.get("contact_name"),
            "contact_role": raw_item.get("contact_role"),
            "metadata": raw_item.get("metadata", {}),
        }

    async def throttle(self):
        """Respect source rate limits."""
        if self.rate_limit_delay > 0:
            await asyncio.sleep(self.rate_limit_delay)
