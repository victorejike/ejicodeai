"""Multi-source scraper adapter package."""
from agents.scrapers.base_adapter import BaseScraperAdapter, clean_url
from agents.scrapers.adapters import ScraperRegistry, scraper_registry

__all__ = ["BaseScraperAdapter", "ScraperRegistry", "clean_url", "scraper_registry"]
