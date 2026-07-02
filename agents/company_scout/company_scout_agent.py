"""Company Scout Agent — discovers real companies from GitHub Trending and HN Show HN."""
import logging
from typing import List, Dict, Any
from agents.base.base_agent import BaseAgent, AgentState, AgentStatus

logger = logging.getLogger(__name__)


class GitHubTrendingScraper:
    """Scrape GitHub trending repos to find active tech companies/projects."""

    async def scrape(self) -> List[Dict[str, Any]]:
        try:
            import httpx
            from bs4 import BeautifulSoup

            async with httpx.AsyncClient(headers={"User-Agent": "EjicodeAI/1.0"}) as client:
                resp = await client.get("https://github.com/trending", timeout=20)
                soup = BeautifulSoup(resp.text, "html.parser")

                companies = []
                for repo in soup.select("article.Box-row")[:20]:
                    name_tag = repo.select_one("h2 a")
                    if not name_tag:
                        continue
                    full_name = name_tag.get_text(strip=True).replace("\n", "").replace(" ", "")
                    parts = full_name.split("/")
                    if len(parts) != 2:
                        continue
                    owner, repo_name = parts

                    desc_tag = repo.select_one("p")
                    description = desc_tag.get_text(strip=True) if desc_tag else ""

                    lang_tag = repo.select_one("[itemprop='programmingLanguage']")
                    language = lang_tag.get_text(strip=True) if lang_tag else ""

                    stars_tag = repo.select_one("a[href$='/stargazers']")
                    stars = stars_tag.get_text(strip=True).replace(",", "") if stars_tag else "0"

                    companies.append({
                        "name": owner,
                        "domain": f"github.com/{owner}",
                        "website": f"https://github.com/{owner}",
                        "industry": language or "Technology",
                        "description": description,
                        "source": "github_trending",
                        "metadata": {"repo": repo_name, "stars": stars, "language": language},
                    })

                logger.info(f"GitHub Trending: {len(companies)} companies")
                return companies
        except Exception as e:
            logger.error(f"GitHub Trending error: {e}")
            return []


class HNShowScraper:
    """Scrape HN 'Show HN' posts to find new startups/products."""

    async def scrape(self) -> List[Dict[str, Any]]:
        try:
            import httpx

            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    "https://hn.algolia.com/api/v1/search",
                    params={"tags": "show_hn", "hitsPerPage": 30, "numericFilters": "points>10"},
                    timeout=15,
                )
                hits = resp.json().get("hits", [])

                companies = []
                for hit in hits:
                    title = hit.get("title", "")
                    url = hit.get("url", "")
                    if not url or not title:
                        continue

                    # Extract domain
                    try:
                        from urllib.parse import urlparse
                        domain = urlparse(url).netloc.replace("www.", "")
                    except Exception:
                        domain = ""

                    if not domain:
                        continue

                    companies.append({
                        "name": title.replace("Show HN: ", "")[:80],
                        "domain": domain,
                        "website": url,
                        "industry": "Technology",
                        "description": title,
                        "source": "hackernews_show",
                        "metadata": {"points": hit.get("points", 0), "hn_id": hit.get("objectID")},
                    })

                logger.info(f"HN Show HN: {len(companies)} companies")
                return companies
        except Exception as e:
            logger.error(f"HN Show HN error: {e}")
            return []


class CompanyScoutAgent(BaseAgent):
    def __init__(self):
        super().__init__(
            name="company_scout",
            agent_type="discovery",
            description="Discovers companies from GitHub Trending and HackerNews Show HN",
            max_retries=3,
            timeout_seconds=120,
        )
        self.scrapers = [GitHubTrendingScraper(), HNShowScraper()]

    async def validate_input(self, input_data: dict) -> bool:
        return True

    async def process(self, state: AgentState) -> AgentState:
        import asyncio
        state["status"] = AgentStatus.RUNNING
        state["current_step"] = "discovery"

        results = await asyncio.gather(*[s.scrape() for s in self.scrapers], return_exceptions=True)

        all_companies = []
        for r in results:
            if isinstance(r, list):
                all_companies.extend(r)

        # Deduplicate by domain
        seen = {}
        for c in all_companies:
            domain = c.get("domain", "")
            if domain and domain not in seen:
                seen[domain] = c
        unique = list(seen.values())

        logger.info(f"Company Scout: {len(unique)} unique companies found")

        return self._update_state(state, {
            "current_step": "discovery_complete",
            "steps_completed": ["company_discovery"],
            "output_data": {"companies": unique, "count": len(unique)},
            "status": AgentStatus.SUCCESS,
        })

    async def validate_output(self, output_data: dict) -> bool:
        return "companies" in output_data
