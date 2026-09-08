"""Base scraper adapter and registry for multi-source opportunity and company discovery."""
import abc
import asyncio
import html as html_module
import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

#: Used only when settings cannot be loaded (e.g. an adapter exercised in isolation).
FALLBACK_TIMEOUT = 20.0
FALLBACK_USER_AGENT = "EjicodeAI-TalentEngine/1.0 (+https://ejicode.ai)"
FALLBACK_RESULTS_PER_SOURCE = 25

#: Hours in a standard work year, used to annualise hourly rates so an hourly
#: posting can be compared against a candidate's annual salary expectation.
#: Stated explicitly rather than buried in a magic number.
WORK_HOURS_PER_YEAR = 2080

_CURRENCY_SYMBOLS = {
    "$": "USD",
    "US$": "USD",
    "C$": "CAD",
    "A$": "AUD",
    "€": "EUR",
    "£": "GBP",
    "₦": "NGN",
    "₹": "INR",
    "R$": "BRL",
    "¥": "JPY",
}


@dataclass(frozen=True)
class ScraperConfig:
    """Runtime knobs every adapter shares, resolved from application settings."""

    timeout: float
    user_agent: str
    results_per_source: int
    serpapi_key: Optional[str]
    scrapingdog_key: Optional[str]
    greenhouse_boards: Tuple[str, ...]
    lever_boards: Tuple[str, ...]

    @property
    def headers(self) -> Dict[str, str]:
        return {"User-Agent": self.user_agent}


def _split_csv(value: Optional[str]) -> Tuple[str, ...]:
    if not value:
        return ()
    return tuple(part.strip() for part in str(value).split(",") if part.strip())


def scraper_config() -> ScraperConfig:
    """Resolve scraper settings, degrading to safe defaults if settings are unavailable.

    Adapters must never crash because configuration is missing - a missing API key
    just means that code path is skipped.
    """
    try:
        from backend.app.config import get_settings

        settings = get_settings()
        return ScraperConfig(
            timeout=float(getattr(settings, "scraper_request_timeout_seconds", FALLBACK_TIMEOUT)),
            user_agent=str(getattr(settings, "scraper_user_agent", FALLBACK_USER_AGENT)),
            results_per_source=int(getattr(settings, "scraper_results_per_source", FALLBACK_RESULTS_PER_SOURCE)),
            serpapi_key=getattr(settings, "serpapi_key", None) or None,
            scrapingdog_key=getattr(settings, "scrapingdog_key", None) or None,
            greenhouse_boards=_split_csv(getattr(settings, "greenhouse_boards", "")),
            lever_boards=_split_csv(getattr(settings, "lever_boards", "")),
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.debug("Falling back to default scraper config: %s", exc)
        return ScraperConfig(
            timeout=FALLBACK_TIMEOUT,
            user_agent=FALLBACK_USER_AGENT,
            results_per_source=FALLBACK_RESULTS_PER_SOURCE,
            serpapi_key=None,
            scrapingdog_key=None,
            greenhouse_boards=(),
            lever_boards=(),
        )


def strip_html(value: Optional[str], *, max_length: Optional[int] = 2500) -> Optional[str]:
    """Turn a scraped HTML fragment into readable plain text, or None if empty."""
    if not value:
        return None
    text = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", str(value), flags=re.I | re.S)
    text = re.sub(r"<br\s*/?>|</p>|</li>|</div>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_module.unescape(text)
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not text:
        return None
    return text[:max_length] if max_length else text


def _to_amount(raw: str, suffix: str) -> Optional[float]:
    try:
        amount = float(raw.replace(",", "").replace(" ", ""))
    except (TypeError, ValueError):
        return None
    if suffix.lower() == "k":
        amount *= 1000
    return amount


def parse_salary_range(text: Optional[str]) -> Tuple[Optional[float], Optional[float], Optional[str]]:
    """Best-effort ``(min, max, currency)`` from free-text pay like "$120k - $160k a year".

    Returns ``(None, None, None)`` when nothing can be read - an unknown salary is
    reported as unknown rather than guessed.
    """
    if not text:
        return None, None, None
    raw = str(text)

    currency = None
    for symbol, code in _CURRENCY_SYMBOLS.items():
        if symbol in raw:
            currency = code
            break
    if currency is None:
        match = re.search(r"\b(USD|EUR|GBP|CAD|AUD|NGN|INR|BRL|JPY|CHF|SEK|ZAR)\b", raw, re.I)
        if match:
            currency = match.group(1).upper()

    numbers = [
        _to_amount(m.group(1), m.group(2) or "")
        for m in re.finditer(r"(\d[\d,]*(?:\.\d+)?)\s*([kK])?", raw)
    ]
    numbers = [n for n in numbers if n]
    if not numbers:
        return None, None, currency

    # Hourly / daily / weekly / monthly rates are annualised so they are
    # comparable with a candidate's annual expectation.
    lowered = raw.lower()
    multiplier = 1.0
    if re.search(r"per hour|an hour|/\s*hour|/\s*hr|hourly", lowered):
        multiplier = WORK_HOURS_PER_YEAR
    elif re.search(r"per day|a day|/\s*day|daily", lowered):
        multiplier = 260
    elif re.search(r"per week|a week|/\s*week|weekly", lowered):
        multiplier = 52
    elif re.search(r"per month|a month|/\s*month|/\s*mo|monthly", lowered):
        multiplier = 12

    scaled = sorted(n * multiplier for n in numbers)
    # Drop values too small to be pay (percentages, "top 10", years).
    scaled = [n for n in scaled if n >= 1000]
    if not scaled:
        return None, None, currency
    low = scaled[0]
    high = scaled[-1] if len(scaled) > 1 else None
    return low, high, currency


def prettify_slug(slug: Optional[str]) -> Optional[str]:
    """``acme-labs`` -> ``Acme Labs``. Used for board slugs that carry no display name."""
    if not slug:
        return None
    words = re.split(r"[-_.]+", str(slug).strip())
    cleaned = [w for w in words if w]
    if not cleaned:
        return None
    return " ".join(w if w.isupper() else w.capitalize() for w in cleaned)


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
